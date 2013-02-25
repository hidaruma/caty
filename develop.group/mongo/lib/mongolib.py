from interfaces.mongo.MongoHandler import MongoHandlerBase
from caty.core.facility import Facility

from pymongo import Connection
from pymongo.errors import ConnectionFailure


class MongoHandler(MongoHandlerBase):
    config = {}
    @classmethod
    def initialize(cls, app, sys_config):
        cls.config = {}

    @classmethod
    def instance(cls, app, system_param):
        return MongoHandler(system_param)

    @classmethod
    def finalize(cls, app):
        pass

    def create(self, mode, user_param=None):
        obj = Facility.create(self, mode)
        return obj

    def clone(self):
        return self

    def __init__(self, *ignore):
        self.conn = Connection(host=self.config.get('host', 'localhost'), port=self.config.get('port', 27017))

    def list_databases(self):
        return self.conn.database_names()

    def create_database(self, name):
        return self.conn[name]

