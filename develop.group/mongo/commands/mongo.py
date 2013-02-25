from caty.command import *

class ListDatabases(Command):
    def execute(self):
        return self.mongo.list_databases()

class CreateDatabase(Command):
    def setup(self, name):
        self.db_name = name

    def execute(self):
        return self.mongo.create_database(self.db_name)

class ListCollections(Command):
    def execute(self):
        return self.arg0.collection_names()

class DropCollection(Command):
    def setup(self, col_name):
        self.col_name = col_name

    def execute(self):
        self.arg0[self.col_name].drop_collection(self.col_name)

class CreateCollection(Command):
    def setup(self, col_name):
        self.col_name = col_name

    def execute(self):
        return self.arg0[self.col_name]


class ClearCollection(Command):
    def setup(self, col_name):
        self.col_name = col_name

    def execute(self):
        self.arg0[self.col_name].remove(None)
