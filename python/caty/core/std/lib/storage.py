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
        obj.collname = user_param
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
            k = v.get(self.keytype)
            if not k:
                throw_caty_exception(u'BadInput', pp(v))
        if k in self.db:
            throw_caty_exception(u'AlreadyExists', pp(k))
        self.db[k] = v
        return v

    def replace(self, k, v):
        if k not in self.db:
            throw_caty_exception(u'NotFound', pp(k))
        self.db[k] = v
        return v

    def delete(self, k):
        if k not in self.db:
            throw_caty_exception(u'NotFound', pp(k))
        del self.db[k]

    def keytype(self):
        tp = self.app._schema_module.get_type(self.collname)
        return tp.annotations['__identified'].value


