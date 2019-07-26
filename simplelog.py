#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Evgeniy Shumilov <evgeniy.shumilov@gmail.com>

import os
from datetime import datetime


class SimpleLog:

    LevelName = {0: 'EMERGENCY', 1: 'ALERT', 2: 'CRITICAL', 3: 'ERROR',
                 4: 'WARNING', 5: 'NOTICE', 6: 'INFO', 7: 'DEBUG'}
    LevelNum = {'EMERGENCY': 0, 'ALERT': 1, 'CRITICAL': 2, 'ERROR': 3,
                'WARNING': 4, 'NOTICE': 5, 'INFO': 6, 'DEBUG': 7}

    def __init__(self, loglevel='INFO'):
        self.llevel = loglevel
        self.debug = self.d
        self.info = self.i
        self.notice = self.n
        self.warn = self.w
        self.warning = self.w
        self.error = self.e
        self.critical = self.c
        self.alert = self.a
        self.df = '%Y.%d.%m %H:%M:%S'
        if type(self.llevel) is str and self.llevel in self.LevelNum.keys():
            self.llevel = self.LevelNum[self.llevel]
        else:
            print('ERROR: Wrong or unknown log level')
            os.sys.exit(1)

    def __simple__(self, record):
        if record:
            s = '%s [%s]: ' % (record['datetime'],
                               record['level_name'][0].upper())
            s += record['message']
            print(s)

    def log(self, obj=None, level='INFO'):
        if obj:
            if type(level) is str:
                if level.upper() in self.LevelNum.keys():
                    level = self.LevelNum[level.upper()]
            else:
                if type(level) is int:
                    # Levels higher than 7 are custom levels
                    if level not in range(0, 255):
                        pass
            if level <= self.llevel:
                # Appending log level to objects
                record = {}
                if level in range(0, 8):
                    record['level_name'] = self.LevelName[level]
                else:
                    record['level_name'] = 'CUSTOM'
                record['level'] = level
                if type(obj) is str:
                    record['message'] = obj
                elif type(obj) is dict:
                    msg = obj.get('message')
                    if msg:
                        record['message'] = msg
                # Setting datetime to current if not exists
                if 'datetime' not in record.keys():
                    record['datetime'] = datetime.now().strftime(self.df)
                if 'message' in record.keys():
                    self.__simple__(record)

    def a(self, obj=None):
        self.log(obj, level=1)

    def c(self, obj=None, exitcode=None):
        self.log(obj, level=2)
        if exitcode:
            os.sys.exit(exitcode)

    def e(self, obj=None):
        self.log(obj, level=3)

    def w(self, obj=None):
        self.log(obj, level=4)

    def n(self, obj=None):
        self.log(obj, level=5)

    def i(self, obj=None):
        self.log(obj, level=6)

    def d(self, obj=None):
        self.log(obj, level=7)

# vim: syntax=python tabstop=4 expandtab shiftwidth=4 softtabstop=4
