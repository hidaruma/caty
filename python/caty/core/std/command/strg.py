#coding: utf-8
from caty.core.command import Builtin
from caty.jsontools import *
from caty.jsontools.path import build_query

name = 'strg'
schema = u"""
type DumpInfo = {
    "collectionName": string,
    "schema": string,
    "data": [object*]
};

type Collection = {
    "collectionName": string,
    "schema": string,
    "appName": string | null,
};

"""

class StorageAccessor(object):

    @property
    def collection(self):
        if ':' in self._collection_name:
            app, collection = self._collection_name.split(':', 1)
            return self.storage(collection, app)
        else:
            return self.storage(self._collection_name)


class CreateCollection(Builtin):

    def setup(self, opts, schema_name, collection_name=None):
        self._schema_name = schema_name
        self.schema[schema_name]
        self._collection_name = collection_name if collection_name else schema_name
        self._global = opts['as-global']

    def execute(self):
        self.storage(self._collection_name).create(self._schema_name, self._global)

class DropCollection(Builtin, StorageAccessor):

    def setup(self, collection_name):
        self._collection_name = collection_name

    def execute(self):
        self.collection.drop()

def _attr_getter(k):
    def _(x):
        v = x
        for n in k.split('.'):
            v = x[n]
        return v

def _cmp_dict(a, b, f):
    return cmp(f(a), f(b))

class List(Builtin):

    def execute(self):
        r = []
        for x in self.storage.collections:
            r.append({
                'collectionName': x['collection_name'],
                'schema': x['schema'],
                'appName': x['app'],
                })
        return r

class Select(Builtin, StorageAccessor):

    def setup(self, opts, collection_name, *args):
        from caty.core.schema.array import ArraySchema
        self._collection_name = collection_name
        self._limit = opts['limit']
        self._offset = opts['offset']
        self._order_by = opts['order-by']
        self._reverse = opts['reverse']
        self._path = args

    def execute(self, input):
        if not input: input = TagOnly('_ANY')
        r = list(self.collection.select(input, self._limit, self._offset, self._reverse))
        if self._order_by:
            r.sort(cmp=lambda a, b:_cmp_dict(a, b, _attr_getter(self._order_by)))
        path = self._path
        if not path:
            return r
        else:
            if len(path) == 1:
                q = build_query('$.'+path[0])
                r_ = []
                for v in r:
                    r_.append(q.find(v).next())
                    q.reset()
                return r_
            else:
                queries = map(build_query, map(lambda a:'$.' + a, path))
                r_ = []
                for v in r:
                    _ = []
                    for q in queries:
                        _.append(q.find(v).next())
                        q.reset()
                    r_.append(_)
                return r_


from caty.core.schema.base import TagSchema, NullSchema
class Select1(Builtin, StorageAccessor):

    def setup(self, collection_name):
        self._collection_name = collection_name
        self._out_schema = self.collection.schema | TagSchema('NG', NullSchema())

    def execute(self, input):
        if not input: input = TagOnly('_ANY')
        r = list(self.collection.select(input, -1, 0))
        if len(r) != 1:
            return tagged(u'Error', u'要素数が1つではありません: %d' % (len(r)))
        return r[0]

class Insert(Builtin, StorageAccessor):

    def setup(self, opts, collection_name):
        self._collection_name = collection_name
        self._allow_dup = opts['allow-dup']
        self._in_schema = self.collection.schema

    def execute(self, input):
        if not self._allow_dup:
            l = list(self.collection.select(input, -1, 0))
            if len(l) !=0:
                return tagged(u'NG', None)
        self.collection.insert(input)
        return tagged(u'OK', None)

class Update(Builtin, StorageAccessor):

    def setup(self, collection_name):
        self._collection_name = collection_name

    def execute(self, input):
        self.collection.update(*input)

class Delete(Builtin, StorageAccessor):

    def setup(self, collection_name):
        self._collection_name = collection_name

    def execute(self, input):
        self.collection.delete(input)

class Dump(Builtin, StorageAccessor):

    def setup(self, collection_name):
        self._collection_name = collection_name

    def execute(self):
        for t in self.storage.collections:
            if t['collection_name'] == self._collection_name:
                storage = self.storage(t['collection_name'])
                return {'collectionName': unicode(t['collection_name']),
                        'schema': unicode(t['schema']),
                        'data':list(storage.dump())}

class Restore(Builtin):

    def execute(self, input):
        storage = self.storage(input['collectionName'])
        storage.drop()
        storage.create(input['schema'])
        storage = self.storage(input['collectionName'])
        storage.restore(input['data'])

