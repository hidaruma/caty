#coding: utf-8
import caty
from caty.core.command import Builtin


class Lookup(Builtin):
    def setup(self, key):
        self.key = key

    def execute(self):
        return self.arg0.lookup(self.key)

class Insert(Builtin):
    def setup(self, key=None):
        self.key = key

    def execute(self, rec):
        return self.arg0.insert(self.key, rec)


class Get(Builtin):
    def setup(self, key, path=None):
        self.key = key
        self.path = path

    def execute(self):
        return self.arg0.get(self.key, self.path)

class Belongs(Builtin):
    def execute(self, record):
        return self.arg0.belongs(record)


class Exists(Builtin):
    def setup(self, key):
        self.key = key

    def execute(self):
        return self.arg0.exists(self.key)

class Keys(Builtin):
    def execute(self):
        return self.arg0.keys()

class All(Builtin):
    def execute(self):
        return self.arg0.all()

class Replace(Builtin):
    def setup(self, key):
        self.key = key

    def execute(self, rec):
        return self.arg0.replace(self.key, rec)

class Delete(Builtin):
    def setup(self, key):
        self.key = key

    def execute(self):
        return self.arg0.delete(self.key)

