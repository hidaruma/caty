# coding: utf-8
import os
from caty.jsontools import prettyprint
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

    def _load(self, app_name, collection_name, schema_name):
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
        self._load(app_name, collection_name, schema_name)
        if app_name:
            if collection_name in self._data_map['apps'][app_name]:
                return
            self._data_map['apps'][app_name][collection_name] = {'app': app_name, 'schema': schema_name, 'collection_name': collection_name, 'data': []}
        else:
            if collection_name in self._data_map['global']:
                return
            self._data_map['global'][collection_name] = {'app': app_name, 'schema': schema_name, 'collection_name': collection_name, 'data': []}

    def commit(self):
        for tbl_name, tbl_data in self._data_map['global'].items():
            open(self.data_dir + '/' + tbl_name + '.json', 'wb').write(prettyprint(tbl_data))

        for app_name, tbl_map in self._data_map['apps'].items():
            for tbl_name, tbl_data in tbl_map.items():
                if not os.path.exists(self.data_dir + '/' + app_name + '/'):
                    os.mkdir(self.data_dir + '/' + app_name + '/')
                open(self.data_dir + '/' + app_name + '/' + tbl_name + '.json', 'wb').write(prettyprint(tbl_data))

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
    pass

def collections(conn):
    for r, d, f in os.walk(conn):
        for e in f:
            if e.endswith('.json'):
                o = stdjson.read(open(r + e).read())
                yield {
                    'collection_name': e.rsplit('.', 1)[0].replace('/', ':'),
                    'schema': o['schema'],
                    'app': o['app']
                }

