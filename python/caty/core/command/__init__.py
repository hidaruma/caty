# coding:utf-8
from __future__ import with_statement
import caty.jsontools as json
from optparse import OptionParser
from itertools import *
from functools import partial
from caty.core.command.exception import *
from caty.core.exception import throw_caty_exception
from caty.core.i18n import I18nMessageWrapper
import types
import caty.util as util
from caty.core.exception import InternalException
from caty.util.collection import OverlayedDict, MultiMap
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

    def __init__(self, opts_ref, args_ref, type_args=[], pos=(None, None), module=None):
        assert type_args != None
        if opts_ref:
            self._opt_names = set([o.key for o in opts_ref])
        else:
            self._opt_names = []
        self._profile = self.profile_container.determine_profile(opts_ref, args_ref)
        self.__type_args = type_args
        self.__var_loader = VarLoader(opts_ref, args_ref, self._profile)
        self.__var_storage = VarStorage(None, None)
        self._annotations = self.profile_container.get_annotations()
        self._mode = set([u'console', u'web', u'test']).intersection(self._annotations)
        self._defined_application = self.profile_container.defined_application
        self.__facility_names = set()
        self._id = '%s(%s)' % (self.profile_container.name, self.profile_container.uri)
        self.__current_application = None
        self.__facility_names = []
        self.__i18n = None
        self.__pos = pos
        _ta = []
        if module:
            schema = module.schema_finder
            l = len(self.__type_args)
            for i, p in enumerate(self.profile_container.type_params):
                if i < l:
                    t = self.__type_args[i]
                    s = schema[t]
                    x = p.clone(set())
                    x._schema = s
                    _ta.append(x)
        self.__type_params = _ta
        if self.type_params:
            self._in_schema, self._out_schema = self.profile.apply(self, self.profile_container.module)
        else:
            self._in_schema = self.profile.in_schema
            self._out_schema = self.profile.out_schema

    def get_command_id(self):
        return self._id

    @property
    def type_params(self):
        return self.__type_params

    @property
    def col(self):
        return self.__pos[0]

    @property
    def line(self):
        return self.__pos[1]

    @property
    def i18n(self):
        if self.__i18n == None:
            return self._defined_application.i18n
        else:
            return self.__i18n

    @property
    def var_loader(self):
        return self.__var_loader

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
            if self._defined_application.name not in ('caty', 'global') and not 'volatile' in self._annotations:
                facility.application = self._defined_application
                self.async_queue = self._defined_application.async_queue
            else:
                self.async_queue = self.__current_application.async_queue
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
        if opts is not None and args is not None:
            self.setup(opts, *args)
        elif opts is not None:
            self.setup(opts)
        elif args is not None:
            self.setup(*args)
        else:
            self.setup()

    def _init_opts(self):
        self._opts, self._args = self.__var_loader.load(self.__var_storage)

    def setup(self, *args, **kwds): pass

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

    def accept(self, visitor):
        return visitor.visit_command(self)

    def execute(self, *args, **kwds):
        throw_caty_exception(
            'NotImplemented',
            self.name
        )

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
    def __init__(self, opts_ref=None, args_ref=None, pos=(None, None), module=None):
        Builtin.__init__(self, opts_ref or [], args_ref or [], [], module)
        self._in_schema = self.profile.in_schema
        self._out_schema = self.profile.out_schema

    def _init_opts(self):
        pass

    def _prepare(self):
        pass

class Dummy(Command):
    def execute(self, *args, **kwds):
        throw_caty_exception('NotImplemented', self.name)

def new_dummy():
    class _Dummy(Dummy):
        pass
    return _Dummy

def scriptwrapper(profile, script):
    class Wrapper(Command):
        def __init__(self, opts_ref, args_ref, type_args=[], pos=(None, None), module=None):
            self.profile_container = profile
            self.script = script
            Command.__init__(self, opts_ref, args_ref, type_args, pos, module)


        def execute(self, input=None):
            try:
                return script(input)
            finally:
                self.var_storage.del_masked_scope()

        def setup(self, *args, **kwds):
            pass

        def accept(self, visitor):
            return visitor.visit_script(self)

        def _prepare(self):
            self._init_opts()

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
        from copy import deepcopy
        self.opts = OverlayedDict(deepcopy(opts) if opts else {})
        self.args = args if args else []
        self.opts['_ARGV'] = args
        self.opts['_OPTS'] = opts
        self.args_stack = []
        self.opts_stack = []

    def clone(self):
        from copy import deepcopy
        n = VarStorage({}, [])
        n.opts = self.opts.clone()
        n.args = deepcopy(self.args)
        n.opts['_ARGV'] = n.args
        for a in self.args_stack:
            n.args_stack.append(deepcopy(a))
        for o in self.opts_stack:
            n.opts_stack.append(o.clone())
        return n

    def new_scope(self):
        self.opts.new_scope()
        self.args_stack.append(self.args)

    def del_scope(self):
        self.opts.del_scope()
        self.args = self.args_stack.pop(-1)

    def new_masked_scope(self, opts, args):
        self.opts_stack.append(self.opts)
        self.args_stack.append(self.args)
        self.opts = OverlayedDict(opts if opts else {})
        self.args = args if args else []
        self.opts['_ARGV'] = args

    def del_masked_scope(self):
        self.opts = self.opts_stack.pop(-1)
        self.args = self.args_stack.pop(-1)

    def __repr__(self):
        return repr(self.opts) + repr(self.args) + repr(self.opts_stack) + repr(self.args_stack)

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
            opts = self.profile.opts_schema.fill_default(self.profile.opts_schema.convert(opts))
        else:
            opts = None
        if self.profile.args_schema.type == 'array':
            args = self._load_args(storage.opts, storage.args)
            args = self.profile.args_schema.convert(args)
        else:
            args = None
        return opts, args

    def _load_opts(self, opts):
        o = MultiMap()
        for opt in self.opts:
            if opt.type == 'option':
                if opt.value != UNDEFINED:
                    o[opt.key] = opt.value
                else:
                    o[opt.key] = True
            elif opt.type == 'var':
                if opt.value.name in opts:
                    o[opt.key] = opts[opt.value.name]
                else:
                    if not opt.optional:
                        raise KeyError(opt.value.name)
            elif opt.type == 'glob':
                o.update(opts['_OPTS'])
            else:
                if opt.key in opts:
                    o[opt.key] = opts[opt.key]
                else:
                    if not opt.optional:
                        raise InternalException(u'Option des not suffice: $opt', opt=opt.key)
        return o.to_dict()

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
            elif arg.type == 'glob':
                a.extend(opts['_ARGV'][1:])
            else:
                if arg.key in opts:
                    a.append(opts[arg.key])
                else:
                    if not arg.optional:
                        raise InternalException(u'Argument des not suffice: $index', index=arg.key)
                    else:
                        a.append(UNDEFINED)
        while a and a[-1] == UNDEFINED:
            a.pop(-1)
        return a

