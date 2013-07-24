from caty.core.facility import Facility, READ
from caty.core.exception import *
import caty.jsontools.selector as selector
from caty.jsontools import pp

class DefaultStorage(Facility):
    __db__ = {}
    def __init__(self, mode, system_param):
        Facility.__init__(self, mode)
        self.dbname = system_param
        if system_param not in DefaultStorage.__db__:
            DefaultStorage.__db__[system_param] = {}

    @classmethod
    def initialize(cls, app_instance, config):
        pass

    @classmethod
    def instance(cls, app_instance, system_param):
        i = DefaultStorage(READ, system_param)
        i.app = app_instance
        return i

    @classmethod
    def finalize(cls, app):
        pass

    def create(self, mode, user_param=u'default-collection'):
        obj = Facility.create(self, mode)
        if ':' in user_param:
            mod, user_param = user_param.split(':', 1)
        else:
            mod = None
        obj.collname = user_param
        self.module_name = mod
        if user_param not in DefaultStorage.__db__[self.dbname]:
            DefaultStorage.__db__[self.dbname][user_param] = {}
        return obj

    def clone(self):
        return self

    @property
    def db(self):
        return DefaultStorage.__db__[self.dbname][self.collname]

    def lookup(self, k):
        try:
            return self.db[k]
        except:
            throw_caty_exception(u'NotFound', pp(k))

    def get(self, k, p=None):
        try:
            r = self.db[k]
            if not p:
                return r
            else:
                stm = selector.compile(p)
                return list(stm.select(input))[0]
        except:
            throw_caty_exception(u'NotFound', pp(k))
        
    def belongs(self, record):
        return record in self.db.values()
    
    def exists(self, k):
        return k in self.db

    def keys(self):
        return list(self.db.keys())

    def all(self):
        return list(self.db.values())

    def insert(self, k, v):
        if k == None:
            path = selector.compile(self.keytype, True)
            k = path.select(v).next()
            if not k:
                throw_caty_exception(u'BadInput', pp(v))
        else:
            path = selector.compile(self.keytype)
            path.replace(v, k)
        if k in self.db:
            throw_caty_exception(u'AlreadyExists', pp(k))
        self.db[k] = v
        return v

    def replace(self, k, v):
        if k not in self.db:
            throw_caty_exception(u'NotFound', pp(k))
        path = selector.compile(self.keytype)
        path.replace(v, k)
        self.db[k] = v
        return v

    def delete(self, k):
        if k not in self.db:
            throw_caty_exception(u'NotFound', pp(k))
        del self.db[k]

    @property
    def keytype(self):
        if self.module_name:
            mod = self.app._schema_module.get_module(self.module_name)
        else:
            mod = self.app._schema_module
        tp = mod.get_type(self.collname)
        return tp.annotations['__identified'].value


