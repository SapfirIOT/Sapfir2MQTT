#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import yaml
from time import time
from mqtt import Mqtt
from simplelog import SimpleLog
from sapfirlocal import SapfirLocal
sys = os.sys


class Sapfir2MQTT(SapfirLocal, Mqtt):

    def __init__(self):
        self.appname = 'sapfir2mqtt'
        self.s2mConfigLoad()
        self.s2mConfigCheck()
        # list of signals that are not published
        self.blacklist = ['uniq_id', 'token', 'ip', 'ping', 'n', 'hp',
                          'tcp-state', 'cur-ch', 'time', 'adc', 'en-tcp',
                          's', 'hw-pb', 'fw-pb', 'pwr-in', 'pwr-brd',
                          'ble-dev', 'tb-list', 'ai-lis', 'ai-pis']
        # list of signals for which the client can change values
        self.modifablelist = ['r-dtrl', 'coff-term', 'light-en', 'tint-en',
                              'aref', 'micwnd', 'rele-wt', 'coff-ntc',
                              'led-stat', 'time-utc', 'led-adpt', 'ntc-beta',
                              'sn-btn2-en', 'ntc-res', 'mic-tm-set', 'en-log',
                              'treg-en', 'capt-ir-raw', 'cs', 'led-bright',
                              'scen', 'mts', 'upd-scen', 'tmxs2', 'tb-type',
                              'in1o', 'in2o', 'in1-inv', 'in2-inv', 'in1c',
                              'in2c', 'inrt1', 'inrt2', 'tm_rele1', 'tm_rele2',
                              'lamp_a1', 'lamp_a2', 'rele1-inv', 'rele2-inv',
                              'in1ct', 'in2ct', 'in1tc', 'in2tc', 'in1ot',
                              'in2ot', 'in1to', 'in2to', 'terev', 'thiev',
                              'tlwev', 'en-udp', 'rele1', 'rele2', 'reg-dmx-a1',
                              'reg-dmx-a2']

        # setting of logging format and level
        self.l = SimpleLog(self.confSL['loglevel'])
        self.l.info('Starting Saprir2MQTT service...')

    # parsing arguments and load config file
    def s2mConfigLoad(self):
        # trying to load config
        if os.path.exists(str('config.yml')):
            with open('config.yml', 'r') as conffile:
                try:
                    c = yaml.safe_load(conffile.read())
                except yaml.YAMLError as e:
                    print(e)
                    print('FATAL ERROR: Fail to open config config.yml')
                    sys.exit(1)
        else:
            print('FATAL ERROR: Fail to found config file config.yml')
            sys.exit(1)
        self.confSL = c.get('sapfirlocal')
        if not self.confSL:
            print('FATAL ERROR: Fail to find config section "sapfirlocal"')
            sys.exit(2)
        self.confMQTT = c.get('mqtt')
        if not self.confMQTT:
            print('FATAL ERROR: Fail to find config section "mqtt"')
            sys.exit(3)

    # setting default parameters
    def s2mConfigCheck(self):
        if not self.confSL.get('host'):
            self.confSL['host'] = '0.0.0.0'
        if not self.confSL.get('pkgmaxlen'):
            self.confSL['pkgmaxlen'] = 4096
        if not self.confSL.get('processing_interval'):
            self.confSL['processing_interval'] = 0.05
        if not self.confSL.get('loglevel'):
            self.confSL['loglevel'] = 'INFO'
        if not self.confMQTT.get('host'):
            self.confMQTT['host'] = '127.0.0.1'
        if not self.confMQTT.get('port'):
            self.confMQTT['port'] = 1883
        if not self.confMQTT.get('user'):
            self.confMQTT['user'] = ''
        if not self.confMQTT.get('password'):
            self.confMQTT['password'] = ''

    # converting value from various unsupported types into string
    def __checkValueType__(self, value):
        if value is None or value in (str, float):
            return value
        else:
            return str(value)

    # override method from class SapfirLocal
    def updateSignal(self, dev_serial, signal_name, last_update, last_value,
                     value):
        value = self.__checkValueType__(value)
        signal_data = {'last_update': time() * 1000, 'last_change': last_update,
                       'value': value, 'prev_value': last_value}
        # publish if signal is in dictionary whitelist
        if signal_name not in self.blacklist:
            topic = '/sapfir/%s/%s' % (dev_serial, signal_name)
            self.l.i('MQTT OUT: %s -> %s' % (topic, value))
            self.publish(topic, value)
        return signal_data

    # override method from class SapfirLocal
    def insertSignal(self, dev_serial, signal_name, value):
        value = self.__checkValueType__(value)
        signal_data = {'last_update': time() * 1000, 'last_change': None,
                       'value': value, 'prev_value': None}
        if signal_name not in self.blacklist:
            topic = '/sapfir/%s/%s' % (dev_serial, signal_name)
            self.l.i('MQTT OUT: %s -> %s' % (topic, value))
            self.publish(topic, value)
            signal_data['last_change'] = time() * 1000
            signal_data['last_value'] = value
        return signal_data

    # override method from calss SapfirLocal
    def saveConfig(self):
        config = {'sapfirlocal': self.confSL, 'mqtt': self.confMQTT}
        with open('config.yml', 'w') as conffile:
            try:
                yaml.safe_dump(config, conffile)
                return True
            except yaml.YAMLError as e:
                self.l.error(e)
                return False

    # override method from class Mqtt
    def on_message(self, client, userdata, msg):
        try:
            sign_arr = (str(msg.topic)).split('/')
            signal_name = sign_arr[-1]
            dev_serial = int(sign_arr[-2])
            value = json.loads(msg.payload.decode('utf-8'))
            value = self.__checkValueType__(value)
            # send request to change value if signal is in modifablelist
            if signal_name in self.modifablelist:
                lastsignal = self.signals.get(dev_serial)
                if lastsignal:
                    lvalue = lastsignal.get(signal_name)['value']
                    if value != lvalue:
                        self.l.i('MQTT IN:  /sapfir/%s/%s <- %s' % (dev_serial,
                                 signal_name, value))
                        self.sendPacket(dev_serial, {signal_name: value})
                else:
                    self.sendPacket(dev_serial, {signal_name: value})
            elif signal_name not in self.blacklist:
                last_value = self.getValueSignal(dev_serial, signal_name)
                if value != last_value and last_value is not None:
                    self.publish(msg.topic, last_value)
        except Exception as e:
            self.l.error(e)

    def startSapfir2MQTT(self):
        self.mqttConfigLoad()
        self.mqttConfigCheck()
        self.mqttClientConnectSetup()
        self.startMQTTClient()
        self.udpConfigLoad()
        self.udpConfigCheck()
        self.udpCreateSocket()
        self.startUDPServer()

if __name__ == "__main__":
    server = Sapfir2MQTT()
    server.startSapfir2MQTT()

# vim: syntax=python tabstop=4 expandtab shiftwidth=4 softtabstop=4
