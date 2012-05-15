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
    def _initialize(cls, conf):
        # confは無視
        if cls.initialized:
            return tagged(u'OK', None)
        e = os.environ
        f = {}
        for k in e:
            f[unicode(k)] = unicode(e[k])
        cls.os_env = f
        return tagged(u'OK', None)

    @classmethod
    def _finalize(cls):
        if cls.initialized:
            cls.initialized = False
        return None

    @classmethod
    def _create(cls, mode_param):
        mode, param = mode_param
        if not mode == "read":
            raise Error("bad mode")
        if cls.the_instance is None:
            cls.the_instance = OsEnv()
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

    def _sync(self):
        pass
    def _close(self):
        pass
    def _begin(self):
        pass
    def _commit(self):
        pass
    def _cancel(self):
        pass



from caty.command import Command

Facility = OsEnv

class MgmntInitialize(Command):
    def execute(self, config):
        return Facility._initialize(config)

class MgmntFinalize(Command):
    def execute(self):
        return Facility._finalize()

class MgmntCreate(Command):
    def execute(self, mod_param):
        return Facility._create(mod_param)

# リクエスタのメソッド、すべてアクセッサ

class List(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        return self.arg0.list()

class Get(Command):
    def setup(self, arg0, name):
        self.arg0 = arg0
        self._name = name

    def execute(self):
        return self.arg0.get(self._name)

class Exists(Command):
    def setup(self, arg0, name):
        self.arg0 = arg0
        self._name = name

    def execute(self):
        return self.arg0.exists(self._name)

