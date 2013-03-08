from caty.command import *
import caty.jsontools as json
from bson import ObjectId
from decimal import Decimal
from caty.core.spectypes import UNDEFINED

class Status(Command):
    def execute(self):
        return {
            'host': self.mongo.config.get('host', u'localhost'),           'port': self.mongo.config.get('port', 27017),
            'status': u'running' if self.mongo.conn else u'stopped'
        }

class ListDatabases(Command):
    def execute(self):
        return self.mongo.list_databases()

class CreateDatabase(Command):
    def setup(self, name):
        self.db_name = name

    def execute(self):
        return self.mongo.create_database(self.db_name)


class ActivateDatabase(CreateDatabase): pass

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

class Get(Command):
    def setup(self, id):
        self._id = id

    def execute(self):
        return xjson_from_bson(self.arg0.find_one(ObjectId(self._id)))

class Set(Command):
    def setup(self, id=None):
        self._id = id

    def execute(self, input):
        if self._id:
            self.arg0.update({'_id': ObjectId(self._id)}, bson_from_xjson(input))
        else:
            self.arg0.insert(bson_from_xjson(input))

class Select(Command):
    def execute(self, input):
        if input:
            q = compile_query(input)
            return map(xjson_from_bson, self.arg0.find(bson_from_xjson(q, True)))
        else:
            return map(xjson_from_bson, self.arg0.find())

class Delete(Command):
    def setup(self, id=None):
        self._id = id

    def execute(self, input):
        if self._id:
            self.arg0.remove(ObjectId(self._id))
        else:
            self.arg0.remove(bson_from_xjson(input))

class ToBSON(Command):
    def execute(self, input):
        return bson_from_xjson(input)

def xjson_from_bson(o):
    if isinstance(o, ObjectId):
        return json.tagged(u'ObjectId', unicode(str(o)))
    elif isinstance(o, list):
        return  map(xjson_from_bson, o)
    elif isinstance(o, dict):
        keys = set(o.keys())
        if keys == set(['__int__', '__float__']):
            return Decimal(o['__int__'] + '.' + o['__float__'])
        elif keys == set(['__int__']):
            return Decimal(o['__int__'])
        r = {}
        for k, v in o.items():
            r[k] = xjson_from_bson(v)
        return r
    elif o is None:
        return UNDEFINED
    else:
        return o

import re
bson_key_pattern = re.compile("[_a-zA-Z!'#&%@,=~^][_a-zA-Z0-9!'#&%@,=~^$]{0,255}")
def bson_from_xjson(o, is_query=False):
    if isinstance(o, json.TaggedValue):
        if o.tag == 'ObjectId':
            return ObjectId(o.value)
        else:
            if isinstance(o.value, dict):
                r = bson_from_xjson(o.value, is_query)
                if '_tag' in r:
                    throw_caty_exception(u'BadInput', u'Not BSON serializable data: $data', data=json.pp(o))
                r['_tag'] = o.tag
                return r
            throw_caty_exception(u'BadInput', u'Not BSON serializable data: $data', data=json.pp(o))
    elif isinstance(o, list):
        return [bson_from_xjson(i, is_query) for i in o if o is not None]
    elif isinstance(o, dict):
        r = {}
        for k, v in o.items():
            if not bson_key_pattern.match(k):
                if not (is_query and k.startswith('$')):
                    throw_caty_exception(u'BadInput', u'Invalid key: $key', key=k)
            r[k] = bson_from_xjson(v, is_query)
            if r[k] is None:
                del r[k]
        return r
    elif isinstance(o, (unicode, int, long, str, bool)):
        return o
    elif isinstance(o, Decimal):
        s = str(o)
        if '.' in s:
            a, b = s.split('.')
            return {'__int__': a, '__float__': b}
        else:
            return {'__int__': s}
    elif o is UNDEFINED:
        return None
    else:
        return None

_qmap = {
    'notEq': u'ne',
    'lte': u'le',
    'gte': u'ge',
    'isIn': u'in',
    'isNotIn': u'nin',
    'includes': u'all',
    'typeIs': u'type',
    'length': u'size'
}
_qset = [u'ne', u'lt', u'gt', u'in', u'nin', u'regex', u'mod', u'type', u'size', u'and', u'or', u'not', u'nor']
for q in _qset:
    _qmap[q] = q
def compile_query(query):
    if isinstance(query, (json.TaggedValue, json.TagOnly)):
        tag, val = json.split_tag(query)
        if tag == 'any':
            return None
        elif tag == 'eq':
            return compile_query(val)
        elif tag == 'isDefined' or tag == 'defined':
            return {'$ne': UNDEFINED}
        elif tag == 'isDefined' or tag == 'defined':
            return {'$exists': True}
        elif tag == 'isNotDefined' or tag == 'ndefined':
            return {'$exists': False}
        elif tag == 'has':
            return {'$all': [val]}
        elif tag == 'hasNot' or tag == 'hasnt':
            return {'$not': {'$all': [val]}}
        elif tag == 'notInclude':
            return {'$not': {'$all': val}}
        elif tag == 'open':
            return compile_query(val)
        elif tag == 'close':
            return compile_query(val)
        elif tag == 'like':
            return {'$regex': val.replace('*', '.*').replace('%', '.*').replace('#', '[0-9]').replace('[!', '[^').replace('?', '.').replace('_', '.')}
        elif tag in _qmap:
            op = '$'+_qmap.get(tag, tag)
            return {op: compile_query(val)}
        else:
            return json.tagged(tag, compile_query(val))
    elif isinstance(query, dict):
        r = {}
        for k, v in query.items():
            r[k] = compile_query(v)
        return r
    elif isinstance(query, list):
        return map(compile_query, query)
    else:
        return query
