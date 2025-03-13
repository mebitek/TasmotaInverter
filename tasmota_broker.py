import logging

import paho.mqtt.client as mqtt


class Broker:
    def __init__(self, name, address, port):
        self.name = name
        self.address = address
        self.port = port

        self.client = mqtt.Client(self.name)

        self.topic_category = {}

        self.client.on_disconnect = self.on_disconnect
        self.client.on_connect = self.on_connect

    def connect_broker(self):

        try:
            logging.info('connecting to MQTTBroker ' + self.address + ' on Port ' + str(self.port))

            if self.address is not None:
                self.client.connect(self.address, port=self.port)  # connect to broker
                self.client.loop_start()
            else:
                logging.error("couldn't connect to MQTT Broker")
        except Exception as e:
            logging.exception("Error in Connect to Broker")
            logging.exception(e)
            logging.debug("Retrying...")
            self.connect_broker()

    def on_message(self, on_message):
        self.client.on_message = on_message

    def on_disconnect(self, client, userdata, rc):
        logging.info("Client Got Disconnected")
        if rc != 0:
            logging.info('Unexpected MQTT disconnection. Will auto-reconnect')
        else:
            logging.info('rc value:' + str(rc))
        try:
            logging.info("Trying to Reconnect")
            self.connect_broker()
        except Exception as e:
            logging.exception("Error in Retrying to Connect with Broker")
            logging.exception(e)


    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("Connected to MQTT Broker!")
            # subscribe to all topics we have in dict
            if len(self.topic_category) > 0:
                for topic in self.topic_category.keys():
                    client.subscribe(topic)
                    logging.info("Subscribed to: " + topic)
            else:
                logging.info("No Topic to subscribe, please configure in config.ini")
        else:
            logging.info("Failed to connect, return code %d\n", rc)