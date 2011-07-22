#coding: utf-8
READ = 0
UPDATE = 1
DUAL = 2

COMMIT = 0
ROLLBACK = 1
PEND = 2

import caty
from caty.core.exception import InternalException
from pbc import PbcObject, Contract
import weakref

class Facility(PbcObject):
    u"""あらゆるファシリティの基底クラス。
    Caty におけるファシリティとは、主にファイル、データベース、セッションなどのストレージを指す概念である。
    Caty のコマンドはファシリティを用いない限りあらゆるストレージへのアクセス手段を持つことができない。
    ファシリティの使用宣言はコマンド宣言で行い、この時読み込みモードで宣言されたファシリティは書き込み操作が不可能となる。
    逆もまた然りであり、読み書きの両方を行う場合は読み書きモードで宣言しなければならない。
    ただし、この読み書き権限の検証は個々のファシリティの実装者次第である。

    ファシリティは抽象的な概念であるため、このクラスではなんら具体的なストレージへのアクセスメソッドは宣言しない。
    具体的なストレージへのアクセス手段の宣言・定義は個々のサブクラスで行うものとし、このクラスでは
    ファシリティがどのモードで宣言されたかの情報と、あらゆるファシリティが実装しなければならない、
    あるいは適宜オーバーライドすべきいくつかの抽象メソッドを宣言するのみである。

    == 実装必須の抽象メソッド

    === clone()

    ファシリティにおける唯一必須の抽象メソッドがこの clone() である。
    このメソッドはファシリティがコマンドにセットされる度に呼ばれ、
    必ず自身と同じクラスのインスタンスを返さなければならない。
    不変クラスに関しては自身と同じインスタンスを返してもよいが、
    その場合は ReadOnlyFacility クラスを使うことを検討するべきである。

    == オーバーライドしても良いメソッド

    === start()

    start() メソッドはパイプラインの最初に各ファシリティについてただ一度ずつ呼ばれる。
    このメソッドではファシリティの使用前のセットアップのような事を行うことが想定されており、
    例えばデータベースアクセスのファシリティでコネクションを取得するなどが該当する。
    このメソッドも clone() 同様、自身と同じクラスのインスタンスを返すものとする。

    === commit(), rollback()

    ストレージアクセスを行うファシリティは、基本的にトランザクションをサポートしなければならない。
    ここでのトランザクションとは、あるパイプラインが成功した場合（例外を創出せず終了した場合）にのみ
    ストレージへの書き込みが行われ、そうでない場合は書き込みが一切行われないことを言う。

    トランザクションの分離レベルは READ COMMITTED であればよい。

    """

    __properties__ = ['mode']

    def __init__(self, mode=READ):
        self._mode = mode
        self._app = None

    def start(self):
        return self

    def commit(self):
        pass

    def rollback(self):
        pass

    def merge_transaction(self, another):
        u"""同一ファシリティの別インスタンスのトランザクション情報をマージする。
        request など、入れ子のトランザクションへの対応が目的である。
        """
        pass

    @property
    def read_mode(self):
        obj = self.__clone()
        obj._mode = READ
        return obj

    @property
    def update_mode(self):
        obj = self.__clone()
        obj._mode = DUAL
        return obj

    @property
    def dual_mode(self):
        obj = self.__clone()
        obj._mode = DUAL
        return obj

    @property
    def mode(self):
        return self._mode

    def application():
        def get(self):
            return self._app
        def set(self, v):
            self._app = v#weakref.proxy(v) if v is not None else v
        return get, set
    application = property(*application())

    def __clone(self):
        return self.clone()

    def clone(self):
        raise NotImplementedError(repr(self))

    if caty.DEBUG:
        def __invariant__(self):
            assert self.mode in (READ, UPDATE, DUAL)

        def _is_same_class(self, r, old, *args, **kwds):
            assert type(self) == type(r)

        def _is_not_same_instance(self, r, old, *args, **kwds):
            if self.mode == READ and r.mode == READ:
                return
            assert self is not r

        __clone = Contract(__clone)
        __clone.ensure += _is_same_class
        __clone.ensure += _is_not_same_instance

class ReadOnlyFacility(Facility):
    _mode = READ
    @property
    def update_mode(self):
        raise InternalException(u'Read only facility')

    @property
    def dual_mode(self):
        raise InternalException(u'Read only facility')

    def clone(self):
        return self

class FakeFacility(Facility):
    u"""便宜上ファシリティとして扱うオブジェクトのための擬似ファシリティクラス。
    FakeFacility を継承した場合、 (read|update|dual)_mode プロパティ及び clone は
    単に自身を戻すだけの実装が与えられる。
    """

    @property
    def read_mode(self):
        return self
    update_mode = read_mode
    dual_mode = read_mode
    clone = read_mode

class AccessManager(property):
    u"""
    read/update/dual の各モードに対してメソッドの呼び出し権限のチェックを行う。
    呼び出し不能なメソッドであった場合、例外が送出される。
    
    {{{
    class Foo(Facility):
        am = AccessManager()
        @am.read
        def read_method(self):
            ...

        @am.update
        def update_method(self):
            ...
    }}}

    このとき observe プロパティを用い、 AccessManager 側で権限チェックは行わないものの、
    呼び出しの監視を行う事が可能である。
    AccessManager クラスでは何も行わないので、サブクラスで適宜定義すること。
    これは TransactionalAccessManager の実装がその例となっている。
    """
    def __init__(self):
        property.__init__(self, lambda name: lambda obj, *args, **kwds: self.execute(obj, name, *args, **kwds))
        self.reader = {}
        self.updator = {}
        self.observed = {}
    

    def read(self, f):
        self.reader[f.__name__] = f
        return self.fget(f.__name__)

    def update(self, f):
        self.updator[f.__name__] = f
        return self.fget(f.__name__)

    def observe(self, f):
        self.observed[f.__name__] = f
        return self.fget(f.__name__)

    def execute(self, obj, name, *args, **kwds):
        fun = self._get_function(obj, name)
        if not fun:
            raise InternalException(u'Operation not allowed: object=$obj, method=$method, mode=$mode',
                                    obj=repr(obj), method=str(name), mode=str(obj.mode))
        return fun(obj, *args, **kwds)

    
    def _get_function(self, obj, name):
        mode = Facility.mode.fget(obj)
        if name in self.observed:
            return self.observed[name]
        elif mode == READ:
            return self.reader.get(name)
        elif mode == UPDATE:
            return self.updator.get(name)
        elif mode == DUAL:
            r = self.updator.get(name, None)
            if not r:
                return self.reader.get(name)
            else:
                return r
        else:
            raise Exception(name)

class TransactionalAccessManager(AccessManager):
    u"""
    トランザクション制御付きアクセスマネージャ。
    通常のファイルシステムなど、トランザクション機能を持たないファシリティに対して適用する。
    write や delete などの破壊的変更については要求を全てキャッシュし、あとでまとめて実行する。
    read などの非破壊操作に対しては、破壊的変更があたかも行われたかのように振る舞う。
    これらの処理は全てサブクラスで実装すること。

    {{{
    class Foo(Facility):
        tam = TransactionalAccessManager()
        commit = tam.commit
        rollback = tam.rollback
    }}}
    """


    def execute(self, obj, name, *args, **kwds):
        fun = getattr(obj.__class__, name)
        if name in self.updator:
            return self.do_update(obj, fun, *args, **kwds)
        elif name in self.reader:
            return self.do_read(obj, fun, *args, **kwds)
        elif name in self.observed:
            return self.do_observed(obj, fun, *args, **kwds)
        else:
            raise Exception(name)

    def do_update(self, obj, fun, *args, **kwds):
        raise NotImplementedError()

    def do_read(self, obj, fun, *args, **kwds):
        raise NotImplementedError()

    def do_observed(self, obj, fun, *args, **kwds):
        raise NotImplementedError()

    def commit(self):
        raise NotImplementedError()

    def rollback(self):
        raise NotImplementedError()


from caty.core.command import Command
from caty.core.command.exception import PipelineInterruption
class TransactionAdaptor(Command):
    u"""Caty スクリプトの実行可能形式に対するアダプタ。
    成功時にはファシリティの処理をコミットし、失敗時にはロールバックする。
    PipelineInterruption の時はコミットとなるのに注意。
    """
    def __init__(self, command, facilities):
        self._facilities = facilities
        self._command = command

    def __call__(self, input):
        try:
            r = self._command(input)
            self.commit()
            return r
        except PipelineInterruption, e:
            self.commit()
            raise
        except:
            self.rollback()
            raise
    
    def commit(self):
        vcs = None
        for k, v in self._facilities.items():
            if k == 'vcs': # vcs は mafs の後にコミットしないとおかしな事になるので
                vcs = v
            else:
                v.commit()
        if vcs:
            vcs.commit()

    def rollback(self):
        for k, v in self._facilities.items():
            v.rollback()

    @property
    def in_schema(self):
        return self._command.in_schema

    @property
    def out_schema(self):
        return self._command.out_schema

class TransactionDiscardAdaptor(TransactionAdaptor):
    u"""常に処理をロールバックするアダプタ。
    主にテスト用。
    """
    def __init__(self, command, facilities):
        self._facilities = facilities
        self._command = command

    def __call__(self, input):
        try:
            r = self._command(input)
            self.rollback()
            return r
        except PipelineInterruption, e:
            self.rollback()
            raise
        except:
            self.rollback()
            raise
    
class TransactionPendingAdaptor(TransactionAdaptor):
    u"""コミットもロールバックもせず、ファシリティの状態を保持するアダプタ。
    主にテスト用。
    """
    def __init__(self, command, facilities):
        self._facilities = facilities
        self._command = command
 
    def commit(self):
        pass
    
    def rollback(self):
        pass

import caty
class FacilitySet(object):
    u"""ファシリティ一式を格納するオブジェクト。
    辞書類似のインターフェースを持つが、不変オブジェクトである事が異なる。
    """
    def __init__(self, dictionaly, app):
        for v in dictionaly.values():
            assert isinstance(v, Facility)
            # 呼び出し元のアプリケーションをセット
            v.application = app
        self._facilities = dictionaly
        self._app = app # ファシリティの作成元
        self._system = app._system

    @property
    def system(self):
        return self._system

    @property
    def app(self):
        return self._app

    def __getitem__(self, k):
        return self._facilities[k]

    def get(self, k, default=None):
        u"""不明なキーへのアクセスは常にエラー。
        フレームワーク内部でしか基本的に使わないクラスではあるが、一応。
        """
        return self._facilities[k]

    def keys(self):
        return self._facilities.keys()

    def values(self):
        return self._facilities.values()

    def items(self):
        return self._facilities.items()

    def iterkeys(self):
        return self._facilities.iterkeys()

    def itervalues(self):
        return self._facilities.itervalues()

    def iteritems(self):
        return self._facilities.iteritems()

    def clone(self):
        u"""主にCatyFITの各テスト実行時にファシリティを隔離するために使う。
        """
        n = {}
        for k, v in self._facilities.items():
            n[k] = v.start()
        f = FacilitySet(n, self._app)
        if 'interpreter' in self.keys():
            n['interpreter'] = self.app._interpreter.file_mode(f)
        return f
