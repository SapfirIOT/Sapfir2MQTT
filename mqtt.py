#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import yaml
import json
import asyncio
import paho.mqtt.client as mqtt
from simplelog import SimpleLog

sys = os.sys


class Mqtt:

    def __init__(self):
        self.mqttConfigLoad()
        self.mqttConfigCheck()
        self.l = SimpleLog('DEBUG')
        self.mqttClientConnectSetup()

    def mqttConfigLoad(self):
        # trying to load config
        if os.path.exists(str('config.yml')):
            with open(str('config.yml'), 'r') as conffile:
                try:
                    c = yaml.safe_load(conffile)
                except yaml.YAMLError as e:
                    print(e)
        else:
            print('FATAL ERROR: Fail to found config file config.yml')
            sys.exit(1)
        self.confMQTT = c.get('mqtt')
        if not self.confMQTT:
            print('FATAL ERROR: Fail to find config section "mqtt"')
            sys.exit(2)

    # setting default values if not exists
    def mqttConfigCheck(self):
        if not self.confMQTT.get('host'):
            self.confMQTT['host'] = '127.0.0.1'
        if not self.confMQTT.get('port'):
            self.confMQTT['port'] = 1883
        if not self.confMQTT.get('user'):
            self.confMQTT['user'] = ''
        if not self.confMQTT.get('password'):
            self.confMQTT['password'] = ''

    # setting up handlers for actions
    def mqttClientConnectSetup(self):
        self.client = mqtt.Client()
        self.client.username_pw_set(self.confMQTT['user'],
                                    self.confMQTT['password'])
        self.connection = False
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_socket_open = self.on_socket_open
        self.client.on_socket_close = self.on_socket_close
        self.client.on_socket_register_write = self.on_socket_register_write
        self.client.on_socket_unregister_write = self.on_socket_unregister_write

    def on_socket_open(self, client, userdata, sock):
        """ called just after the socket was opend
            client:     the client instance for this callback
            userdata:   the private user data as set in Client() or userdata_set()
            sock:       the socket which was just opened
        """
        def cb():
            client.loop_read()
        self.loopMQTT.add_reader(sock, cb)
        self.misc = self.loopMQTT.create_task(self.misc_loop())

    def on_socket_close(self, client, userdata, sock):
        """ called just before the socket is closed
            client:     the client instance for this callback
            userdata:   the private user data as set in Client() or userdata_set()
            sock:       the socket which is about to be closed
        """
        self.loopMQTT.remove_reader(sock)
        self.misc.cancel()

    def on_socket_register_write(self, client, userdata, sock):
        """ called when the socket needs writing but can't
            client:     the client instance for this callback
            userdata:   the private user data as set in Client() or userdata_set()
            sock:       the socket which should be registered for writing
        """
        def cb():
            client.loop_write()
        self.loopMQTT.add_writer(sock, cb)

    def on_socket_unregister_write(self, client, userdata, sock):
        """ called when the socket doesn't need writing anymore
            client:     the client instance for this callback
            userdata:   the private user data as set in Client() or userdata_set()
            sock:       the socket which should be unregistered for writing
        """
        self.loopMQTT.remove_writer(sock)

    async def misc_loop(self):
        while self.client.loop_misc() == mqtt.MQTT_ERR_SUCCESS:
            try:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break

    def on_connect(self, client, userdata, flags, rc):
        """ called when the broker responds to our connection
            client:     the client instance for this callback
            userdata:   the private user data as set in Client() or userdata_set()
            flags:      response flags sent by the broker
            rc:         the connection result
        """
        if rc == 0:
            self.connection = True
            self.l.info("Connected to mqtt server")
            self.client.subscribe("/sapfir/#")

    def on_message(self, client, userdata, msg):
        """called when a message has been received on a topic that the client subscribes to
            client:     the client instance for this callback
            userdata:   the private user data as set in Client() or userdata_set()
            msg:    an instance of MQTTMessage
        """
        self.l.debug("Got MQTT message: %s %s" % (msg.topic,
                                                  json.loads(msg.payload)))

    def publish(self, topic, value):
        if value is None:
            self.client.publish(topic, None)
        elif not type(value) in (str, int, float):
            self.client.publish(topic, str(value))
        else:
            self.client.publish(topic, value)

    def startMQTTClient(self):
        self.loopMQTT = asyncio.get_event_loop()
        self.loopMQTT.run_until_complete(self.startClient())

    async def startClient(self):
        self.l.i('Connecting to the MQTT server %s' % self.confMQTT['host'])
        self.client.connect(self.confMQTT['host'], self.confMQTT['port'])
        # Wait for connection
        while not self.connection:
            await asyncio.sleep(0.1)

# vim: syntax=python tabstop=4 expandtab shiftwidth=4 softtabstop=4
