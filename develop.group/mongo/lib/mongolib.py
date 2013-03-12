from interfaces.mongo.MongoHandler import MongoHandlerBase
from interfaces.mongo.Database import DatabaseBase
from interfaces.mongo.Collection import CollectionBase
from caty.core.facility import Facility
from caty.core.exception import *
from caty.core.spectypes import UNDEFINED
import caty.jsontools as json

from decimal import Decimal

from bson import ObjectId
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
        return {u'className': u'mongo:Database', u'state': DatabaseWrapper(self.conn[name], self.mode)}

class DatabaseWrapper(DatabaseBase):
    def __init__(self, database, mode):
        self.database = database
        DatabaseBase.__init__(self, mode)

    def create_collection(self, name):
        return {'className': u'mongo:Collection', 'state': CollectionWrapper(self.database[name], self.mode)}

    def list_collections(self):
        return self.database.collection_names()

    def drop_collection(self, name):
        self.database.drop_collection(name)

    def clear_collection(self, name):
        self.database[name].remove(None)

class CollectionWrapper(CollectionBase):
    def __init__(self, collection, mode):
        self.collection = collection
        CollectionBase.__init__(self, mode)

    def get(self, id):
        return xjson_from_bson(self.collection.find_one(ObjectId(id)))

    def set(self, input, id=UNDEFINED):
        if id:
            self.collection.update({'_id': ObjectId(id)}, bson_from_xjson(input))
        else:
            self.collection.insert(bson_from_xjson(input))

    def select(self, input):
        if input:
            q = compile_query(input)
            return map(xjson_from_bson, self.collection.find(bson_from_xjson(q, True)))
        else:
            return map(xjson_from_bson, self.collection.find())

    def delete(self, input, id=UNDEFINED):
        if id:
            self.collection.remove(ObjectId(id))
        else:
            self.collection.remove(bson_from_xjson(input))

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
