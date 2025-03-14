#!/usr/bin/env python

"""
Created by mebitek in 2025.

Inspired by:
 - https://github.com/Waldmensch1/venus.dbus-tasmota-inverter (base code)
 - https://github.com/Marv2190/venus.dbus-MqttToGridMeter (Inspiration)
 - https://github.com/victronenergy/velib_python/blob/master/dbusdummyservice.py (Template)


This code and its documentation can be found on: https://github.com/Waldmensch1/venus.dbus-tasmota-inverter
Used https://github.com/victronenergy/velib_python/blob/master/dbusdummyservice.py as basis for this service.
Reading information from Tasmota SENSOR MQTT and puts the info on dbus as inverter.

"""

# our own packages
import configparser
import shutil

import requests

import utils
import vreg_link_item
from tasmota_broker import Broker
from tasmota_config import TasmotaConfig

from vedbus import VeDbusService, VeDbusItemImport, VeDbusItemExport
import os
import json
import sys
import dbus
import logging
from gi.repository import GLib
import _thread as thread  # for daemon = True  / Python 3.x

from vreg_link_item import VregLinkItem, InverterReg, GenericReg


class Inverter:
    def __init__(self, status, voltage, current, power, temperature):
        self.state = 'Offline'
        self.status = status
        self.voltage = voltage
        self.current = current
        self.power = power
        self.temperature = temperature
        self.apparent_power = 0
        self.battery_voltage = None
        self.frequency = 50

    def get_mode_and_state(self):
        # /Mode  <- Switch position: 1=Charger only,2=Inverter only;3=On;4=Off;5=Low Power/Eco;
        #           251=Passthrough;252=Standby;253=Hibernate
        # /State <- 0=Off; 1=Low Power; 2=Fault; 9=Inverting

        if self.state == 'Offline':
            return 4, 0
        if self.status == 'ON':
            if self.power > 15:
                return 2, 9
            else:
                return 5, 1
        else:
            return 4, 0


sys.path.insert(1, os.path.join(
    os.path.dirname(__file__), '../ext/velib_python'))


class TasmotaInverterService:

    def __init__(self, servicename, deviceinstance, paths, productname='Tasmota Inverter', connection='MQTT',
                 config=None):

        self.config = config or TasmotaConfig()
        # prepare dict for topic categories
        self.topic_category = {}
        self.get_topics()

        # broker
        self.broker = Broker(config.get_mqtt_name(), config.get_mqtt_address(), config.get_mqtt_port())
        self.broker.topic_category = self.topic_category
        self.broker.on_message(self.on_message)
        self.broker.connect_broker()

        # inverter class
        self.inverter = Inverter("OFF", 0, 0, 0, 0)

        # dbus service
        self._dbusservice = VeDbusService(servicename, register=False)
        self._paths = paths

        vregtype = lambda *args, **kwargs: VregLinkItem(*args, **kwargs,
                                                        getvreg=self.vreglink_get, setvreg=self.vreglink_set)

        logging.debug("%s /DeviceInstance = %d" %
                      (servicename, deviceinstance))

        productname = config.get_product_name()

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path('/Mgmt/ProcessVersion', config.get_version())
        self._dbusservice.add_path('/Mgmt/Connection', connection)

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', deviceinstance)
        # value used in ac_sensor_bridge.cpp of dbus-cgwacs
        self._dbusservice.add_path('/ProductId', 41601)
        self._dbusservice.add_path('/ProductName', productname)
        self._dbusservice.add_path('/DeviceName', productname)
        self._dbusservice.add_path('/FirmwareVersion', 0x0136)
        self._dbusservice.add_path('/HardwareVersion', 8)
        self._dbusservice.add_path('/Connected', 1)
        self._dbusservice.add_path('/Serial', config.get_serial())

        self._dbusservice.add_path('/Devices/0/CustomName', productname)
        self._dbusservice.add_path('/Devices/0/DeviceInstance', deviceinstance)
        self._dbusservice.add_path('/Devices/0/FirmwareVersion', 0x0136)
        self._dbusservice.add_path('/Devices/0/ProductId', 0xA281)
        self._dbusservice.add_path('/Devices/0/ProductName', "Smart Phoenix Inverter 12V 1600VA 230V")
        self._dbusservice.add_path('/Devices/0/ServiceName', servicename)
        self._dbusservice.add_path('/Devices/0/Serial', config.get_serial())
        self._dbusservice.add_path('/Devices/0/VregLink', None, itemtype=vregtype)

        for path, settings in self._paths.items():
            self._dbusservice.add_path(
                path, settings['initial'], writeable=True, onchangecallback=self._handlechangedvalue)

        self._dbusservice.register()
        GLib.timeout_add(1000, self._update)

    def _update(self):
        dbus_conn = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()
        battery_voltage = VeDbusItemImport(dbus_conn, 'com.victronenergy.system', '/Dc/Battery/Voltage')
        self.inverter.battery_voltage = battery_voltage.get_value()
        # if inverter.battery_voltage == None:
        #    inverter.battery_voltage = 11.65

        # inverter.battery_voltage = round(random.uniform(11.6, 14.65),2)

        # else:
        #    if float(inverter.battery_voltage) < 14:
        #        inverter.battery_voltage = float(inverter.battery_voltage) + 1
        #    elif float(inverter.battery_voltage) >= 14 and float(inverter.battery_voltage) <= 14.65:
        #        inverter.battery_voltage = float(inverter.battery_voltage) + 0.01
        # else:
        #    if float(inverter.battery_voltage) < 12:
        #        inverter.battery_voltage = float(inverter.battery_voltage) + 0.01
        # elif float(inverter.battery_voltage) >= 14 and float(inverter.battery_voltage) <= 14.65:
        #    inverter.battery_voltage = float(inverter.battery_voltage) + 0.01

        self._dbusservice['/Ac/Out/L1/F'] = self.inverter.frequency
        self._dbusservice['/Ac/Out/L1/V'] = self.inverter.voltage
        self._dbusservice['/Ac/Out/L1/I'] = self.inverter.current
        self._dbusservice['/Ac/Out/L1/P'] = self.inverter.power
        self._dbusservice['/Ac/Out/L1/S'] = self.inverter.apparent_power

        self._dbusservice["/Ac/L1/Current"] = self.inverter.current
        self._dbusservice["/Ac/L1/Power"] = self.inverter.power
        self._dbusservice["/Ac/L1/Voltage"] = self.inverter.voltage

        self._dbusservice["/Dc/0/Voltage"] = self.inverter.battery_voltage
        if self.inverter.battery_voltage == 0 or None:
            dc_current = 0
        else:
            dc_current = round(float(self.inverter.power) / float(self.inverter.battery_voltage), 2)
        self._dbusservice["/Dc/0/Current"] = -dc_current

        mode, state = self.inverter.get_mode_and_state()
        self._dbusservice['/Mode'] = mode
        self._dbusservice['/State'] = state

        # alarms
        if self.inverter.temperature > float(self.config.get_high_temperature_limit()):
            self._dbusservice['/Alarms/HighTemperature'] = 1
        else:
            self._dbusservice['/Alarms/HighTemperature'] = 0

        overload = self.config.get_overload_limit() * 0.1 + self.config.get_overload_limit()
        if self.inverter.power > overload:
            self._dbusservice['/Alarms/Overload'] = 1
        else:
            self._dbusservice['/Alarms/Overload'] = 0

        if self.inverter.battery_voltage is not None:
            if float(self.inverter.battery_voltage) < float(self.config.get_low_voltage_limit()):
                self._dbusservice['/Alarms/LowVoltage'] = 1
            else:
                self._dbusservice['/Alarms/LowVoltage'] = 0

            if float(self.inverter.battery_voltage) < float(self.config.get_low_battery_shutdown()):
                self._dbusservice['/Alarms/LowVoltageShutdown'] = 1
                if self.inverter.status != 'OFF':
                    self.tasmota_http_request(4, "VE_REG_SHUTDOWN_LOW_VOLTAGE_SET")

        index = self._dbusservice['/UpdateIndex'] + 1  # increment index
        if index > 255:  # maximum value of the index
            index = 0  # overflow from 255 to 0
        self._dbusservice['/UpdateIndex'] = index
        return True

    # MQTT On message
    def on_message(self, client, userdata, msg):
        try:
            logging.debug('Incoming message from: ' + msg.topic)

            # write the values into dict
            if msg.topic in self.topic_category:
                if self.topic_category[msg.topic] == 'LWT':
                    self.inverter.state = msg.payload.decode('utf-8')
                else:
                    jsonpayload = json.loads(msg.payload)
                    if self.topic_category[msg.topic] == 'CONFIG':
                        self.inverter.status = jsonpayload['POWER']
                    else:
                        self.inverter.power = float(jsonpayload["ENERGY"]["Power"])
                        self.inverter.current = float(jsonpayload["ENERGY"]["Current"])
                        self.inverter.voltage = float(jsonpayload["ENERGY"]["Voltage"])
                        self.inverter.temperature = float(jsonpayload["ESP32"]["Temperature"])
                        self.inverter.apparent_power = float(jsonpayload["ENERGY"]["ApparentPower"])

            else:
                logging.debug("Topic not in configurd topics. This shouldn't be happen")

        except Exception as e:
            logging.exception("Error in handling of received message payload: " + msg.payload)
            logging.exception(e)

    def _handlechangedvalue(self, path, value):
        logging.debug("someone else updated %s to %s" % (path, value))
        if path == "/Mode":
            self.tasmota_http_request(value, "GUI")
        if path.startswith("/Settings"):
            value_str = str(value)
            if value_str.startswith("."):
                value_str = "0%s" % value_str
            parts = path.split('/')
            p, k = parts[-2:]
            self.config.write_to_config(value_str, p, k)
        return True  # accept the change

    def tasmota_http_request(self, value, source):
        ip = self.config.get_tasmota_ip()
        if value == 4:
            response = requests.get(f"http://{ip}/cm?cmnd=Power%20off")
            self.inverter.status = "OFF"
        elif value == 2 or value == 5:  # Ensure we handle both values correctly
            if not self.can_start_due_voltage_limits():
                return
            response = requests.get(f"http://{ip}/cm?cmnd=Power%20On")
            self.inverter.status = "ON"

        if response is None:
            logging.warning("Failed to send HTTP request.")
            return

        # Update the status only if the request was successful
        if response.status_code == 200:
            logging.info(f"Status changed from {source}")

    def can_start_due_voltage_limits(self):
        if float(self.inverter.battery_voltage) < float(
                self.config.get_low_voltage_limit()) and self._dbusservice.__getitem__(
                '/Alarms/LowVoltageShutdown') == 0:
            logging.info("Cannot turn on the device, low battery restart and alarm has not been reached")
            return False
        if self._dbusservice.__getitem__('/Alarms/LowVoltageShutdown') == 1 and float(
                self.inverter.battery_voltage) < float(
                self.config.get_charge_detected()):
            logging.info(
                "Cannot turn on the device, shutdown detected for low battery and battery voltage has no reached the charged voltage")
            return False
        if self._dbusservice.__getitem__('/Alarms/LowVoltageShutdown') == 1:
            self._dbusservice['/Alarms/LowVoltageShutdown'] = 0
        return True

    def get_topics(self):
        self.topic_category[self.config.get_topic_option('L1')] = 'L1'
        self.topic_category[self.config.get_topic_option('CONFIG')] = 'CONFIG'
        self.topic_category[self.config.get_topic_option('LWT')] = 'LWT'

    # Vreg methods get/set
    def vreglink_get(self, regid):
        if regid == InverterReg.VE_REG_DEVICE_MODE.value:
            mode, state = self.inverter.get_mode_and_state()
            return GenericReg.OK.value, [mode]
        if regid == InverterReg.VE_REG_INV_WAVE_SET50HZ_NOT60HZ.value:
            return GenericReg.OK.value, [1]  # 50Hz
        elif regid == InverterReg.VE_REG_AC_OUT_VOLTAGE.value:
            return GenericReg.OK.value, [self.inverter.voltage]
        elif regid == InverterReg.VE_REG_AC_OUT_CURRENT.value:
            return GenericReg.OK.value, [self.inverter.current]
        elif regid == InverterReg.VE_REG_DC_CHANNEL1_VOLTAGE.value:
            return GenericReg.OK.value, [self.inverter.battery_voltage]
        elif regid == InverterReg.VE_REG_AC_OUTPUT_L1_APPARENT_POWER.value or regid == InverterReg.VE_REG_AC_OUT_APPARENT_POWER.value:
            return GenericReg.OK.value, [self.inverter.apparent_power]
        elif regid == InverterReg.VE_REG_SHUTDOWN_LOW_VOLTAGE_SET.value:
            low_battery_shutdown = float(self.config.get_low_battery_shutdown())
            return GenericReg.OK.value, utils.convert_decimal(low_battery_shutdown)
        elif regid == InverterReg.VE_REG_ALARM_LOW_VOLTAGE_SET.value:
            low_voltage_warning = float(self.config.get_low_voltage_limit())
            return GenericReg.OK.value, utils.convert_decimal(low_voltage_warning)
        elif regid == InverterReg.VE_REG_ALARM_LOW_VOLTAGE_CLEAR.value:
            charge_detect = float(self.config.get_charge_detected())
            return GenericReg.OK.value, utils.convert_decimal(charge_detect)
        elif regid == InverterReg.VE_REG_INV_PROT_UBAT_DYN_CUTOFF_ENABLE.value:
            return GenericReg.OK.value, [0]
        elif regid == InverterReg.VE_REG_INV_OPER_ECO_LOAD_DETECT_PERIODS.value:
            return GenericReg.OK.value, [0x08]  # 0.16s
        elif regid == InverterReg.VE_REG_INV_OPER_ECO_MODE_RETRY_TIME.value:
            return GenericReg.OK.value, [0x0A]  # 3s
        elif regid == InverterReg.VE_REG_CAPABILITIES1.value:
            return GenericReg.OK.value, utils.create_capabilities_status(False, False, False, False, True)
        else:
            logging.debug("GET REG_ID %s" % regid)
            return GenericReg.OK.value, []

    def vreglink_set(self, regid, data):
        logging.debug(" * * * SET REGID %s" % hex(regid))
        if regid == InverterReg.VE_REG_DEVICE_MODE.value:  # change state
            value = int.from_bytes(data, byteorder='little')
            self.tasmota_http_request(value, "VictronConnect")
        elif regid == InverterReg.VE_REG_ALARM_LOW_VOLTAGE_SET.value:
            decimal = utils.convert_to_decimal(bytearray(data))
            self.config.write_to_config(decimal, 'Warnings', 'LowVoltage')
        elif regid == InverterReg.VE_REG_SHUTDOWN_LOW_VOLTAGE_SET.value:  # change low battery shutdown -
            decimal = utils.convert_to_decimal(bytearray(data))
            self.config.write_to_config(decimal, 'Options', 'LowBatteryShutdown')
        elif regid == InverterReg.VE_REG_ALARM_LOW_VOLTAGE_CLEAR.value:
            decimal = utils.convert_to_decimal(bytearray(data))
            self.config.write_to_config(decimal, 'Options', 'ChargeDetected')

        return GenericReg.OK.value, data


def main():
    config = TasmotaConfig()

    # set logging level to include info level entries
    level = logging.INFO
    if config.get_debug():
        level = logging.DEBUG
    logging.basicConfig(level=level)
    logging.info(">>>>>>>>>>>>>>>> Tasmota Inverter Starting <<<<<<<<<<<<<<<<")

    thread.daemon = True  # allow the program to quit

    from dbus.mainloop.glib import DBusGMainLoop
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    pvac_output = TasmotaInverterService(
        servicename='com.victronenergy.inverter.tasmota',
        deviceinstance=295,
        paths={
            '/Dc/0/Voltage': {'initial': 0},
            '/Dc/0/Current': {'initial': 0},
            '/Ac/Power': {'initial': 0},
            '/Ac/Out/L1/F': {'initial': 50},
            '/Ac/Out/L1/V': {'initial': 0},
            '/Ac/Out/L1/I': {'initial': 0},
            '/Ac/Out/L1/P': {'initial': 0},
            '/Ac/Out/L1/S': {'initial': 0},
            '/Ac/L1/Voltage': {'initial': 0},
            '/Ac/L1/Current': {'initial': 0},
            '/Ac/L1/Power': {'initial': 0},
            '/Alarms/LowVoltage': {'initial': 0},
            '/Alarms/HighTemperature': {'initial': 0},
            '/Alarms/Overload': {'initial': 0},
            '/Alarms/LowVoltageShutdown': {'initial': 0},
            '/Mode': {'initial': 2},
            '/State': {'initial': 0},

            '/Settings/Tasmota/Setup/Name': {'initial': config.get_inverter_name()},
            '/Settings/Tasmota/Setup/Serial': {'initial': config.get_inverter_serial()},

            '/Settings/Tasmota/Setup/TasmotaIp': {'initial': config.get_tasmota_ip()},

            '/Settings/Tasmota/MQTTBroker/Address': {'initial': config.get_mqtt_address()},
            '/Settings/Tasmota/MQTTBroker/Port': {'initial': config.get_mqtt_port()},
            '/Settings/Tasmota/MQTTBroker/Name': {'initial': config.get_mqtt_name()},

            '/Settings/Tasmota/Warnings/HighTemperature': {'initial': config.get_high_temperature_limit()},
            '/Settings/Tasmota/Warnings/Overload': {'initial': config.get_overload_limit()},
            '/Settings/Tasmota/Warnings/LowVoltage': {'initial': config.get_low_voltage_limit()},

            '/Settings/Tasmota/Options/LowBatteryShutdown': {'initial': config.get_low_battery_shutdown()},
            '/Settings/Tasmota/Options/ChargeDetected': {'initial': config.get_charge_detected()},

            '/Settings/Tasmota/Topics/L1': {'initial': config.get_topic_option("L1")},
            '/Settings/Tasmota/Topics/CONFIG': {'initial': config.get_topic_option("CONFIG")},
            '/Settings/Tasmota/Topics/LWT': {'initial': config.get_topic_option("LWT")},

            '/UpdateIndex': {'initial': 0}
        },
        config=config
    )

    logging.info('Connected to dbus, and switching over to GLib.MainLoop() (= event based)')
    mainloop = GLib.MainLoop()
    mainloop.run()


if __name__ == "__main__":
    main()
