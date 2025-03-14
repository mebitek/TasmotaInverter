import configparser
import logging
import os
import shutil


class TasmotaConfig:
    def __init__(self):
        self.config = configparser.ConfigParser()
        config_file = "%s/../conf/tasmota_config.ini" % (os.path.dirname(os.path.realpath(__file__)))
        if not os.path.exists(config_file):
            sample_config_file = "%s/config.sample.ini" % (os.path.dirname(os.path.realpath(__file__)))
            shutil.copy(sample_config_file, config_file)
        self.config.read("%s/../conf/tasmota_config.ini" % (os.path.dirname(os.path.realpath(__file__))))

    def get_product_name(self):
        return self.config.get('Setup', 'Name', fallback="Tasmota Inverter")

    def get_serial(self):
        return self.config.get('Setup', 'Serial', fallback="XXX")

    def get_tasmota_ip(self):
        return self.config.get("Setup", "TasmotaIp", fallback="127.0.0.1")

    def get_inverter_name(self):
        return self.config.get("Setup", "Name", fallback="Tasmota Inverter")

    def get_inverter_serial(self):
        return self.config.get("Setup", "Serial", fallback="000000")

    def get_debug(self):
        val = self.config.get("Setup", "debug", fallback=False)
        if val == "true":
            return True
        else:
            return False

    def get_mqtt_address(self):
        address = self.config.get('MQTTBroker', 'address', fallback=None)
        if address is None:
            logging.error("No MQTT Broker set in config.ini")
            return address
        else:
            return address

    def get_mqtt_port(self):
        port = self.config.get('MQTTBroker', 'port', fallback=None)
        if port is not None:
            return int(port)
        else:
            return 1883

    def get_mqtt_name(self):
        return self.config.get('MQTTBroker', 'name', fallback='MQTT_to_Inverter')

    def get_high_temperature_limit(self):
        return self.config.get('Warnings', 'HighTemperature', fallback=65)

    def get_overload_limit(self):
        return float(self.config.get('Warnings', 'Overload', fallback=1500))

    def get_low_voltage_limit(self):
        return self.config.get('Warnings', 'LowVoltage', fallback=10.8)

    def get_low_battery_shutdown(self):
        return self.config.get('Options', 'LowBatteryShutdown', fallback=9.30)

    def get_charge_detected(self):
        return self.config.get('Options', 'ChargeDetected', fallback=14.00)

    def get_topic_option(self, topic):
        return self.config.get('Topics', topic)

    def write_to_config(self, value, path, key):
        logging.debug("Writing config file %s %s " % (path, key))
        self.config[path][key] = str(value)
        with open("%s/../conf/tasmota_config.ini" % (os.path.dirname(os.path.realpath(__file__))), 'w') as configfile:
            self.config.write(configfile)

    @staticmethod
    def get_version():
        with open("%s/version" % (os.path.dirname(os.path.realpath(__file__))), 'r') as file:
            return file.read()
