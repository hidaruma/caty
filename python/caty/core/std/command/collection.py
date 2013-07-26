#coding: utf-8
import caty
from caty.core.command import Builtin
import caty.jsontools.selector as selector


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

class List(Builtin):
    def execute(self):
        return self.arg0.all()

class All(List):
    pass

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

class DeleteAll(Builtin):
    def execute(self):
        for k in self.arg0.keys():
            self.arg0.delete(k)

class Dump(Builtin):
    def execute(self):
        return self.arg0.dump()

class Count(Builtin):
    def execute(self):
        return len(self.arg0.all())


class Mget(Builtin):
    def setup(self, opts):
        self.strict = opts['strict']

    def execute(self, input):
        r = []
        for i in input:
            if len(i) == 2:
                k, p = i
            else:
                k = i[0]
                p = None
            try:
                r.append(self.arg0.get(k, p))
            except:
                if self.strict:
                    raise
                else:
                    pass
        return r


class Poke(Insert):
    pass

class Set(Builtin):
    def setup(self, key, path=None):
        self.key = key
        self.path = path

    def execute(self, rec):
        if not self.path:
            return self.arg0.replace(self.key, rec)
        else:
            v = self.arg0.get(self.key)
            path = selector.compile(self.path)
            path.replace(v, rec)
            return self.arg0.replace(self.key, v)
