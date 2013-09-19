from caty.core.facility import Facility, READ
from caty.core.exception import *
from caty.core.spectypes import UNDEFINED
import caty.jsontools as json

import caty.jsontools.selector as selector
from caty.jsontools import pp
from decimal import Decimal

from bson import ObjectId
from pymongo import Connection
from pymongo.errors import ConnectionFailure

class MongoDB(Facility):
    config = {}
    conn = None

    def __init__(self, mode, system_param):
        Facility.__init__(self, mode)
        self.dbname = system_param
        self.module_name = None
        self.db = self.conn[self.dbname]
        #self._new_collection(u'default-collection')


    def _new_collection(self, collname):
        self.collname = collname
        self.collection = self.db[self.collname]
        if self.module_name:
            mod = self.app._schema_module.get_module(self.module_name)
        else:
            mod = self.app._schema_module
        tp = mod.get_type(self.collname)
        self.keytype = tp.annotations['__identified'].value
        self.keyname = self.keytype.rstrip('$.')

    @classmethod
    def initialize(cls, app, sys_config):
        cls.config = sys_config
        try:
            cls.conn = Connection(host=cls.config.get('host', u'localhost'), port=cls.config.get('port', 27017))
        except ConnectionFailure as e:
            app.i18n.write(u'DatabaseAccessError: error=$e', e=str(e))
            cls.conn = None

    @classmethod
    def instance(cls, app, system_param):
        r = cls(READ, system_param)
        r.app = app
        return r

    @classmethod
    def finalize(cls, app):
        pass

    def create(self, mode, user_param=u'default-collection'):
        obj = Facility.create(self, mode)
        if ':' in user_param:
            mod, user_param = user_param.split(':', 1)
        else:
            mod = None
        obj.module_name = mod
        obj._new_collection(user_param)
        return obj

    def clone(self):
        return self

    def lookup(self, k):
        o = xjson_from_bson(self.collection.find_one({self.keyname: k}))
        if not o:
            throw_caty_exception(u'NotFound', pp(k))
        return o

    def get(self, k, p=None):
        o = self.lookup(k)
        if p:
            stm = selector.compile(p)
            return list(stm.select(o))[0]
        else:
            return o

    def belongs(self, record):
        o = self.lookup(record)
        return o == record

    def exists(self, k):
        return self.collection.find_one({self.keyname: k}) is not None

    def keys(self):
        return [xjson_from_bson(o)[self.keyname] for o in self.collection.find()]

    def all(self):
        return [xjson_from_bson(o) for o in self.collection.find()]

    def slice(self, from_idx, to_idx=None):
        if to_idx:
            return self.all()[from_idx:from_idx+to_idx]
        else:
            return self.all()[from_idx:]

    def insert(self, k, v):
        if k == None:
            path = selector.compile(self.keyname, True)
            try:
                k = path.select(v).next()
            except KeyError as e:
                throw_caty_exception(u'BadInput', pp(v))
        else:
            path = selector.compile(self.keyname)
            path.replace(v, k)
        if self.collection.find_one(v):
            throw_caty_exception(u'AlreadyExists', pp(k))
        self.collection.insert(bson_from_xjson(v))
        return v

    def replace(self, k, v):
        if not self.collection.find_one({self.keyname: k}):
            throw_caty_exception(u'NotFound', pp(k))
        path = selector.compile(self.keyname)
        path.replace(v, k)
        self.collection.find_and_modify({self.keyname: k}, {'$set': v})
        return v

    def delete(self, k):
        if not self.collection.find_one({self.keyname: k}):
            throw_caty_exception(u'NotFound', pp(k))
        self.collection.remove({self.keyname: k})

    dump = all

def xjson_from_bson(o):
    if isinstance(o, ObjectId):
        return UNDEFINED #json.tagged(u'ObjectId', unicode(str(o)))
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
bson_key_pattern = re.compile("[^$.0-9][^.]{0,255}")
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
