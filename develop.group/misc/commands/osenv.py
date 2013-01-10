# -*- coding: utf-8 -*- 
# 
#
import os
from caty.jsontools import tagged

class OsEnv(object):
    initialized = False
    the_instance = None
    os_env = None

    @classmethod
    def initialize(cls, app_instance, config):
        # app_instance, configは無視
        if cls.initialized:
            return None
        e = os.environ
        f = {}
        for k in e:
            f[unicode(k)] = unicode(e[k])
        cls.os_env = f
        cls.the_instance = OsEnv()
        cls.initialized = True
        print "initialized"

    @classmethod
    def finalize(cls, app_instance):
        if cls.initialized:
            os_env = None
            cls.the_instance = None
            cls.initialized = False
            print "finalized"

    @classmethod
    def create(cls, app_instance, sys_param=None, mode="read", usr_param=None):
        if not mode == "read":
            raise Exception("bad mode")
        return cls.the_instance

    def __init__(self):
        pass
        
    def list(self):
        return OsEnv.os_env.keys()

    def get(self, name):
        return OsEnv.os_env.get(name, None)

    def exists(self, name):
        if name in OsEnv.os_env:
            return tagged(u"OK", name)
        else:
            return tagged(u"NG", name)


    # トランザクション管理は不要

# 以下はブリッジングコマンド


from caty.command import Command

Facility = OsEnv

class Initialize(Command):
    def setup(self, config=None):
        self.config = config

    def execute(self, app_instance):
        return Facility.initialize(app_instance, self.config)

class Finalize(Command):
    def execute(self, app_instance):
        return Facility.finalize(app_instance)

class Create(Command):
    def setup(self, sys_param=None, mode="read", usr_param=None):
        self.sys_param = sys_param
        self.mode = mode
        self.usr_param = usr_param

    def execute(self, app_instance):
        return Facility.create(app_instance, self.sys_param, self.mode, self.usr_param)

# リクエスタのメソッド、すべてアクセッサ

class List(Command):
    def execute(self):
        return self.arg0.list()

class Get(Command):
    def setup(self, name):
        self._name = name

    def execute(self):
        return self.arg0.get(self._name)

class Exists(Command):
    def setup(self, name):
        self._name = name

    def execute(self):
        return self.arg0.exists(self._name)

