#coding: utf-8
from caty.storage import sqlite
from caty.util import memoize
from caty.jsontools import TagOnly
from caty.util.path import join
from caty.core.exception import InternalException

def initialize(config):
    t = config['type']
    if t == 'sqlite':
        sqlite.initialize(config['path'])
        return StorageModuleWrapper(sqlite, config)

from caty.core.facility import Facility, AccessManager, READ
class StorageModuleWrapper(Facility):
    def __init__(self, mod, conf, mode=READ):
        self._mod = mod
        self._storage_class = mod.JsonStorage
        self._conf = conf
        self._conn = None
        self._storage = None
        self._schema_module = None
        self._collection_name = None
        self.application = None
        Facility.__init__(self, mode)

    def set_finder(self, finder):
        self._schema_module = finder
        return self

    def start(self):
        n = self.clone()
        n._connect()
        return n

    def clone(self):
        new = StorageModuleWrapper(self._mod, self._conf, self.mode)
        new._conn = self._conn
        new._schema_module = self._schema_module
        new.application = self.application
        return new

    def _connect(self):
        self._conn = self._mod.connect(self._conf)

    def commit(self):
        self._conn.commit()

    def cancel(self):
        self._conn.rollback()

    def __call__(self, collection_name, app_name=''):
        current_app_name = self.application.name
        smw = self.clone()
        smw._storage = smw._storage_class(self._conn, self._schema_module, collection_name, app_name, current_app_name)
        smw._collection_name = collection_name
        return smw

    am = AccessManager()

    @am.update
    def create_collection(self, schema_name, global_collection=False):
        return self._storage.factory.create(schema_name, global_collection)

    @am.update
    def drop(self):
        return self._storage.manipulator.drop()

    @am.update
    def insert(self, obj):
        return self._storage.manipulator.insert(obj)

    @am.read
    def select(self, obj=TagOnly('_ANY'), limit=-1, start=0, reverse=False):
        return self._storage.manipulator.select(obj, limit, start, reverse)

    @am.read
    def select1(self, obj):
        return self._storage.manipulator.select1(obj)

    @am.update
    def delete(self, obj):
        return self._storage.manipulator.delete(obj)

    @am.update
    def update(self, oldobj, newobj):
        return self._storage.manipulator.update(oldobj, newobj)

    @am.read
    def dump(self):
        return self._storage.manipulator.dump()

    @am.update
    def restore(self, objects):
        return self._storage.manipulator.restore(objects)

    @property
    def schema(self):
        return self._storage.manipulator.schema

    @property
    def collections(self):
        return list(self._storage_class.collections(self._conn))

class NullStorage(object):
    def create(self, mode, user_param):
        raise InternalException(u'JSON storage is not configured')

    def connect(self):
        return self

    def commit(self):
        pass

    def cancel(self):
        pass
