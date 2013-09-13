#coding: utf-8
import caty
from caty.core.command import Builtin
import caty.jsontools.selector as selector
import caty.jsontools as json
from caty.core.exception import throw_caty_exception


class Lookup(Builtin):
    def setup(self, key):
        self.key = key

    def execute(self):
        return self.arg0.lookup(self.key)

class Insert(Builtin):
    def setup(self, opts, key=None):
        self.key = key
        self.output_rec = opts['output-rec']

    def execute(self, rec):
        r = self.arg0.insert(self.key, rec)
        if self.output_rec:
            return r


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
    def setup(self, opts):
        self.skip = opts['skip']
        self.max = opts['max']

    def execute(self):
        if self.max != u'unbounded':
            if self.skip:
                return self.arg0.slice(self.skip, self.max)
            else:
                return self.arg0.slice(0, self.max)
        if self.skip:
            return self.arg0.slice(self.skip)
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
            if not isinstance(i, list):
                k = i
                p = None
            elif len(i) == 2:
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
    def execute(self, obj):
        if not isinstance(obj, dict):
            throw_caty_exception(u'BadInput', json.pp(obj))
        return Insert.execute(self, obj)

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

class Grep(Builtin):
    def execute(self, query):
        r = []
        for k in self.arg0.keys():
            if self.match(self.arg0.get(k), query):
                r.append(k)
        return r

    def match(self, value, query):
        for k, q in query.items():
            if k not in value:
                return False
            data = value[k]
            if isinstance(q, unicode):
                if not isinstance(data, unicode):
                    return False
                if q not in data:
                    return False
            elif isinstance(q, list):
                if not isinstance(data, unicode):
                    return False
                for subq in q:
                    if subq not in data:
                        return False
            elif isinstance(q, dict):
                if not isinstance(data, dict):
                    return False
                if not self.match(data, q):
                    return False
            else:
                if not isinstance(data, unicode):
                    return False
                if q.tag == u'or':
                    for subq in q.value:
                        if subq in data:
                            break
                    else:
                        return False
                else:
                    for subq in q.value:
                        if subq not in data:
                            return False
        return True


