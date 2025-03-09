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
from vedbus import VeDbusService
import paho.mqtt.client as mqtt
import os
import json
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
import platform
from gi.repository import GLib
import _thread as thread   # for daemon = True  / Python 3.x

sys.path.insert(1, os.path.join(
    os.path.dirname(__file__), '../ext/velib_python'))

os.makedirs('/var/log/dbus-tasmota-inverter', exist_ok=True) 
logging.basicConfig(
    format = '%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S',
    level = logging.DEBUG,
    handlers = [
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = RotatingFileHandler('/var/log/dbus-tasmota-inverter/current.log', maxBytes=200000, backupCount=5)
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.info("Service Startup")

def getConfig():
    config = configparser.ConfigParser()
    config.read("%s/config.ini" % (os.path.dirname(os.path.realpath(__file__))))
    return config

config = getConfig()

def getMQTTName():
    return config.get('MQTTBroker','name', fallback = 'MQTT_to_Inverter')

def getMQTTAddress():
    address = config.get('MQTTBroker','address', fallback = None)
    if address == None:
        logger.error("No MQTT Broker set in config.ini")
        return address
    else:
        return address

def getHighTemperatureLimit():
    return config.get('Warnings','HighTemperature', fallback = 65)

def getOverloadLimit():
    overload = float(config.get('Warnings','Overload', fallback = 1500))
    return overload * 0.1 + overload

def getProductName():
    return config.get('Setup','Name', fallback = "Tasmota Inverter")

def getMQTTPort():
    port = config.get('MQTTBroker','port', fallback = None)
    if port != None:
        return int(port)
    else:
        return 1883

def connectBroker():
    broker_address = getMQTTAddress()
    broker_port = getMQTTPort()

    try:
        logger.info('connecting to MQTTBroker ' + broker_address + ' on Port ' + str(broker_port))

        if broker_address != None:
            client.connect(broker_address, port=broker_port)  # connect to broker
            client.loop_start()
        else:
            logger.error("couldn't connect to MQTT Broker")
    except Exception as e:
        logger.exception("Error in Connect to Broker")
        logger.exception(e)
        logger.debug("Retrying...")
        connectBroker()

def getPosition():
    return int(config.get('Setup','Inverter_Position', fallback = 0))

# prepare dict
tasmota_devices = {}
topic_category = {}

# get topics for a single phase
def getTopic(phase):
    strtopics = config.get('Topics', phase, fallback ='')
    if strtopics != '':
        topics = strtopics.split(',')
        for topic in topics:
            t = topic.strip()
            if t not in tasmota_devices:
                if phase == 'CONFIG':
                    tasmota_devices[t] = {'status': 'OFF'}
                else:
                    tasmota_devices[t] = {'phase' : phase, 'power': 0, 'voltage': 0, 'current': 0, 'total': 0, 'temperature': 0}

                logger.info("Topic added to " + phase + ": " + t)
                topic_category[t] = phase
            else:
                logger.info("Cannot add topic " + t + " as it is already added to " + tasmota_devices[t]['phase'])

# get topics for all phases
def getTopics():
    getTopic('L1')
    getTopic('CONFIG')
    
# MQTT Abfragen:
def on_disconnect(client, userdata, rc):
    logger.info("Client Got Disconnected")
    if rc != 0:
        logger.info('Unexpected MQTT disconnection. Will auto-reconnect')

    else:
        logger.info('rc value:' + str(rc))

    try:
        logger.info("Trying to Reconnect")
        connectBroker()
    except Exception as e:
        logger.exception("Error in Retrying to Connect with Broker")
        logger.exception(e)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT Broker!")

        # subscribe to all topics we have in dict
        if len(tasmota_devices) > 0:
            for topic in tasmota_devices.keys():
                client.subscribe(topic)
                logger.info("Subscribed to: " + topic)
        else:
            logger.info("No Topic to subscribe, please configure in config.ini")
    else:
        logger.info("Failed to connect, return code %d\n", rc)

def on_message(client, userdata, msg):
    try:

        logger.debug('Incoming message from: ' + msg.topic)

        # write the values into dict
        if msg.topic in tasmota_devices:
            jsonpayload = json.loads(msg.payload)
            if topic_category[msg.topic] == 'CONFIG':
                tasmota_devices[msg.topic]['status'] = jsonpayload['POWER']
            else:
                tasmota_devices[msg.topic]['power'] = float(jsonpayload["ENERGY"]["Power"])
                tasmota_devices[msg.topic]['current'] = float(jsonpayload["ENERGY"]["Current"])
                tasmota_devices[msg.topic]['voltage'] = float(jsonpayload["ENERGY"]["Voltage"])
                tasmota_devices[msg.topic]['total'] = float(jsonpayload["ENERGY"]["Total"])
                tasmota_devices[msg.topic]['temperature'] = float(jsonpayload["ESP32"]["Temperature"])


        else:
            logger.info("Topic not in configurd topics. This shouldn't be happen")

    except Exception as e:
        logger.exception("Error in handling of received message payload: " + msg.payload)
        logger.exception(e)

# Konfiguration MQTT
getTopics()
client = mqtt.Client(getMQTTName())  # create new instance
client.on_disconnect = on_disconnect
client.on_connect = on_connect
client.on_message = on_message

class DbusDummyService:
    def __init__(self, servicename, deviceinstance, paths, productname='Tasmota Inverter', connection='MQTT'):
        self._dbusservice = VeDbusService(servicename, register=False)
        self._paths = paths

        logger.debug("%s /DeviceInstance = %d" %
                      (servicename, deviceinstance))

        productname = getProductName()

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path(
            '/Mgmt/ProcessVersion', 'Unkown version, and running on Python ' + platform.python_version())
        self._dbusservice.add_path('/Mgmt/Connection', connection)

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', deviceinstance)
        # value used in ac_sensor_bridge.cpp of dbus-cgwacs
        self._dbusservice.add_path('/ProductId', 16)
        self._dbusservice.add_path('/ProductName', productname)
        self._dbusservice.add_path('/FirmwareVersion', 0.1)
        self._dbusservice.add_path('/HardwareVersion', 0)
        self._dbusservice.add_path('/Connected', 1)

        for path, settings in self._paths.items():
            self._dbusservice.add_path(
                path, settings['initial'], writeable=True, onchangecallback=self._handlechangedvalue)

        self._dbusservice.register()
        GLib.timeout_add(1000, self._update)

    def _signOfLife(self):
        logger.info("Service is running")

    def _update(self):

        vals = {'L1':{'v':0,'c':0,'p':0, 't':0},
                'total':{'v':0,'c':0,'p':0},
                'status': "OFF"}

        for tasmota_device in tasmota_devices.values():
            # the voltage is a bit a problem here, as it can differ from tasmota device to device
            # so we take the first best voltage
            if 'status' in tasmota_device:
                vals['status'] = tasmota_device['status']
            else:
                if tasmota_device['voltage'] != 0:
                    vals[tasmota_device['phase']]['v'] = tasmota_device['voltage']
                vals[tasmota_device['phase']]['c'] += tasmota_device['current']
                vals[tasmota_device['phase']]['p'] += tasmota_device['power']
                # this is the sum power per phase
                vals['total']['p'] += tasmota_device['power']
                vals[tasmota_device['phase']]['t'] = tasmota_device['temperature']

                self._dbusservice['/Ac/Out/L1/V'] = vals['L1']['v']
                self._dbusservice['/Ac/Out/L1/I'] = vals['L1']['c']
                self._dbusservice['/Ac/Out/L1/P'] = vals['L1']['p']
                if vals[tasmota_device['phase']]['t'] > float(getHighTemperatureLimit()):
                    self._dbusservice['/Alarms/HighTemperature'] = 1
                else:
                    self._dbusservice['/Alarms/HighTemperature'] = 0

        if vals['status'] == 'ON':
            if vals['L1']['p'] > 15:
                self._dbusservice['/State'] = 9
                self._dbusservice['/Mode'] = 2
            else:
                self._dbusservice['/State'] = 1
                self._dbusservice['/Mode'] = 5
        else:
            self._dbusservice['/State'] = 0
            self._dbusservice['/Mode'] = 4

        if vals['L1']['p'] > getOverloadLimit():
            self._dbusservice['/Alarms/Overload'] = 1
        else:
            self._dbusservice['/Alarms/Overload'] = 0

        index = self._dbusservice['/UpdateIndex'] + 1  # increment index
        if index > 255:   # maximum value of the index
            index = 0       # overflow from 255 to 0
        self._dbusservice['/UpdateIndex'] = index
        return True

    def _handlechangedvalue(self, path, value):
        logger.debug("someone else updated %s to %s" % (path, value))
        return True  # accept the change


def main():

    connectBroker()

    thread.daemon = True  # allow the program to quit

    from dbus.mainloop.glib import DBusGMainLoop
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    pvac_output = DbusDummyService(
        servicename='com.victronenergy.inverter.tasmota',
        deviceinstance=0,
        paths={
            '/Ac/Power': {'initial': 0},
            '/Ac/Out/L1/V': {'initial': 0},
            '/Ac/Out/L1/I': {'initial': 0},
            '/Ac/Out/L1/P': {'initial': 0},
            '/Alarms/HighTemperature': {'initial': 0},
            '/Alarms/Overload': {'initial': 0},
	        '/Mode': {'initial': 2 },
            '/State': {'initial': 0 },
            '/UpdateIndex': {'initial': 0},
        })

    logging.info('Connected to dbus, and switching over to GLib.MainLoop() (= event based)')
    mainloop = GLib.MainLoop()
    mainloop.run()


if __name__ == "__main__":
    main()
