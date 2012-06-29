#coding:utf-8
u"""JSON ストレージの SQLite バックエンド。
JSON <-> RDB のマッピング手法としては、経路列挙モデル+モデル写像を用いている。
モデル写像とは {"x": string, y:{"z":integer}} のようなデータに対して、
以下のようなコレクションを対応付ける手法である。
詳しいことは論文を探して読むこと。

property|value|eid|cid |pid 
x       |"foo"|  1|null|null
y       |null |  1|null|   1
z       |   10|  1|   1|null

ただしこのままでは煩雑過ぎるので、要素間の親子関係を JSON パスで表し、
以下のようなコレクションに格納することで単純化を図っている。

id  |path |value|
xxxx|$.x  |"foo"|
yyyy|$.y.z |   10|

またコレクションとスキーマの対応付けのためのコレクションも作成する。

|collection_name|schema |app |logical_name|
|__foo     |xxx:foo|null|foo         |
|x__bar    |yyy:bar|x   |bar         |

app カラムには定義元アプリケーションが入る。
これが null の場合、グローバル定義のスキーマとされる。
"""

import os
import sqlite3
from caty.jsontools import *
from caty.jsontools.path import build_query
from caty.core.exception import InternalException
from caty.util import to_unicode, try_parse
from decimal import Decimal
from itertools import islice

def connect(config):
    conn = sqlite3.connect(config['path'], isolation_level='IMMEDIATE')
    conn.row_factory = sqlite3.Row
    create_functions(conn)
    return conn

def initialize(path):
    u"""コレクションとトリガーの作成を行う。
    サイト初期化時に一度呼べば良く、また既にDBが作成されている場合は処理を行わないものとする。
    """
    conn = sqlite3.connect(path)
    conn.execute("""create table if not exists collection_schema_matching (
    collection_name text primary key,
    schema text not null,
    app text not null,
    logical_name text not null
    )
    """)
    conn.commit()

import string
num = frozenset(list(string.digits))
def path_matches(path, pattern):
    u"""path がパスマッチ式にマッチするかの結果を返す。
    パスマッチ式は $.foo.[0-9].bar のように [0-9] を特殊なパス名として含み、
    「[0-9] は配列インデックスにマッチする」という意味となる。
    """
    for x, y in zip(path.split('.'), pattern.split('.')):
        if y == '[0-9]':
            if not all(map(num.__contains__, x)):
                return 0
        else:
            if x != y:
                return 0
    return 1

class PathMatcher(object):
    def __init__(self, pattern):
        self.pattern = pattern
    
    @property
    def query(self):
        if '[0-9]' not in self.pattern:
            return "path='%s'" % self.pattern
        else:
            return '1=path_matches(path, \'%s\')' % self.pattern

def cmp_lt(a, b):
    return Decimal(a) < Decimal(b)

def cmp_le(a, b):
    return Decimal(a) <= Decimal(b)

def cmp_gt(a, b):
    return Decimal(a) > Decimal(b)

def cmp_ge(a, b):
    return Decimal(a) >= Decimal(b)

def between(a, b, c):
    return Decimal(a) >= Decimal(b) and Decimal(a) <= Decimal(c)

def create_functions(conn):
    conn.create_function("path_matches", 2, path_matches)
    conn.create_function("lt", 2, cmp_lt)
    conn.create_function("le", 2, cmp_le)
    conn.create_function("gt", 2, cmp_gt)
    conn.create_function("ge", 2, cmp_ge)
    conn.create_function("between_", 3, between)

from caty.util.collection import merge_dict
from caty.jsontools import obj2path, path2obj, TaggedValue, TagOnly, encode, decode
from time import time
from uuid import uuid4
class QueryBuilder(object):
    u"""クエリ構築オブジェクト。
    SQLiteStorage は QueryBuilder に全てのクエリ作成処理を委譲する。
    コンストラクタの第二引数は None が可能だが、これが None であってよいのは
    create_collection_query を呼び出す場合のみで、他のクエリの生成には必須のパラメータである。
    """
    def __init__(self, collection_name, app='', schema=None):
        self._collection_name = app + '__' + collection_name
        self._logical_name = collection_name
        self._schema = schema
        self._app_name = app
       

    def create_collection(self):
        return 'create table if not exists %s (id text, path text, value text)' % self._collection_name

    def drop_collection(self):
        return 'drop table if exists %s' % self._collection_name

    def delete_schema_match(self):
        return 'delete from collection_schema_matching where collection_name=\'%s\'' % self._collection_name

    def collection_schema_match(self, schema_name):
        return ('insert into collection_schema_matching (collection_name, schema, app, logical_name) values (?, ?, ?, ?)', 
                (self._collection_name, schema_name, self._app_name, self._logical_name))

    def already_created(self):
        return 'select count(*) from collection_schema_matching where collection_name=?', (self._collection_name,)

    def insert(self, obj):
        p = obj2path(encode(obj))
        eid = unicode(uuid4())
        p['$.$deleted'] = 'false'
        p['$.$created'] = unicode(str(time()))
        p['$.$modified'] = unicode(str(time()))
        for k, v in p.items():
            yield ('insert into ' + self._collection_name + ' (id, path, value) values(?, ?, ?)', (eid, k, to_unicode(v)))

    def restore(self, obj):
        p = obj2path(encode(obj))
        eid = obj['$.$id']
        del obj['$.$id']
        for k, v in p.items():
            yield ('insert into ' + self._collection_name + ' (id, path, value) values(?, ?, ?)', (eid, k, to_unicode(v)))

    def select_id(self, obj, reverse):
        order = 'desc' if reverse else 'asc'
        if tag(obj) == '_ANY':
            yield """select distinct id from %s where id in 
                (select id from %s where path='$.$deleted' and value='false')
                and path='$.$created' order by value %s limit ? offset ?""" % (self._collection_name, self._collection_name, order), []
        else:
            yield 'select distinct id from %s where id in (select id from %s where id in (' % (self._collection_name, self._collection_name), []
            p = object2query(obj, self._collection_name)
            head = 'select id from %s where ' % self._collection_name
            send =  False
            for q in p.build('$'):
                if send:
                    yield ' intersect ', []
                yield head + q[0], q[1]
                send = True
            yield """) and path='$.$deleted' and value='false') 
            and path='$.$created' order by value %s limit ? offset ?""" % order, []

    def select_by_id(self):
        return 'select * from %s where id=?' % self._collection_name

    def delete(self):
        return "update %s set value='true' where id=? and path='$.$deleted'" % self._collection_name

    def update(self, eid, created, new):
        n = obj2path(new)
        n['$.$id'] = eid
        n['$.$deleted'] = False
        n['$.$created'] = created
        n['$.$modified'] = str(time())
        yield "delete from %s where id=?" % self._collection_name, (eid,)
        for path, value in n.items():
            yield "insert into %s (id, path, value) values(?, ?, ?)" % self._collection_name, (eid, path, to_unicode(value))

def object2query(obj, collection_name):
    if isinstance(obj, dict):
        d = {}
        for k, v in obj.items():
            d[k] = object2query(v, collection_name)
        return _(d)
    elif isinstance(obj, (list, tuple)):
        return _(map(lambda o:object2query(o, collection_name), obj))
    elif isinstance(obj, (TaggedValue, TagOnly)):
        if tag(obj) in predicates:
            return predicates[tag(obj)](obj, collection_name)
        else:
            if isinstance(obj, TaggedValue):
                return _({'$$tag': _(tag(obj)), '$$val':object2query(untagged(obj), collection_name)})
            else:
                return _({'$$tag': _(tag(obj)), '$$no-value': _(True)})
    else:
        return _(obj)

class Query(object):
    def build(self, k):
        raise NotImplemented

class UnaryQuery(Query):
    def __init__(self, t=None, dummy=None):
        assert isinstance(t, TagOnly) or t is None

class BinaryQuery(Query):
    def __init__(self, obj, collection_name):
        assert isinstance(obj, TaggedValue)
        self._collection_name = collection_name
        self.initialize(untagged(obj))

class _(Query):
    def __init__(self, v, dummy=None):
        self.value = v

    def build(self, path):
        if isinstance(self.value, dict):
            for k, v in self.value.items():
                if isinstance(path, PathMatcher):
                    p = PathMatcher('%s.%s' % (path.pattern, k))
                else:
                    p = '%s.%s' % (path, k)
                for q in v.build(p):
                    yield q
        elif isinstance(self.value, (list, tuple)):
            for i, v in enumerate(self.value):
                if isinstance(path, PathMatcher):
                    p = PathMatcher('%s.%d' % (path.pattern, i))
                else:
                    p = '%s.%d' % (path, i)
                for q in v.build(p):
                    yield q
        elif self.value is not None:
            if isinstance(path, PathMatcher):
                q = path.query
                yield q + ' and value=?', (to_unicode(self.value),)
            else:
                yield 'path=? and value=?', (path, to_unicode(self.value))
        else:
            if isinstance(path, PathMatcher):
                q = path.query
                yield q + ' and value is null', (p,)
            else:
                yield 'path=? and value is null', (path,)

class Or(BinaryQuery):
    def initialize(self, value):
        assert isinstance(value, (list, tuple))
        self.preds = []
        for v in value:
            self.preds.append(object2query(v, self._collection_name))

    def build(self, path):
        queries = []
        for p in self.preds:
            for q in p.build(path):
                queries.append(q)
        yield ' or '.join(map(lambda a:a[0], queries)), reduce(lambda x, y: x + y, map(lambda a:a[1], queries))

class And(BinaryQuery):
    def initialize(self, value):
        assert isinstance(value, (list, tuple))
        self.preds = []
        for v in value:
            self.preds.append(object2query(v, self._collection_name))

    def build(self, path):
        queries = []
        for p in self.preds:
            for q in p.build(path):
                queries.append((' select id from %s where %s ' % (self._collection_name, q[0]), q[1]))

        args = reduce(lambda x, y: x + y, map(lambda a:a[1], queries))
        query = ' id in (%s) ' % (reduce(lambda a, b: '%s intersect %s' % (a, b), map(lambda a:a[0], queries)))
        yield query, args

class Any(UnaryQuery):
    def build(self, path):
        if isinstance(path, PathMatcher):
            yield path.query
        else:
            yield 'path=?', (path,)

class NotNull(UnaryQuery):
    def build(self, path):
        if isinstance(path, PathMatcher):
            q = path.query
            yield q + ' and value is not null', ()
        else:
            yield 'path=? and value is not null', (path, )

class Like(BinaryQuery):
    def initialize(self, pattern):
        self.pattern = pattern

    def build(self, path):
        if isinstance(path, PathMatcher):
            q = path.query
            yield q + ' and value like ?', (self.pattern,)
        else:
            yield 'path=? and value like ?', (path, self.pattern)

class Contains(BinaryQuery):
    def initialize(self, item):
        self.item = object2query(item, self._collection_name)

    def build(self, path):
        queries = []
        for q in self.item.build(PathMatcher(path+'.[0-9]')):
            queries.append((' select id from %s where %s ' % (self._collection_name, q[0]), q[1]))

        args = reduce(lambda x, y: x + y, map(lambda a:a[1], queries))
        query = ' id in (%s)' % (reduce(lambda a, b: '%s union %s' % (a, b), map(lambda a:a[0], queries)))
        yield query, args

class Each(BinaryQuery):
    def initialize(self, item):
        self.item = object2query(item, self._collection_name)

    def build(self, path):
        matcher = PathMatcher(path+'.[0-9]')
        empty_list = PathMatcher(path+'.[]')
        q1, args = self.item.build(matcher).next()
        q2 = ' select id, path from %s where %s ' % (self._collection_name, q1)
        query = ' id not in (select id from (select id, path from %s where %s or %s except %s)) ' % (
                self._collection_name, matcher.query, empty_list.query, q2)
        yield query, args

class Between(BinaryQuery):
    def initialize(self, pair):
        self.pair = pair

    def build(self, path):
        if isinstance(path, PathMatcher):
            yield q + ' and 1=between_(value, ?, ?)', (self.pair[0], self.pair[1])
        else:
            yield 'path=? and 1=between_(value, ?, ?)', (path, self.pair[0], self.pair[1])

class Cmp(BinaryQuery):
    def initialize(self, item):
        assert isinstance(item, (int, Decimal))
        self.item = to_unicode(item)

    def build(self, path):
        if isinstance(path, PathMatcher):
            yield '%s and value is not null and 1=%s(value, ?)' % (path.query, self.expr), (self.item,)
        else:
            yield 'path=? and value is not null and 1=%s(value, ?)' % self.expr, (path, self.item)

class LessThan(Cmp):
    expr = 'lt'
class LessThanEqual(Cmp):
    expr = 'le'
class GreaterThan(Cmp):
    expr = 'gt'
class GreaterThanEqual(Cmp):
    expr = 'ge'

predicates = {
    '_OR': Or, 
    '_AND': And, 
    '_ANY': Any, 
    '_EACH': Each, 
    '_CONTAINS': Contains, 
    '_LIKE': Like,
    '_NOT_NULL': NotNull,
    '_LT': LessThan,
    '_LE': LessThanEqual,
    '_GT': GreaterThan,
    '_GE': GreaterThanEqual,
    '_BETWEEN': Between,
}


class CollectionManipulator(object):
    u"""JSON ストレージ操作のフロントエンド。
    他のモジュールからはこのオブジェクトだけを通じて JSON ストレージの操作を行う。
    """
    def __init__(self, conn, finder, collection_name, app_name='', current_app_name=''):
        self._conn = conn
        self._finder = finder
        self._collection_name = collection_name
        self._app_name = app_name if app_name else current_app_name
        self._current_app_name = current_app_name
        self._schema = self._load_schema(app_name)
        self._app_collection_pair = self._load_collection_name()
        assert self._schema, (repr(self._schema), collection_name)

    def _load_schema(self, app_name):
        u"""コレクション名に対応したスキーマの読み込みを行う。
        対応が未登録の場合は None を返す。
        一旦登録されたスキーマが後に削除されたときのために、
        スキーマが取得できなくてもエラーとはしない。
        その場合、コレクションのドロップかスキーマの対応関係の修正が必要となる。

        コレクションの所属するアプリケーションが指定された場合はそこだけを検索し、
        特にアプリケーションが指定されなかったら呼び出し元のアプリケーションと、
        グローバル空間を検索対象とする。
        """
        if app_name:
            query = 'select app, schema from collection_schema_matching where logical_name=? and app=?'
            c = self._conn.cursor()
            c.execute(query, [self._collection_name, app_name])
        else:
            query = 'select app, schema from collection_schema_matching where logical_name=? and app=?'
            c = self._conn.cursor()
            c.execute(query, [self._collection_name, self._current_app_name])
        s = self._fetch_schema(c)
        if s is None:
            if not app_name:
                query = 'select app, schema from collection_schema_matching where logical_name=? and app=\'\''
                c = self._conn.cursor()
                c.execute(query, [self._collection_name])
                return self._fetch_schema(c)
        else:
            return s

    def _fetch_schema(self, c):
        r = c.fetchone()
        if r:
            try:
                sn = r['schema']
                ap = r['app']
                if not ap:
                    return self._finder.get_type(sn)
                else:
                    if ':' in sn:
                        return self._finder.get_type(ap + ':' + sn)
                    else:
                        return self._finder.get_type(ap + '::' + sn) # public モジュールのスキーマを他のアプリケーションから参照するので
            except KeyError:
                return None
        else:
            return None

    def _load_collection_name(self):
        query = """select collection_name from collection_schema_matching 
                    where (logical_name=? and app=?) or (logical_name=? and app='')"""
        c = self._conn.cursor()
        c.execute(query, [self._collection_name, self._app_name, self._collection_name])
        t = self._fetch_collection(c)
        if not t:
            raise InternalException(u'Collection does not found: collection name=$colname, defined at $denined, called by $callee', colname=self._collection_name, defined=self._app_name, callee=self._current_app_name)
        return t.split('__')

    def _fetch_collection(self, c):
        r = c.fetchone()
        if r:
            return r['collection_name']
        else:
            return ''

    @property
    def query_builder(self):
        return QueryBuilder(self._app_collection_pair[1], self._app_collection_pair[0], self._schema)

    @property
    def schema(self):
        return self._schema

    def insert(self, obj):
        self._schema.validate(obj)
        queries = []
        qb = self.query_builder
        for q in qb.insert(obj):
            queries.append(q)
        c = self._conn.cursor()
        for q, o in queries:
            c.execute(q, o)

    def select(self, obj, limit=-1, offset=0, reverse=False):
        for v in self._select(obj, limit, offset, reverse):
            yield self._convert(v)

    def _convert(self, obj):
        del obj['$id']
        del obj['$deleted']
        del obj['$created']
        del obj['$modified']
        return self._schema.convert(self._remove_tag(obj))

    def _remove_tag(self, obj):
        u"""スキーマのコンバート処理に通す前にタグを全て剥ぎ取る。
        そうしないとタグが全て二重に付けられてしまう
        """
        from caty.jsontools import untagged
        if isinstance(obj, dict):
            r = {}
            for k, v in obj.items():
                r[k] = self._remove_tag(v)
            return r
        elif isinstance(obj, list):
            r = []
            for v in obj:
                r.append(self._remove_tag(v))
            return r
        else:
            return untagged(obj)

    def _select(self, obj, limit, offset, reverse):
        qb = self.query_builder
        id_list = self._select_id_sets(qb, obj, limit, offset, reverse)
        if id_list:
            for i in id_list:
                c = self._conn.cursor()
                c.execute(qb.select_by_id(), [i])
                rows = c.fetchall()
                v = construct_object(rows)
                if v['$deleted'] == 'false':
                    yield v
                c.close()

    def _select_id_sets(self, qb, obj, limit, offset, reverse):
        q, o = reduce(lambda a, b: (a[0] + b[0], self._merge_arg(a[1], b[1])), qb.select_id(obj, reverse))
        c = self._conn.cursor()
        c.execute(q, o + [limit, offset])
        r = c.fetchall()
        c.close()
        if r:
            return [i['id'] for i in r]
        else:
            return []

    def _merge_arg(self, a, b):
        if not a:
            return list(b)
        if not b:
            return list(a)
        else:
            return list(a) + list(b)

    def slice(self, it, limit, offset):
        if limit == -1:
            return islice(it, offset, None)
        else:
            return islice(it, offset, offset+limit)

    def select1(self, obj):
        v = list(self.select(obj))
        assert len(v) == 1
        return v[0]

    def delete(self, obj):
        qb = self.query_builder
        id_set = self._select_id_sets(qb, obj , -1, 0, False)
        if id_set:
            for i in id_set:
                c = self._conn.cursor()
                c.execute(qb.delete(), [i])

    def update(self, query_obj, obj):
        qb = self.query_builder
        c = self._conn.cursor()
        for o in self._select(query_obj, -1, 0, False):
            eid = o['$id']
            created = o['$created']
            n = merge_dict(self._convert(o), obj, 'post')
            self._schema.validate(n)
            for q, o in qb.update(eid, created, n):
                c.execute(q, o)

    def dump(self):
        for obj in self._select(TagOnly('_ANY'), -1, 0, False):
            sysprop = {
                '$id': obj['$id'],
                '$deleted': obj['$deleted'],
                '$created': obj['$created'],
                '$modified': obj['$modified'],
            }
            r = self._convert(obj)
            obj.update(sysprop)
            yield obj

    def restore(self, objects):
        assert isinstance(objects, (list, tuple))
        for obj in objects:
            self._restore(obj)

    def _restore(self, obj):
        queries = []
        qb = self.query_builder
        for q in qb.restore(obj):
            queries.append(q)
        c = self._conn.cursor()
        for q, o in queries:
            c.execute(q, o)

    def drop(self):
        qb = QueryBuilder(self._app_collection_pair[1], self._app_collection_pair[0])
        c = self._conn.cursor()
        c.execute(qb.delete_schema_match())
        c.execute(qb.drop_collection())


class CollectionFactory(object):
    def __init__(self, conn, finder, collection_name, app_name='', current_app_name=''):
        self._conn = conn
        self._finder = finder
        self._collection_name = collection_name
        self._app_name = app_name if app_name else current_app_name
        self._current_app_name = current_app_name

    def create(self, schema_name, global_collection=False):
        u"""コレクション名とスキーマ名の対応表に新たな値を作り、
        新規のコレクションを作成する。
        """
        app_name = self._current_app_name if not global_collection else ''
        qb = QueryBuilder(self._collection_name, app_name)
        c = self._conn.cursor()
        q, o = qb.already_created()
        c.execute(q, o)
        r = c.fetchone()
        if r[0] != 0:
            return
        q, o = qb.collection_schema_match(schema_name)
        c.execute(q, o)
        query = qb.create_collection()
        c.execute(query)

class JsonStorage(CollectionFactory, CollectionManipulator):
    def __init__(self, *args, **kwds):
        self.__args = args
        self.__kwds = kwds
        self.__initialized = False

    @property
    def manipulator(self):
        if not self.__initialized:
            CollectionManipulator.__init__(self, *self.__args, **self.__kwds)
        return self

    @property
    def factory(self):
        CollectionFactory.__init__(self, *self.__args, **self.__kwds)
        return self

    @classmethod
    def collections(cls, conn):
        return collections(conn)


def construct_object(values):
    d = {}
    ids = []
    for v in values:
        d[v['path']] = v['value']
        ids.append(v['id'])
    assert len(set(ids)) == 1, ids
    d['$.$id'] = ids[0]
    r = decode(path2obj(d))
    return r

def collections(conn):
    c = conn.cursor()
    c.execute('select * from collection_schema_matching')
    for r in c.fetchall():
        yield {'collection_name': r['logical_name'], 'schema': r['schema'], 'app': r['app']}

