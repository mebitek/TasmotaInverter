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
import requests

import utils

from vedbus import VeDbusService, VeDbusItemImport, VeDbusItemExport
import paho.mqtt.client as mqtt
import os
import json
import sys
import dbus
import logging
from gi.repository import GLib
import _thread as thread  # for daemon = True  / Python 3.x


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


class VregLinkItem(VeDbusItemExport):
    def __init__(self, *args, getvreg=None, setvreg=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.getvreg = getvreg
        self.setvreg = setvreg

    @dbus.service.method('com.victronenergy.VregLink',
                         in_signature='q', out_signature='qay')
    def GetVreg(self, regid):
        return self.getvreg(int(regid))

    @dbus.service.method('com.victronenergy.VregLink',
                         in_signature='qay', out_signature='qay')
    def SetVreg(self, regid, data):
        return self.setvreg(int(regid), bytes(data))

sys.path.insert(1, os.path.join(
    os.path.dirname(__file__), '../ext/velib_python'))

config = configparser.ConfigParser()
inverter = Inverter("OFF", 0, 0, 0, 0)


def get_version():
    with open("%s/version" % (os.path.dirname(os.path.realpath(__file__))), 'r') as file:
        return file.read()

def get_config():
    config.read("%s/config.ini" % (os.path.dirname(os.path.realpath(__file__))))
    return config

def get_product_name():
    return config.get('Setup', 'Name', fallback="Tasmota Inverter")

def get_serial():
    return config.get('Setup', 'Serial', fallback="XXX")

def get_tasmota_ip():
    return config.get("Setup", "TasmotaIp", fallback="127.0.0.1")

def get_debug():
    val =  config.get("Setup", "debug", fallback=False)
    if val=="true":
        return True
    else:
        return False

def get_mqtt_address():
    address = config.get('MQTTBroker', 'address', fallback=None)
    if address is None:
        logging.error("No MQTT Broker set in config.ini")
        return address
    else:
        return address

def get_mqtt_port():
    port = config.get('MQTTBroker', 'port', fallback=None)
    if port is not None:
        return int(port)
    else:
        return 1883

def get_mqtt_name():
    return config.get('MQTTBroker', 'name', fallback='MQTT_to_Inverter')

def get_high_temperature_limit():
    return config.get('Warnings', 'HighTemperature', fallback=65)

def get_overload_limit():
    overload = float(config.get('Warnings', 'Overload', fallback=1500))
    return overload * 0.1 + overload

def get_low_voltage_limit():
    return config.get('Warnings', 'LowVoltage', fallback=10.8)

def get_low_battery_shutdown():
    return config.get('Options', 'LowBatteryShutdown', fallback=9.30)

def get_charge_detected():
    return config.get('Options', 'ChargeDetected', fallback=14.00)

def get_topic_option(topic):
    return config.get('Topics', topic)

def write_to_config(value, path, key):
    config[path][key] = str(value)
    with open("%s/config.ini" % (os.path.dirname(os.path.realpath(__file__))), 'w') as configfile:
        config.write(configfile)

def connect_broker(client):
    broker_address = get_mqtt_address()
    broker_port = get_mqtt_port()

    try:
        logging.info('connecting to MQTTBroker ' + broker_address + ' on Port ' + str(broker_port))

        if broker_address is not None:
            client.connect(broker_address, port=broker_port)  # connect to broker
            client.loop_start()
        else:
            logging.error("couldn't connect to MQTT Broker")
    except Exception as e:
        logging.exception("Error in Connect to Broker")
        logging.exception(e)
        logging.debug("Retrying...")
        connect_broker(client)

# prepare dict
topic_category = {}

# get topics for a single phase
def get_topic(phase):
    strtopics = config.get('Topics', phase, fallback='')
    if strtopics != '':
        topics = strtopics.split(',')
        for topic in topics:
            t = topic.strip()
            if t not in topic_category:
                logging.info("Topic added to " + phase + ": " + t)
                topic_category[t] = phase
            else:
                logging.info("Cannot add topic " + t + " as it is already added to " + topic_category[t])


# get topics for all phases
def get_topics():
    get_topic('L1')
    get_topic('CONFIG')
    get_topic('LWT')


# MQTT Abfragen:
def on_disconnect(client, userdata, rc):
    logging.info("Client Got Disconnected")
    if rc != 0:
        logging.info('Unexpected MQTT disconnection. Will auto-reconnect')
    else:
        logging.info('rc value:' + str(rc))
    try:
        logging.info("Trying to Reconnect")
        connect_broker(client)
    except Exception as e:
        logging.exception("Error in Retrying to Connect with Broker")
        logging.exception(e)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to MQTT Broker!")
        # subscribe to all topics we have in dict
        if len(topic_category) > 0:
            for topic in topic_category.keys():
                client.subscribe(topic)
                logging.info("Subscribed to: " + topic)
        else:
            logging.info("No Topic to subscribe, please configure in config.ini")
    else:
        logging.info("Failed to connect, return code %d\n", rc)


def on_message(client, userdata, msg):
    try:
        logging.debug('Incoming message from: ' + msg.topic)

        # write the values into dict
        if msg.topic in topic_category:
            if topic_category[msg.topic] == 'LWT':
                inverter.state = msg.payload.decode('utf-8')
            else:
                jsonpayload = json.loads(msg.payload)
                if topic_category[msg.topic] == 'CONFIG':
                    inverter.status = jsonpayload['POWER']
                else:
                    inverter.power = float(jsonpayload["ENERGY"]["Power"])
                    inverter.current = float(jsonpayload["ENERGY"]["Current"])
                    inverter.voltage = float(jsonpayload["ENERGY"]["Voltage"])
                    inverter.temperature = float(jsonpayload["ESP32"]["Temperature"])
                    inverter.apparent_power = float(jsonpayload["ENERGY"]["ApparentPower"])

        else:
            logging.debug("Topic not in configurd topics. This shouldn't be happen")

    except Exception as e:
        logging.exception("Error in handling of received message payload: " + msg.payload)
        logging.exception(e)

class DbusDummyService:

    def vreglink_get(self, regid):
        if regid == 0x0200: #VE_REG_DEVICE_MODE
            mode, state = inverter.get_mode_and_state()
            return 0x0000, [mode]
        if regid == 0xEB03: #VE_REG_INV_WAVE_SET50HZ_NOT60HZ
            return 0x0000, [1]
        elif regid == 0x2200: #VE_REG_AC_OUT_VOLTAGE
            return 0x0000, [inverter.voltage]
        elif regid == 0x2201: #VE_REG_AC_OUT_CURRENT
            return 0x0000, [inverter.current]
        elif regid == 0xED8D: #VE_REG_DC_CHANNEL1_VOLTAGE
            return 0x0000, [inverter.battery_voltage]
        elif regid == 0x2216 or regid==0x2205: #VE_REG_AC_OUTPUT_L1_APPARENT_POWER
            return 0x0000, [inverter.apparent_power]
        elif regid == 0x2210: #VE_REG_SHUTDOWN_LOW_VOLTAGE_SET
            low_battery_shutdown = float(get_low_battery_shutdown())
            return 0x0000, utils.convert_decimal(low_battery_shutdown)
        elif regid == 0x0320: #VE_REG_ALARM_LOW_VOLTAGE_SET
            low_voltage_warning = float(get_low_voltage_limit())
            return 0x0000, utils.convert_decimal(low_voltage_warning)
        elif regid == 0x0321: #VE_REG_ALARM_LOW_VOLTAGE_CLEAR
            charge_detect = float(get_charge_detected())
            return 0x0000, utils.convert_decimal(charge_detect)
        elif regid == 0xEBBA: #VE_REG_INV_PROT_UBAT_DYN_CUTOFF_ENABLE
            return 0x0000, [0]
        elif regid == 0xEB10: #VE_REG_INV_OPER_ECO_LOAD_DETECT_PERIODS
            return 0x0000, [0x08] # 0.16s
        elif regid == 0xEB06: #VE_REG_INV_OPER_ECO_MODE_RETRY_TIME
            return 0x0000, [0x0A] # 3s
        elif regid == 0x0140: #VE_REG_CAPABILITIES1
            return 0x0000, utils.create_capabilities_status(False, False, False, False, True)
        else:
            logging.debug("GET REG_ID %s" % regid)
            return 0x0000, []

    def vreglink_set(self, regid, data):
        logging.debug(" * * * SET REGID %s" %  hex(regid))
        global config
        config = get_config()
        if regid == 0x200: #change state
            value = int.from_bytes(data, byteorder='little')
            self.tasmota_http_request(value, "VictronConnect")
        elif regid == 0x0320: #change low voltage limit - VE_REG_ALARM_LOW_VOLTAGE_SET
            decimal = utils.convert_to_decimal(bytearray(data))
            write_to_config(decimal, 'Warnings', 'LowVoltage')
        elif regid == 0x2210: #change low battery shutdown -
            decimal = utils.convert_to_decimal(bytearray(data))
            write_to_config(decimal, 'Options', 'LowBatteryShutdown')
        elif regid == 0x0321:
            decimal = utils.convert_to_decimal(bytearray(data))
            write_to_config(decimal, 'Options', 'ChargeDetected')

        return 0x0000, data

    def __init__(self, servicename, deviceinstance, paths, productname='Tasmota Inverter', connection='MQTT'):
        self._dbusservice = VeDbusService(servicename, register=False)
        self._paths = paths

        vregtype = lambda *args, **kwargs: VregLinkItem(*args, **kwargs,
                                                        getvreg=self.vreglink_get, setvreg=self.vreglink_set)

        logging.debug("%s /DeviceInstance = %d" %
                     (servicename, deviceinstance))

        productname = get_product_name()

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path('/Mgmt/ProcessVersion', get_version())
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
        self._dbusservice.add_path('/Serial', get_serial())

        self._dbusservice.add_path('/Devices/0/CustomName', productname)
        self._dbusservice.add_path('/Devices/0/DeviceInstance', deviceinstance)
        self._dbusservice.add_path('/Devices/0/FirmwareVersion', 0x0136)
        self._dbusservice.add_path('/Devices/0/ProductId', 0xA281)
        self._dbusservice.add_path('/Devices/0/ProductName', "Smart Phoenix Inverter 12V 1600VA 230V")
        self._dbusservice.add_path('/Devices/0/ServiceName', servicename)
        self._dbusservice.add_path('/Devices/0/Serial', get_serial())
        self._dbusservice.add_path('/Devices/0/VregLink', None, itemtype=vregtype)

        self._dbusservice.add_path ('/Tasmota', 0, writeable = True)

        for path, settings in self._paths.items():
            self._dbusservice.add_path(
                path, settings['initial'], writeable=True, onchangecallback=self._handlechangedvalue)

        self._dbusservice.register()
        GLib.timeout_add(1000, self._update)

    def _update(self):
        self._dbusservice['/Tasmota'] = 1
        global config
        config = get_config()

        dbus_conn = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()
        battery_voltage = VeDbusItemImport(dbus_conn, 'com.victronenergy.system', '/Dc/Battery/Voltage')
        inverter.battery_voltage = battery_voltage.get_value()
        #if inverter.battery_voltage == None:
        #    inverter.battery_voltage = 11.65

        #inverter.battery_voltage = round(random.uniform(11.6, 14.65),2)

        #else:
        #    if float(inverter.battery_voltage) < 14:
        #        inverter.battery_voltage = float(inverter.battery_voltage) + 1
        #    elif float(inverter.battery_voltage) >= 14 and float(inverter.battery_voltage) <= 14.65:
        #        inverter.battery_voltage = float(inverter.battery_voltage) + 0.01
        #else:
        #    if float(inverter.battery_voltage) < 12:
        #        inverter.battery_voltage = float(inverter.battery_voltage) + 0.01
            #elif float(inverter.battery_voltage) >= 14 and float(inverter.battery_voltage) <= 14.65:
            #    inverter.battery_voltage = float(inverter.battery_voltage) + 0.01

        self._dbusservice['/Ac/Out/L1/F'] = inverter.frequency
        self._dbusservice['/Ac/Out/L1/V'] = inverter.voltage
        self._dbusservice['/Ac/Out/L1/I'] = inverter.current
        self._dbusservice['/Ac/Out/L1/P'] = inverter.power
        self._dbusservice['/Ac/Out/L1/S'] = inverter.apparent_power

        self._dbusservice["/Ac/L1/Current"] = inverter.current
        self._dbusservice["/Ac/L1/Power"] = inverter.power
        self._dbusservice["/Ac/L1/Voltage"] = inverter.voltage

        self._dbusservice["/Dc/0/Voltage"] = inverter.battery_voltage

        dc_current = round(float(inverter.power) / float(inverter.battery_voltage), 2)
        self._dbusservice["/Dc/0/Current"] = -dc_current

        mode, state = inverter.get_mode_and_state()
        self._dbusservice['/Mode'] = mode
        self._dbusservice['/State'] = state

        #alarms
        if inverter.temperature > float(get_high_temperature_limit()):
            self._dbusservice['/Alarms/HighTemperature'] = 1
        else:
            self._dbusservice['/Alarms/HighTemperature'] = 0

        if inverter.power > get_overload_limit():
            self._dbusservice['/Alarms/Overload'] = 1
        else:
            self._dbusservice['/Alarms/Overload'] = 0

        if inverter.battery_voltage is not None:
            if float(inverter.battery_voltage) < float(get_low_voltage_limit()):
                self._dbusservice['/Alarms/LowVoltage'] = 1
            else:
                self._dbusservice['/Alarms/LowVoltage'] = 0

            if float(inverter.battery_voltage) < float(get_low_battery_shutdown()):
                self._dbusservice['/Alarms/LowVoltageShutdown'] = 1
                if inverter.status != 'OFF':
                    self.tasmota_http_request(4, "VE_REG_SHUTDOWN_LOW_VOLTAGE_SET")

        index = self._dbusservice['/UpdateIndex'] + 1  # increment index
        if index > 255:  # maximum value of the index
            index = 0  # overflow from 255 to 0
        self._dbusservice['/UpdateIndex'] = index
        return True

    def _handlechangedvalue(self, path, value):
        logging.debug("someone else updated %s to %s" % (path, value))
        if path == "/Mode":
            self.tasmota_http_request(value, "GUI")
        return True  # accept the change

    def tasmota_http_request(self, value, source):
        response = None
        ip = get_tasmota_ip()
        if value == 4:
            response = requests.get(f"http://{ip}/cm?cmnd=Power%20off")
            inverter.status = "OFF"
        elif value == 2:
            if not self.can_start_due_voltage_limits():
                return
            response = requests.get(f"http://{ip}/cm?cmnd=Power%20On")
            inverter.status = "ON"
        elif value == 5:
            if not self.can_start_due_voltage_limits():
                return
            response = requests.get(f"http://{ip}/cm?cmnd=Power%20On")
            inverter.status = "ON"
        if response.status_code == 200:
            logging.info("Status changed from %s" % source)

    def can_start_due_voltage_limits(self):
        if float(inverter.battery_voltage) < float(get_low_voltage_limit()) and self._dbusservice.__getitem__('/Alarms/LowVoltageShutdown') == 0:
            logging.info("Cannot turn on the device, low battery restart and alarm has not been reached")
            return False
        if self._dbusservice.__getitem__('/Alarms/LowVoltageShutdown') == 1 and float(inverter.battery_voltage) < float(get_charge_detected()):
            logging.info("Cannot turn on the device, shutdown detected for low battery and battery voltage has no reached the charged voltage")
            return False
        if self._dbusservice.__getitem__('/Alarms/LowVoltageShutdown') == 1:
            self._dbusservice['/Alarms/LowVoltageShutdown'] = 0
        return True

def main():
    global config
    config = get_config()

    # set logging level to include info level entries
    level = logging.INFO
    if get_debug():
        level = logging.DEBUG
    logging.basicConfig(level=level)
    logging.info (">>>>>>>>>>>>>>>> Tasmota Inverter Starting <<<<<<<<<<<<<<<<")

    get_topics()
    client = mqtt.Client(get_mqtt_name())  # create new instance
    client.on_disconnect = on_disconnect
    client.on_connect = on_connect
    client.on_message = on_message

    connect_broker(client)

    thread.daemon = True  # allow the program to quit

    from dbus.mainloop.glib import DBusGMainLoop
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    pvac_output = DbusDummyService(
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
            '/Alarms/LowVoltage': {'initial': 0 },
            '/Alarms/HighTemperature': {'initial': 0},
            '/Alarms/Overload': {'initial': 0},
            '/Alarms/LowVoltageShutdown': {'initial': 0},
            '/Mode': {'initial': 2},
            '/State': {'initial': 0},


            '/Settings/Tasmota/Setup/TasmotaIp': {'initial': get_tasmota_ip()},

            '/Settings/Tasmota/MQTTBroker/Address': {'initial': get_mqtt_address()},
            '/Settings/Tasmota/MQTTBroker/Port': {'initial': get_mqtt_port()},
            '/Settings/Tasmota/MQTTBroker/Name': {'initial': get_mqtt_name()},

            '/Settings/Tasmota/Warnings/HighTemperature': {'initial': get_high_temperature_limit()},
            '/Settings/Tasmota/Warnings/Overload': {'initial': get_overload_limit()},
            '/Settings/Tasmota/Warnings/LowVoltage': {'initial': get_low_voltage_limit()},

            '/Settings/Tasmota/Options/LowBatteryShutdown': {'initial': get_low_battery_shutdown()},
            '/Settings/Tasmota/Options/ChargeDetected': {'initial': get_charge_detected()},

            '/Settings/Tasmota/Topics/L1': {'initial': get_topic_option("L1")},
            '/Settings/Tasmota/Topics/CONFIG': {'initial': get_topic_option("CONFIG")},
            '/Settings/Tasmota/Topics/LWT': {'initial': get_topic_option("LWT")},


            '/UpdateIndex': {'initial': 0}
        })

    logging.info('Connected to dbus, and switching over to GLib.MainLoop() (= event based)')
    mainloop = GLib.MainLoop()
    mainloop.run()


if __name__ == "__main__":
    main()
