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
        self.order_by = opts['order-by']
        self.max = opts['max']

    def execute(self):
        if self.max != u'unbounded':
            if self.skip:
                return sort_items(self.arg0.slice(self.skip, self.max), self.order_by)
            else:
                return sort_items(self.arg0.slice(0, self.max), self.order_by)
        if self.skip:
            return sort_items(self.arg0.slice(self.skip), self.order_by)
        return sort_items(self.arg0.all(), self.order_by)

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
    def setup(self, opts):
        self.order_by = opts['order-by']

    def execute(self, query):
        r = []
        for k in self.arg0.keys():
            if self.match(self.arg0.get(k), query):
                r.append(self.arg0.get(k))
        items = sort_items(r, self.order_by)
        p = selector.compile(self.arg0.keytype)
        return map(lambda x: p.select(x).next(), items)

    def match(self, data, query):
        if isinstance(query, unicode):
            if not isinstance(data, unicode):
                return False
            if query not in data:
                return False
        elif isinstance(query, list):
            if not isinstance(data, unicode):
                return False
            for subquery in query:
                if subquery not in data:
                    return False
        elif isinstance(query, dict):
            if not isinstance(data, dict):
                return False
            for k, q in query.items():
                if k not in data:
                    return False
                if not self.match(data[k], q):
                    return False
        elif isinstance(query, json.TaggedValue):
            t, query = json.split_tag(query)
            if t == u'every':
                if not isinstance(data, list):
                    return False
                for v in data:
                    if not self.match(v, query):
                        return False
            elif t == u'some':
                if not isinstance(data, list):
                    return False
                for v in data:
                    if self.match(v, query):
                        break
                else:
                    return False
            else:
                if not isinstance(data, unicode):
                    return False
                if t == u'or':
                    for subquery in query:
                        if subquery in data:
                            break
                    else:
                        return False
                else:
                    for subquery in query:
                        if subquery not in data:
                            return False
        return True


def sort_items(items, order_by):
    if not order_by:
        return items
    func = _make_comparator(order_by)
    items.sort(func)
    return items

def _make_comparator(key):
    if isinstance(key, basestring):
        path = selector.compile(key)
        def cmp_obj(a, b):
            return cmp(path.select(a).next(), path.select(b).next())
    else:
        path_list = map(selector.compile, key)
        def cmp_obj(a, b):
            r = 0
            for p in path_list:
                r = cmp(p.select(a).next(), p.select(b).next())
                if r != 0:
                    return r
            return r
    return cmp_obj


