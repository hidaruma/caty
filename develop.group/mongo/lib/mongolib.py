from interfaces.mongo.MongoHandler import MongoHandlerBase
from caty.core.facility import Facility
from caty.core.exception import *

from pymongo import Connection
from pymongo.errors import ConnectionFailure


class MongoHandler(MongoHandlerBase):
    config = {}
    @classmethod
    def initialize(cls, app, sys_config):
        cls.config = {}

    @classmethod
    def instance(cls, app, system_param):
        return MongoHandler(app, system_param)

    @classmethod
    def finalize(cls, app):
        pass

    def create(self, mode, user_param=None):
        obj = Facility.create(self, mode)
        return obj

    def clone(self):
        return self

    def __init__(self, app, system_param):
        self.app = app
        self.system_param = system_param
        try:
            self.conn = Connection(host=self.config.get('host', u'localhost'), port=self.config.get('port', 27017))
        except ConnectionFailure as e:
            self.app.i18n.write(u'DatabaseAccessError: error=$e', e=str(e))
            self.conn = None

    def list_databases(self):
        return self.conn.database_names()

    def create_database(self, name):
        return self.conn[name]

class CollectionWrapper(object):
    def __init__(self, collection):
        self.collection = collection

    def get(self, id):
        return xjson_from_bson(self.collection.find_one(ObjectId(id)))

    def set(self, input, id=None):
        if id:
            self.collection.update({'_id': ObjectId(id)}, bson_from_xjson(input))
        else:
            self.collection.insert(bson_from_xjson(input))

    def select(self, input):
        if input:
            return map(xjson_from_bson, self.collection.find(bson_from_xjson(input)))
        else:
            return map(xjson_from_bson, self.collection.find())

    def delete(self, input, id=None):
        if id:
            self.collection.remove(ObjectId(id))
        else:
            self.collection.remove(bson_from_xjson(input))


