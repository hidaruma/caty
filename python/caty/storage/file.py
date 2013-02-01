# coding: utf-8
import os
from caty.jsontools import prettyprint, TaggedValue, TagOnly
import caty.jsontools.stdjson as stdjson

def initialize(conf):
    # 初期化時にディレクトリの作成は行う
    if not os.path.exists(conf['data_dir']):
        os.mkdir(conf['data_dir'])

def connect(conf):
    return FileStorageConnection(conf['data_dir'])

class FileStorageConnection(object):
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self._data_map = {'apps': {}, 'global': {}}

    def _load(self, app_name, collection_name):
        if app_name:
            if not app_name in self._data_map['apps']:
                self._data_map['apps'][app_name] = {}
            path = self.data_dir + '/' + app_name + '/' + collection_name + '.json'
            if os.path.exists(path):
                self._data_map['apps'][app_name][collection_name] = stdjson.loads(open(path).read())
        else:
            path = self.data_dir + '/' + collection_name + '.json'
            if os.path.exists(path):
                self._data_map['global'][collection_name] = stdjson.loads(open(path).read())

    def create_collection(self, app_name, collection_name, schema_name):
        self._load(app_name, collection_name)
        if app_name:
            if collection_name in self._data_map['apps'][app_name]:
                return
            self._data_map['apps'][app_name][collection_name] = {'appName': app_name, 'schema': schema_name, 'collectionName': collection_name, 'data': []}
        else:
            if collection_name in self._data_map['global']:
                return
            self._data_map['global'][collection_name] = {'appName': app_name, 'schema': schema_name, 'collectionName': collection_name, 'data': []}

    def drop(self, app_name, collection_name):
        self.get_collection(app_name, collection_name)['delete'] = True

    def load_collection(self, app_name, collection_name):
        self._load(app_name, collection_name)
        return self.get_collection(app_name, collection_name)

    def get_collection(self, app_name, collection_name):
        if app_name:
            return self._data_map['apps'][app_name][collection_name]
        else:
            return self._data_map['global'][collection_name]

    def insert(self, app_name, collection_name, obj):
        self.get_collection(app_name, collection_name)['data'].append(obj)

    def commit(self):
        for tbl_name, tbl_data in self._data_map['global'].items():
            path = self.data_dir + '/' + tbl_name + '.json'
            if tbl_data.get('delete') and os.path.exists(path):
                os.unlink(path)
            else:
                open(path, 'wb').write(prettyprint(tbl_data))

        for app_name, tbl_map in self._data_map['apps'].items():
            for tbl_name, tbl_data in tbl_map.items():
                path = self.data_dir + '/' + app_name + '/' + tbl_name + '.json'
                if tbl_data.get('delete') and os.path.exists(path):
                    os.unlink(path)
                    if not os.path.exists(self.data_dir + '/' + app_name + '/'):
                        os.mkdir(self.data_dir + '/' + app_name + '/')
                    open(path, 'wb').write(prettyprint(tbl_data))

    def rollback(self):
        self._data_map = {'apps': {}, 'global': {}}

class CollectionFactory(object):
    def __init__(self, conn, finder, collection_name, app_name='', current_app=None):
        self._conn = conn
        self._finder = finder
        self._collection_name = collection_name
        self._current_app_name = current_app.name if current_app else u''
        self._app_name = app_name if app_name else self._current_app_name

    def create(self, schema_name, global_collection=False):
        u"""コレクション名とスキーマ名の対応表に新たな値を作り、
        新規のコレクションを作成する。
        """
        app_name = self._current_app_name if not global_collection else ''
        self._conn.create_collection(app_name, self._collection_name, schema_name)


class CollectionManipulator(object):
    def __init__(self, conn, finder, collection_name, app_name='', current_app=None):
        self._conn = conn
        self._finder = finder
        self._app = current_app
        self._collection_name = collection_name
        self._current_app_name = current_app.name if current_app else u''
        self._app_name = app_name if app_name else self._current_app_name
        self._schema = self._load_schema()
        assert self._schema, (repr(self._schema), collection_name)

    def _load_schema(self):
        r = self._conn.load_collection(self._app_name, self._collection_name)
        try:
            sn = r['schema']
            ap = r['appName']
            if not ap:
                return self._finder.get_type(sn)
            else:
                return self._finder.get_type(ap + '::' + sn)
        except:
            return None

    @property
    def schema(self):
        return self._schema

    def drop(self):
        sefl._conn.drop(self._app_name, self._collection_name)

    def insert(self, obj):
        self._conn.insert(self._app_name, self._collection_name, obj)

    def select(self, obj, limit=-1, offset=0, reverse=False):
        data = self._conn.get_collection(self._app_name, self._collection_name)['data']
        r = []
        for d in data:
            if self._match(d, obj):
                if offset:
                    offset-=1
                elif limit != -1 and len(r) >= limit:
                    break
                else:
                    r.append(d)
        return iter(r)

    def _match(self, obj, queries):
        if not queries:
            queries = {}
        if not isinstance(queries, dict):
            return self._process_query(obj, queries)
        for k, q in queries.items():
            if k not in obj:
                return False
            v = obj[k]
            if not self._process_query(v, q):
                return False
        return True

    def _process_query(self, val, query):
        if isinstance(query, (TagOnly, TaggedValue)):
            if query.tag == '_NOT_NULL':
                return val is not None
            elif query.tag == '_ANY':
                return True
            elif query.tag == '_LT':
                return val < query.value
            elif query.tag == '_LE':
                return val <= query.value
            elif query.tag == '_GT':
                return val > query.value
            elif query.tag == '_GE':
                return val >= query.value
            elif query.tag == '_CONTAINS':
                return any(map(lambda v: self._process_query(v, query.value), val))
            elif query.tag == '_EACH':
                return all(map(lambda v: self._process_query(v, query.value), val))
            elif query.tag == '_OR':
                return any(map(lambda v: self._process_query(val, v), query.value))
            elif query.tag == '_AND':
                return all(map(lambda v: self._process_query(val, v), query.value))
            elif query.tag == '_LIKE':
                import re
                ptn = re.compile(query.value
                                .replace('.', '\\.')
                                .replace('*', '.*')
                                .replace('%', '.*')
                                .replace('?', '.')
                                .replace('_', '.')
                                .replace('#', '[0-9]')
                                .replace('[!', '[^'))
                return ptn.match(val)
            elif query.tag == '_BETWEEN':
                return query.value[0] <= val < query.value[1]
        else:
            return val == query

    def select1(self, obj):
        v = list(self.select(obj))
        assert len(v) == 1
        return v[0]

    def delete(self, obj):
        self._conn.get_collection(self._app_name, self._collection_name)['data'].remove(obj)

    def update(self, oldobj, newobj):
        data = self._conn.get_collection(self._app_name, self._collection_name)['data']
        pos = data.index(oldobj)
        data[pos] = newobj

    def dump(self):
        return self._conn.get_collection(self._app_name, self._collection_name)

    def restore(self, objects):
        col = self._conn.get_collection(self._app_name, self._collection_name)
        col.update(objects)

    @property
    def schema(self):
        return self._schema

def collections(conn):
    for r, d, f in os.walk(conn):
        for e in f:
            if e.endswith('.json'):
                o = stdjson.read(open(r + e).read())
                yield {
                    'collectionName': o['collectionName'],
                    'schema': o['schema'],
                    'appName': o['appName']
                }

