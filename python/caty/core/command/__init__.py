# coding:utf-8
from __future__ import with_statement
import caty.jsontools as json
from optparse import OptionParser
from itertools import *
from functools import partial
from caty.core.command.exception import *
from caty.core.i18n import I18nMessageWrapper
import types
import caty.util as util
from caty.core.exception import InternalException
from caty.util.collection import OverlayedDict
from caty import UNDEFINED

__all__ = ['Command', 'Builtin', 'ScriptError', 'PipelineInterruption', 'PipelineErrorExit', 'compile_builtin']



class Command(object):
    u"""コマンド基底クラス。
    すべてのコマンドは入力チャンネルと出力チャンネルを持ち、
    関数のように呼び出し可能であるとする。
    このクラスのサブクラスは profile と profile_container の二つのプロパティを持つ。
    このプロパティの実体は caty.schema.commandprofile で定義された
    コマンド型宣言オブジェクトであり、コマンドの入出力の型を定義する。

    これはシステムの初期化時に /schema/ 以下の .casm ファイルで定義された
    コマンドの型指定からインジェクトされる。
    そのため、コマンドクラスの実装に際しては必ずスキーマを書かなければならない。

    schema, env プロパティはそれぞれスキーマモジュールの各関数/クラスへの参照と
    環境変数へのアクセスオブジェクトであり、これらは常にインジェクトされる。
    他のプロパティは入出力をのぞき、基本的にコマンド型宣言の reads, updates, uses 句に
    基づいてインジェクトされる。型宣言に記述の無い Caty ファシリティにはアクセスできない。
    """

    def __init__(self, opts_ref, args_ref, type_args=[]):
        assert type_args != None
        self._profile = self.profile_container.determine_profile(opts_ref, args_ref)
        self.__type_args = type_args
        self.__var_loader = VarLoader(opts_ref, args_ref, self._profile)
        self.__var_storage = VarStorage(None, None)
        self._annotations = self.profile_container.get_annotations()
        self._mode = set([u'console', u'web', u'test']).intersection(self._annotations)
        self._defined_application = self.profile_container.defined_application
        self.__type_var_names = self.profile_container.type_var_names
        self.async_queue = self._defined_application.async_queue
        self.__facility_names = set()
        self._id = '%s(%s)' % (self.profile_container.name, self.profile_container.uri)
        self.__current_application = None
        self.__facility_names = []
        self.__i18n = None

    def get_command_id(self):
        return self._id

    @property
    def i18n(self):
        if self.__i18n == None:
            return self._defined_application.i18n
        else:
            return self.__i18n

    @property
    def profile(self):
        u"""コマンドの入出力のスキーマ情報オブジェクト。
        入出力のスキーマは多相型への対応のために不変オブジェクトになっていないが、
        基本的に値の変更は行わないこと。
        """
        return self._profile

    @property
    def annotations(self):
        u"""コマンドに対するアノテーション。
        アノテーションではコマンドがどのような条件で動作するかといった情報を付け加える。
        """
        return self._annotations

    @property
    def name(self):
        return self.profile_container.name

    @property
    def current_app(self):
        return self.__current_application

    def set_facility(self, facilities):
        u"""ファシリティの設定。
        フレームワーク側で行う処理なので、一般のコマンド実装者が直に使うべきではない。
        """
        _set = set()
        self.__current_application = facilities.app
        self.__i18n = I18nMessageWrapper(self._defined_application.i18n, facilities['env'])
        for mode, decl in self.profile.facilities:
            name = decl.name
            key = decl.alias if decl.alias else name
            facility = facilities[name]
            if mode == 'reads':
                facility = facility.read_mode
            elif mode == 'updates':
                facility = facility.update_mode
            elif mode == 'uses':
                facility = facility.dual_mode
            # Dummy で定義されてない（=ユーザ定義）ファシリティは、
            # 定義元のアプリケーションへの参照に差し替える
            if self._defined_application.name not in ('builtin', 'global') and not 'volatile' in self._annotations:
                facility.application = self._defined_application
            setattr(self, key, facility)
            _set.add(name)
        # 互換性維持のため、envとschemaを追加
        if not 'env' in _set:
            setattr(self, 'env', facilities['env'].read_mode)
            _set.add('env')
        if not 'schema' in _set:
            setattr(self, 'schema', facilities['schema'].read_mode)
            _set.add('schema')
        
        # アプリケーション固有設定はすべてのコマンドから読み取り可能
        if not 'config' in _set:
            setattr(self, 'config', facilities['config'].read_mode)
            _set.add('config')

        # ロギング機能は常にセットする
        if not 'logger' in _set:
            setattr(self, 'logger', facilities['logger'].read_mode)
            _set.add('logger')
        self.__facility_names = _set

        _ta = []
        for t in self.__type_args:
            s = self.schema[t].clone()
            _ta.append(s)
        self.profile.apply(dict(zip(self.__type_var_names, _ta)))
        self._in_schema = self.profile.in_schema
        self._out_schema = self.profile.out_schema

    def get_facility(self, facility_name):
        u"""ファシリティの取得。
        指定されたファシリティが存在しない場合、 None を返す。
        """
        if hasattr(self, facility_name):
            return getattr(self, facility_name)
        else:
            return None

    def set_var_storage(self, storage):
        self.__var_storage = storage

    @property
    def facility_names(self):
        return self.__facility_names

    @property
    def var_storage(self):
        return self.__var_storage

    def _prepare(self):
        self._init_opts()
        opts = self._opts
        args = self._args
        if opts:
            for k, v in opts.items():
                self.__var_storage.opts[k] = v
        if args:
            self.__var_storage.opts['_ARGV'] = [u""] + args
        else:
            self.__var_storage.opts['_ARGV'] = [u""]
        if opts:
            self.__var_storage.opts['_OPTS'] = opts
        else:
            self.__var_storage.opts['_OPTS'] = {}
        if opts is not None and args:
            self.setup(opts, *args)
        elif opts:
            self.setup(opts)
        elif args:
            self.setup(*args)
        else:
            self.setup()

    def _init_opts(self):
        self._opts, self._args = self.__var_loader.load(self.__var_storage)

    def setup(self): pass

    @property
    def in_schema(self):
        u"""入力スキーマ。
        """
        return self._in_schema

    @property
    def out_schema(self):
        u"""出力スキーマ。
        """
        return self._out_schema

    def __call__(self, input):
        if 'deprecated' in self.annotations:
            util.cout.writeln(u'[DEBUG] Deprecated: %s' % self.name)
        if self._mode: # @console など、特定のモードでしか動かしてはいけないコマンドのチェック処理
            mode = self.env.get('CATY_EXEC_MODE')
            if not self._mode.intersection(set(mode)):
                raise InternalException(u"Command $name can not use while running mode $mode", 
                                        name=self.profile_container.name,
                                        mode=str(mode)
                )
        try:
            self.__var_storage.new_scope()
            self._prepare()
            self.in_schema.validate(input)
            if self.profile.in_schema.type == 'void':
                r = self.execute()
            else:
                r = self.execute(input)
            self.out_schema.validate(r)
            if 'commit-point' in self.profile_container.get_annotations():
                for n in self.__facility_names:
                    getattr(self, n).commit()
            if isinstance(r, list):
                while r and r[-1] is UNDEFINED:
                    r.pop(-1)
            return r
        finally:
            self.__var_storage.del_scope()

    def accept(self, visitor):
        return visitor.visit_command(self)

    def execute(self, *args, **kwds):
        raise NotImplementedError

    def error(self, json_obj):
        u"""コマンドをエラーとして終了させる。
        このメソッドが呼ばれた後はエラーハンドラーに処理が委譲され、
        後のパイプラインは一切処理されなくなる。
        """
        raise PipelineErrorExit(json_obj)

    def exit(self, json_obj):
        u"""コマンドを json_obj を出力にして終了する。
        """
        raise PipelineInterruption(json_obj)

    def clone(self):
        raise NotImplementedError()

    def _new_facility(self):
        from caty.core.facility import FacilitySet
        fs = {}
        for n in self.__facility_names:
            f = getattr(self, n)
            fs[n] = f.start()
        return FacilitySet(fs, self.__current_application)

    def _internal_commit(self):
        for n in self.__facility_names:
            f = getattr(self, n)
            f.commit()
                
    def call(self, line, input):
        fset = self._new_facility()
        interpreter = self._defined_application.interpreter.file_mode(fset)
        c = interpreter.build(line)
        return c(input)


class Builtin(Command):
    u"""組み込みコマンドのベースクラス。
    組み込みコマンドはコマンド宣言をファイルではなく
    プロパティとして直に記述する。
    この時は文字列としてスキーマを記述し、それをスキーマオブジェクトに変換、
    クラスの属性として追加という流れになる。

    このクラス自体は特に何もせず、マーカーとしてのみ使う。
    """

class Filter(Command):
    u"""テンプレートのフィルターにも使われるコマンドのベースクラス。
    """

class Internal(Builtin):
    u"""内部コマンドクラス。
    一部のコマンドは Caty システムに直接触る必要がある。
    そのようなコマンドはこのクラスを継承すること。
    ユーザ定義コマンドは基本的に使ってはいけない。
    """
    def set_facility(self, facilities):
        self._facilities = facilities
        self._system = facilities.system
        self._app = facilities.app
        Builtin.set_facility(self, facilities)

class Syntax(Builtin):
    u"""Caty スクリプトの構文要素のベースクラス。
    Caty スクリプトではオブジェクトやリストの構築、分岐処理もコマンドとして実装する。
    それらのコマンドは通常とは異なったインスタンス化の経路を必要とするため、
    このクラスで必要な処理を提供する。
    """
    def __init__(self, opts_ref=None, args_ref=None):
        Builtin.__init__(self, opts_ref or [], args_ref or [], [])
        self._in_schema = self.profile.in_schema
        self._out_schema = self.profile.out_schema

    def _init_opts(self):
        pass

    def _prepare(self):
        pass

class Dummy(Command):
    def execute(self):
        raise NotImplementedError()

def new_dummy():
    class _Dummy(Command):
        def execute(self):
            raise NotImplementedError()
    return _Dummy

def scriptwrapper(profile, script):
    class Wrapper(Command):
        def __init__(self, opts_ref, args_ref, type_args=[]):
            self.profile_container = profile
            Command.__init__(self, opts_ref, args_ref, type_args)

        def execute(self, input=None):
            try:
                return script(input)
            finally:
                self.var_storage.del_masked_scope()

        def setup(self, *args, **kwds):
            pass

        def _prepare(self):
            self._init_opts()
            opts = self._opts
            args = self._args
            self.var_storage.new_maked_scope(opts, args)
            if opts:
                for k, v in opts.items():
                    self.var_storage.opts[k] = v
            if args:
                self.var_storage.opts['_ARGV'] = [u""] + args
                self.var_storage.args = [u""] + args
            else:
                self.var_storage.opts['_ARGV'] = [u""]
                self.var_storage.args = [u""]
            if opts:
                self.var_storage.opts['_OPTS'] = opts
            else:
                self.var_storage.opts['_OPTS'] = {}

        def set_var_storage(self, storage):
            Command.set_var_storage(self, storage)
            script.set_var_storage(self.var_storage)

        def set_facility(self, facilities):
            Command.set_facility(self, facilities)
            script.set_facility(facilities)

    return Wrapper

class VarStorage(object):
    u"""変数テーブル。
    コマンドライン引数やオプション引数がストアされる。
    """
    def __init__(self, opts, args):
        self.opts = OverlayedDict(opts if opts else {})
        self.args = args if args else []
        self.opts['_ARGV'] = args
        self.args_stack = []
        self.opts_stack = []

    def new_scope(self):
        self.opts.new_scope()
        self.args_stack.append(self.args)

    def del_scope(self):
        self.opts.del_scope()
        self.args = self.args_stack.pop(-1)

    def new_maked_scope(self, opts, args):
        self.opts_stack.append(self.opts)
        self.args_stack.append(self.args)
        self.opts = OverlayedDict(opts if opts else {})
        self.args = args if args else []
        self.opts['_ARGV'] = args

    def del_masked_scope(self):
        self.opts = self.opts_stack.pop(-1)
        self.args = self.args_stack.pop(-1)

    def __repr__(self):
        return repr(self.opts) + repr(self.args)

def compile_builtin(module, registrar):
    u"""ビルトインのコマンドのプロパティで定義されたコマンド宣言をコンパイルする。
    ビルトインのコマンドはすべて以下のプロパティを持っていなければならない。
    
    * command_decl

    このプロパティにはコマンド宣言を直に記述する。
    """
    for item in filter(lambda a: isinstance(a, types.TypeType), module.__dict__.values()):
        if issubclass(item, Builtin) and item != Builtin:
            schema_string = u"%s" % (item.command_decl)
            registrar.compile(schema_string)

class VarLoader(object):
    def __init__(self, opts_ref, args_ref, profile):
        self.opts = opts_ref
        self.args = args_ref
        self.profile = profile

    def load(self, storage):
        if self.profile.opts_schema.type == 'object':
            opts = self._load_opts(storage.opts)
        else:
            opts = None
        if self.profile.args_schema.type == 'array':
            args = self._load_args(storage.opts, storage.args)
        else:
            args = None
        return (self._to_option_value(self.profile.opts_schema.convert(opts)), 
                self.profile.args_schema.convert(args))

    def _load_opts(self, opts):
        o = {}
        for opt in self.opts:
            if opt.type == 'option':
                if opt.value is not None:
                    o[opt.key] = opt.value
                else:
                    o[opt.key] = True
            else:
                if opt.key in opts:
                    o[opt.key] = opts[opt.key]
                else:
                    if not opt.optional:
                        raise InternalException(u'Option des not suffice: $opt', opt=opt.key)
        return o

    def _load_args(self, opts, args):
        a = []
        for arg in self.args:
            if arg.type == 'arg':
                a.append(arg.value)
            elif arg.type == 'iarg':
                if arg.index < len(args):
                    a.append(args[arg.index])
                else:
                    if not arg.optional:
                        raise InternalException(u'Argument does not suffice: $index', index=arg.index)
            else:
                if arg.key in opts:
                    a.append(opts[arg.key])
                else:
                    if not arg.optional:
                        raise InternalException(u'Argument des not suffice: $index', index=arg.index)
        return a

    def _to_option_value(self, option):
        from caty import UNDEFINED
        if option is None: return
        value = JsonableValues()
        key_set = set()
        for k, v in option.items():
            key_set.add(k)
            value[k] = v
        for k, v in self.profile.opts_schema.items():
            if k not in key_set:
                value[k] = UNDEFINED
        return value

class JsonableValues(dict):
    def __setitem__(self, k, v):
        dict.__setitem__(self, k, v)
        object.__setattr__(self, k.replace('-', '_').replace(' ', ''), v)



