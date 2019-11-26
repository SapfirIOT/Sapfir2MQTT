#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import yaml
import json
import socket
import asyncio
from time import time
from simplelog import SimpleLog
import ast

sys = os.sys


class SapfirLocal:

    def __init__(self):
        self.udpConfigLoad()
        self.udpConfigCheck()
        self.l = SimpleLog(self.confSL['loglevel'])

        self.udpCreateSocket()

    def udpConfigLoad(self):
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
        self.confSL = c.get('sapfirlocal')
        if not self.confSL:
            print('FATAL ERROR: Fail to find config section "sapfirlocal"')
            sys.exit(2)

    # setting default values if not exists
    def udpConfigCheck(self):
        self.port = 30300
        if not self.confSL.get('host'):
            self.confSL['host'] = '0.0.0.0'
        if not self.confSL.get('pkgmaxlen'):
            self.confSL['pkgmaxlen'] = 4096
        if not self.confSL.get('processing_interval'):
            self.confSL['processing_interval'] = 0.05
        if not self.confSL.get('loglevel'):
            self.confSL['loglevel'] = 'INFO'
        if not self.confSL['addresses']:
            self.confSL['addresses'] = {}
        if not self.confSL['tokens']:
            self.confSL['tokens'] = {}
        self.signals = {}
        self.requests = {}

    def udpCreateSocket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(False)
        self.sock.bind((self.confSL['host'], self.port))
        self.sendsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def udpRecieve(self, fut=None, registed=False):
        """ receiving packets from devices"""
        fd = self.sock.fileno()
        if fut is None:
            fut = self.loopUDP.create_future()
        if registed:
            self.loopUDP.remove_reader(fd)
        try:
            data, addr = self.sock.recvfrom(self.confSL['pkgmaxlen'])
        except (BlockingIOError, InterruptedError):
            self.loopUDP.add_reader(fd, self.udpRecieve, fut, True)
        else:
            fut.set_result((data, addr))
            if data != b'Discovery':
                self.l.debug('Got data from %s: %s' % (addr[0], data))
        return fut

    def udpSend(self, data, addr):
        """ sending packet to device
            data:   content for sending
            addr:   device address (ip, port)
        """
        if data and addr:
            plength = self.sendsock.sendto(data.encode(), addr)
            if plength:
                return True
            else:
                return False
        else:
            return False

    async def udpServe(self):
        """ listening devices, prossesing of the received packets"""
        while True:
            data, addr = await self.udpRecieve()
            try:
                data = data.replace(b'\n', b'')
                decrypted_data = json.loads(data)
                if 'header' in decrypted_data:
                    decrypted_data = decrypted_data['header']
            except:
                if data != b'Discovery':
                    self.l.warn('Got unknown format of packet from %s: %s' %
                                (addr[0], data))
            else:
                self.processPacket(addr, decrypted_data)
            await asyncio.sleep(0.1)

    def startUDPServer(self):
        if not hasattr(self, 'loop'):
            self.loopUDP = asyncio.get_event_loop()
        try:
            self.loopUDP.run_until_complete(self.udpServe())
        finally:
            self.loopUDP.close()

    def getToken(self, dev_serial):
        if dev_serial not in self.confSL['tokens']:
            self.l.warn("Token for device %s wasn't got yet" % dev_serial)
            return False
        else:
            return self.confSL['tokens'][dev_serial]

    def getAddress(self, dev_serial):
        if dev_serial not in self.confSL['addresses']:
            self.l.warn("Haven't got ip address for device %s yet" % dev_serial)
            return False
        else:
            addr = self.confSL['addresses'][dev_serial]
            return (addr, self.port)

    def getValueSignal(self, dev_serial, signal_name):
        if self.signals[dev_serial][signal_name]['value']:
            return self.signals[dev_serial][signal_name]['value']
        else:
            return None

    def processPacket(self, addr, data):
        """ processing and saving of the received signal data
            addr:   device address (ip, port)
            data:   device data from the received packet
        """
        self.l.debug("Processing packet from %s: %s" % (addr[0], data))
        # device serial number
        dev_serial = data['id']
        # signals
        if 'data'in data:
            dev_data = data['data']
        else:
            dev_data = data

        # remember address in dictionary address (ip, port)
        self.saveAddress(dev_serial, addr)
        self.getSignals(dev_serial, dev_data)

        return dev_serial, addr, dev_data

    def getSignals(self, dev_serial, dev_data):
        """ processing data and signal data in dictionary signals
            dev_serial: device serial number
            dev_data:   signals from received packet
        """
        flagUniqId = False
        # if there is such device in dictionary signals
        if dev_serial in self.signals:
            # device signals from dictionary signals
            dev_signals = self.signals[dev_serial]
            # iterate signals in received packet
            for signal_name in dev_data:
                # received packet with token
                if signal_name == 'token':
                    # remember token in dictionary tokens
                    self.saveTokens(dev_serial, dev_data[signal_name])
                # received packet with uniq_id
                elif signal_name == 'uniq_id' and dev_data['uniq_id'] != 0:
                    flagUniqId = True
                # if there is such signal in dictionary signals[dev_serial]
                elif signal_name in dev_signals:
                    # signal value in received packet
                    value = dev_data[signal_name]
                    last_value = dev_signals[signal_name]['value']
                    # if signal value in received packet not equal to signal
                    # value from signals[dev_serial][signal_name]
                    if value != last_value:
                        last_update = \
                            self.signals[dev_serial][signal_name]['last_update']
                        self.signals[dev_serial][signal_name] = \
                            self.updateSignal(dev_serial, signal_name,
                                              last_update, last_value, value)
                else:
                    # signal value in received packet
                    value = dev_data[signal_name]
                    # remember new signal
                    self.signals[dev_serial][signal_name] = \
                        self.insertSignal(dev_serial, signal_name, value)
        else:
            dev_signals = {}
            for signal_name in dev_data:
                # received packet with token
                if signal_name == 'token':
                    # remember token in dictionary tokens
                    self.saveTokens(dev_serial, dev_data[signal_name])
                # received packet with uniq_id
                elif signal_name == 'uniq_id' and dev_data['uniq_id'] != 0:
                    flagUniqId = True
                else:
                    # signal value in received packet
                    value = dev_data[signal_name]
                    # remember new signal
                    dev_signals[signal_name] = self.insertSignal(dev_serial,
                                                                 signal_name,
                                                                 value)
            self.signals[dev_serial] = dev_signals
        # received packet with uniq_id
        if flagUniqId:
            # checking the packet for changes in values and comparing the time
            # of sending and receiving
            self.checkRequest(dev_data['uniq_id'], dev_data)

    def insertSignal(self, dev_serial, signal_name, value):
        if type(value) in (list, tuple):
            value = str(value)
        signal_data = {'last_update': time() * 1000, 'last_change': None,
                       'value': value, 'prev_value': None}
        return signal_data

    def updateSignal(self, dev_serial, signal_name, last_update,
                     last_value, value):
        signal_data = {'last_update': time() * 1000, 'last_change': last_update,
                       'value': value, 'prev_value': last_value}
        return signal_data

    def saveConfig(self):
        """ rewrite current config file (config.yml) with new values
        """
        config = {'sapfirlocal': self.confSL}
        with open('config.yml', 'w') as conffile:
            try:
                yaml.safe_dump(config, conffile)
                return True
            except yaml.YAMLError as e:
                self.l.error(e)
                return False

    def saveAddress(self, dev_serial, addr):
        """ update config when new address is received
            dev_serial: device serial number
            addr:       device address (ip, port)
        """
        if dev_serial not in self.confSL['addresses']:
            self.confSL['addresses'][dev_serial] = addr[0]
            self.l.n('Found new device with address %s' % addr[0])
            self.saveConfig()
        elif self.confSL['addresses'][dev_serial] != addr[0]:
            self.l.n('Address for device %s was changed from %s to %s' % (
                     dev_serial, self.confSL['addresses'][dev_serial], addr[0]))
            self.confSL['addresses'][dev_serial] = addr[0]
            self.saveConfig()

    def saveTokens(self, dev_serial, token):
        """ update config when new token is received
            dev_serial: device serial number
            addr:       device address (ip, port)
        """
        if dev_serial not in self.confSL['tokens']:
            self.confSL['tokens'][dev_serial] = token
            self.l.n('Got token for device %s' % dev_serial)
            self.saveConfig()
        elif self.confSL['tokens'][dev_serial] != token:
            self.l.n('Token for device %s was changed from %s to %s' % (
                     dev_serial, self.confSL['tokens'][dev_serial], token))
            self.confSL['tokens'][dev_serial] = token
            self.saveConfig()

    def sendPacket(self, dev_serial, signals={}):
        """ dev_serial: device serial number
            signals:    signals that need to change values
        """
        if signals and dev_serial and self.getToken(dev_serial) and \
                self.getAddress(dev_serial):
            # time in seconds
            time_sec = int(time())
            uniq_id = int(time() % 100 * 1000)
            req = {'command': 'management', 'id': dev_serial,
                   'uniq_id': uniq_id, 'token': self.getToken(dev_serial)}
            for signal_name in signals:
                req[signal_name] = signals[signal_name]
            # remember request in dictionary requests
            request_data = {'dev_serial': dev_serial, 'signals': signals,
                            'time': time_sec}
            self.requests[uniq_id] = request_data
            data = json.dumps(req).replace(' ', '')
            self.l.debug('Sending packet for device %s with data %s' %
                         (dev_serial, data))
            addr = self.getAddress(dev_serial)
            self.udpSend(data, addr)
        else:
            self.l.error("Fail to send data to device %s" % dev_serial)

    def checkRequest(self, uniq_id, dev_data):
        """ checking the packet for changes in values and comparing the time of
            sending and receiving
            uniq_id:    uniq_id from received packet
            dev_data:   signals from received packet
        """
        if uniq_id in self.requests:
            # get signals on uniq_id from dictionary requests
            request_signals = self.requests[uniq_id]['signals']
            request_time = self.requests[uniq_id]['time']
            for signal_name in request_signals:
                # value signal from packet not changed
                if request_signals[signal_name] != dev_data[signal_name]:
                    self.l.error("Setted value %s is failed to check" %
                                 signal_name)
            try:
                dev_time = dev_data['time']
            except:
                pass
            else:
                delta = dev_time - request_time
                # packet waiting limit exceeded
                if delta > 5:
                    self.l.e("Fail to check sended signal because of timeout")
        else:
            self.l.w("Fail to found request id (possible of other local "
                     "manamgment device)")

# vim: syntax=python tabstop=4 expandtab shiftwidth=4 softtabstop=4
