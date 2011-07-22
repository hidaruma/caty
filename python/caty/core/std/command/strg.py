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
    u"""JSON ストレージ操作コマンド用の Mix-in クラス。
    コードの簡潔さと処理の重複の回避のために、各コマンドに多重継承を用いて Mix-in する。
    """
    @property
    def collection(self):
        if ':' in self._collection_name:
            app, collection = self._collection_name.split(':', 1)
            return self.storage(collection, app)
        else:
            return self.storage(self._collection_name)


class CreateCollection(Builtin):
    command_decl = u"""
    /**
     * JSON スキーマに対応したコレクションの作成。
     * 第一引数はスキーマ名であり、省略不可能である。またこのスキーマは object 型でなければならない。
     * 第二引数はコレクション名であり、省略した場合スキーマ名がコレクション名となる。
     * 既にコレクションが存在する場合何もせず終了する。
     */
    command create-collection {"as-global": boolean} [string, string?] :: void -> void
        reads schema
        updates storage
        refers python:caty.command.strg.CreateCollection;
    """
    def setup(self, opts, schema_name, collection_name=None):
        self._schema_name = schema_name
        self.schema[schema_name]
        self._collection_name = collection_name if collection_name else schema_name
        self._global = opts.as_global

    def execute(self):
        self.storage(self._collection_name).create(self._schema_name, self._global)

class DropCollection(Builtin, StorageAccessor):
    command_decl = u"""
    /**
     * コレクションの削除。
     */
    command drop-collection [string] :: void -> void
        updates storage
        refers python:caty.command.strg.DropCollection;
    """
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
    command_decl = u"""
    /**
     * コレクション名とそのスキーマ一覧の表示。
     */
    command list-collections :: void -> [Collection*]
        reads storage
        refers python:caty.command.strg.List;
    """
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
    command_decl = u"""
    /**
     * JSON ストレージの検索。
     * 引数で指定されたコレクションに対して入力値をクエリとして検索を行い、その結果を返す。
     * コレクション以降の引数はオプションであり、検索結果のオブジェクトに含める要素のパスを指定する。
     *
     * --limit オプションは検索結果の最大件数を指定する。デフォルトでは無制限に値を取得する。
     * --offset オプションは検索の開始位置を指定する。デフォルトでは最初から値を取得する。
     * --order-by オプションはソートに用いるプロパティ名を指定する。デフォルトでは insert された順に値を取得する。
     * 
     * 検索クエリには JSON オブジェクトを用いる。
     *
     * {{{
     * {"birth": 1984} | strg:select person 
     * }}}
     *
     * 上記のクエリの結果は、 person コレクションの birth の値が 1984 であるオブジェクトの配列となる。
     * 特に指定されなかった項目に付いては、その値が何であれ取得される。
     *
     * また、以下のように特殊なタグを使って検索する事も出来る。
     *
     * {{{
     * {"name": @_OR [@_LIKE "山田%", @_LIKE 鈴木%"]} | strg:select person
     * }}}
     *
     * この場合は name の値が "山田" か "鈴木" で始まるオブジェクトのリストが検索結果となる。
     *
     * クエリが null の場合、全件取得が行われる。
     *
     * これら特殊タグの一覧を以下に示す。
     *
     * * @_ANY              検索条件なし
     * * @_OR [条件リスト]  [条件リスト]のうちいずれかを満たす
     * * @_AND [条件リスト] [条件リスト]をすべて満たす
     * * @_EACH <条件>      配列の要素全てが条件を満たす（配列型の値に対してのみ使用可能）
     * * @_CONTAINS <条件>  配列の要素が一つでも条件を満たす（配列型の値に対してのみ使用可能）
     * * @_LIKE <パターン>  <パターン>に一致する（string型に対してのみ使用可能）
     * * @_NOT_NULL         null でない 
     * * @_LT <数値>        オブジェクトの値が<数値>より小さい
     * * @_LE <数値>        オブジェクトの値が<数値>より小さいあるいは等しい
     * * @_GT <数値>        オブジェクトの値が<数値>より大きい
     * * @_GE <数値>        オブジェクトの値が<数値>より大きいあるいは等しい
     * 
     */
    command select<T> {
                    "limit": pinteger, 
                    "reverse":boolean, 
                    "order-by": string, 
                    "offset": pinteger,
                   } [string, string*] :: any -> [T*]
        reads storage
        refers python:caty.command.strg.Select;
    """
    def setup(self, opts, collection_name, *args):
        self._collection_name = collection_name
        self._limit = -1 if not opts.limit else opts.limit
        self._offset = 0 if not opts.offset else opts.offset
        self._order_by = opts.order_by
        self._reverse = opts.reverse
        self._path = args
        l = self.schema['list']
        l.schemata = [self.collection.schema]
        self._out_schema = l

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
                return [q.find(v).next() for v in r]
            else:
                queries = map(build_query, map(lambda a:'$.' + a, path))
                return [[q.find(v).next() for q in queries] for v in r]


from caty.core.schema.base import TagSchema, NullSchema
class Select1(Builtin, StorageAccessor):
    command_decl = u"""
    /**
     * 一件のデータ取得。
     * クエリの指定の仕方は select と同様である。
     * 検索結果が一件でない場合、 @Error が出力値となる。
     *
     */
    command select1<T> [string] :: any -> T | @Error string
        reads storage
        refers python:caty.command.strg.Select1;
    """
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
    command_decl = u"""
    /**
     * JSON コレクションに入力値を挿入する。
     * --alow-dup オプションが指定された場合、重複した値を挿入可能になる。
     * デフォルトでは重複した値を挿入しようとした場合は値が挿入されず、 @NG が出力値となる。
     * 
     */
    command insert<T> {"allow-dup": boolean} [string] :: T -> @OK null | @NG null
        updates storage
        refers python:caty.command.strg.Insert;
    """
    def setup(self, opts, collection_name):
        self._collection_name = collection_name
        self._allow_dup = opts.allow_dup
        self._in_schema = self.collection.schema

    def execute(self, input):
        if not self._allow_dup:
            l = list(self.collection.select(input, -1, 0))
            if len(l) !=0:
                return tagged(u'NG', None)
        self.collection.insert(input)
        return tagged(u'OK', None)

class Update(Builtin, StorageAccessor):
    command_decl = u"""
    /**
     * JSON ストレージの更新。
     * 入力値の最初の要素で JSON ストレージを検索し、その結果を第二の入力値で更新する。
     */
    command update [string] :: [any, any] -> null
        updates storage
        refers python:caty.command.strg.Update;
    """
    def setup(self, collection_name):
        self._collection_name = collection_name

    def execute(self, input):
        self.collection.update(*input)

class Delete(Builtin, StorageAccessor):
    command_decl = u"""
    /**
     * JSON コレクションの値の削除。
     * 
     */
    command delete [string] :: any -> null
        updates storage
        refers python:caty.command.strg.Delete;
    """
    def setup(self, collection_name):
        self._collection_name = collection_name

    def execute(self, input):
        self.collection.delete(input)

class Dump(Builtin, StorageAccessor):
    command_decl = u"""
    /**
     * コレクションのダンプ。
     * 出力結果は {"collectionName":コレクション名, "schema": スキーマ名, "data": データの配列} という形式になる。
     */
    command dump 
        [string] :: void -> DumpInfo
        reads storage
        refers python:caty.command.strg.Dump;
    """

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
    command_decl = u"""
    /**
     * ダンプされた情報のリストア。
     * コレクションを新たに生成し、すべてのデータを再度挿入する。
     * 既存のコレクションが存在する場合、一旦ドロップされる。
     */
    command restore :: DumpInfo -> void
        uses storage
        refers python:caty.command.strg.Restore;
    """
    def execute(self, input):
        storage = self.storage(input['collectionName'])
        storage.drop()
        storage.create(input['schema'])
        storage = self.storage(input['collectionName'])
        storage.restore(input['data'])

