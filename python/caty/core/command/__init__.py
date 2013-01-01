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
from caty.core.schema.errors import JsonSchemaError
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
    """

    def __init__(self, opts_ref, args_ref, type_args=[], pos=(None, None), module=None):
        assert type_args != None
        self._opt_names = []
        self.__arg0 = None
        self.__arg0_ref = None
        if opts_ref:
            for o in opts_ref:
                if o.key == '0':
                    self.__arg0_ref = o
                else:
                    self._opt_names.append(o.key)
        if self.__arg0_ref:
            opts_ref.remove(self.__arg0_ref)
        self.__opts_ref = opts_ref
        self.__args_ref = args_ref
        self._opts = None
        self._args = None
        self.__type_args = type_args # コマンドラインで与えられた型引数
        self.__type_params = self.profile_container.type_params # デフォルトの型パラメータ。
        self.__var_loader = VarLoader(opts_ref, args_ref)
        self.__var_storage = VarStorage(None, None) # 基本的に実行時に置換される。
        self._annotations = self.profile_container.get_annotations()
        self._mode = set([u'console', u'web', u'test']).intersection(self._annotations)
        self._defined_application = self.profile_container.defined_application
        self.__facility_names = set()
        self._id = '%s(%s)' % (self.profile_container.name, self.profile_container.uri)
        self.__current_application = None
        self.__facility_names = []
        self.__i18n = None
        self.__pos = pos
        self.__module = module
        self.applied = False

    def _prepare(self):
        self._prepare_opts()
        self._set_profile()
        self._finish_opts()
        opts = self._opts
        args = self._args
        if opts:
            for k, v in opts.items():
                self.__var_storage.opts[k] = v
        if args:
            self.__var_storage.opts['_ARGV'] = [self.__arg0] + args
        else:
            self.__var_storage.opts['_ARGV'] = [self.__arg0]
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

    def _prepare_opts(self):
        self._opts, self._args = self.__var_loader.load(self.__var_storage)
        if self.__arg0_ref and not u'static' in self._annotations:
            self.__arg0 = self.__var_loader.load_arg0(self.__arg0_ref, self.__var_storage)

    def _finish_opts(self):
        from caty.jsontools import prettyprint
        try:
            self.__arg0_schema.validate(self.__arg0)
        except JsonSchemaError, e:
            info = e.error_report(self.i18n)
            throw_caty_exception(u'Arg0TypeError', prettyprint(info), errorInfo=info)
        if self.profile.opts_schema.type == 'object':
            try:
                self._opts = self.profile.opts_schema.fill_default(self.profile.opts_schema.convert(self._opts), True)
            except JsonSchemaError, e:
                info = e.error_report(self.i18n)
                throw_caty_exception(u'OptsTypeError', prettyprint(info), errorInfo=info)
        else:
            self._opts = None
        if self.profile.args_schema.type == 'array':
            try:
                self._args = self.profile.args_schema.convert(self._args)
            except JsonSchemaError, e:
                info = e.error_report(self.i18n)
                throw_caty_exception(u'ArgsTypeError', prettyprint(info), errorInfo=e.error_report(self.i18n))
        else:
            self._args = None

    def _set_profile(self):
        opts = self._opts
        args = self._args
        self._profile = self.profile_container.determine_profile(opts, args)
        _ta = []
        if self.__module and self.__type_args:
            schema = self.__module.schema_finder
            l = len(self.__type_args)
            for i, p in enumerate(self.profile_container.type_params):
                if i < l:
                    s = self.__type_args[i]
                    sb = self.__module.make_schema_builder()
                    sb._type_params = self.type_params
                    rr = self.__module.make_reference_resolver()
                    tn = self.__module.make_type_normalizer()
                    ta = self.__module.make_typevar_applier()
                    ta._init_type_params(self)
                    ta.real_root = False
                    t = tn.visit(s.accept(sb).accept(rr)).accept(ta)
                    x = p.clone(set())
                    x._schema = t
                    _ta.append(x)
        if _ta:
            self.apply_type_params(_ta)
        if self.type_params:
            self._in_schema, self._out_schema, self.__arg0_schema = self.profile.apply(self, self.profile_container.module)
        else:
            self._in_schema = self.profile.in_schema
            self._out_schema = self.profile.out_schema
            self.__arg0_schema = self.profile.arg0_schema

    def apply_type_params(self, type_params):
        if not type_params:
            return
        tp = []
        for param, _, arg in zip(type_params, self.__type_args, self.type_params):
            param.var_name = arg.var_name
            tp.append(param)
        if tp:
            self.__type_params = tp
            self.__type_args = []

    def get_command_id(self):
        return self._id

    @property
    def type_params(self):
        return self.__type_params

    @property
    def type_args(self):
        return self.__type_args

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

    @property
    def arg0(self):
        return self.__arg0

    def set_facility(self, facilities, target_app=None):
        u"""ファシリティの設定。
        フレームワーク側で行う処理なので、一般のコマンド実装者が直に使うべきではない。
        """
        if self.profile_container.implemented == 'none': return
        _set = set()
        self.__current_application = target_app or facilities.app
        self.__i18n = I18nMessageWrapper(self._defined_application.i18n, facilities['env'])
        for mode, decl in self.profile_container.profiles[0].facilities:
            name = decl.name
            key = decl.alias if decl.alias else name
            param = decl.param
            if name not in facilities:
                e = self.profile_container.module.get_facility_or_entity(name)
                if e:
                    name = e.canonical_name
            factory = facilities.get(name)
            if not factory:
                throw_caty_exception('FacilityNotDefined', u'Facility $name is not defined', name=name)
            if factory.is_entity:
                if param:
                    throw_caty_exception('InvalidOperation', u'Entity takes no parameter: $name', name=name)
                facility = factory.create(mode)
            else:
                facility = factory.create(mode, param)
            # Dummy で定義されてない（=ユーザ定義）ファシリティは、
            # 定義元のアプリケーションへの参照に差し替える
            if target_app:
                facility.application = target_app
                self.async_queue = target_app.async_queue
            elif self._defined_application.name not in ('caty', 'global') and not 'volatile' in self._annotations:
                facility.application = self._defined_application
                self.async_queue = self._defined_application.async_queue
            else:
                self.async_queue = self.__current_application.async_queue
            setattr(self, key, facility)
            _set.add(name)
        # 互換性維持のため、schemaを追加
        if not 'schema' in _set:
            setattr(self, 'schema', facilities['schema'].create(u'reads'))
            _set.add('schema')
        
        # アプリケーション固有設定はすべてのコマンドから読み取り可能
        if not 'config' in _set:
            setattr(self, 'config', facilities['config'].create(u'reads'))
            _set.add('config')

        # ロギング機能は常にセットする
        if not 'logger' in _set:
            setattr(self, 'logger', facilities['logger'].create(u'reads'))
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

    @property
    def throw_schema(self):
        u"""例外スキーマ
        """
        return self._profile.throw_schema

    @property
    def signal_schema(self):
        u"""シグナルスキーマ
        """
        return self._profile.signal_schema

    def accept(self, visitor):
        return visitor.visit_command(self)

    def execute(self, *args, **kwds):
        throw_caty_exception(
            'NotImplemented',
            self.name
        )

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
    
    @property
    def current_module(self):
        return self.__module

    @property
    def defined_module(self):
        return self.profile_container.module

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
    def set_facility(self, facilities, target=None):
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
        Builtin.__init__(self, opts_ref or [], args_ref or [], [], pos, module)

    def _prepare(self):
        self._set_profile()

class Dummy(Command):
    def execute(self, *args, **kwds):
        throw_caty_exception('NotImplemented', self.name)

def new_dummy():
    class _Dummy(Dummy):
        pass
    return _Dummy

def scriptwrapper(profile, scriptfactory):
    class Wrapper(Command):
        def __init__(self, opts_ref, args_ref, type_args=[], pos=(None, None), module=None):
            self.profile_container = profile
            self.scriptfactory = scriptfactory
            self.script = None
            self.type_var_applied = False
            Command.__init__(self, opts_ref, args_ref, type_args, pos, module)

        def execute(self, input=None):
            try:
                return self.script(input)
            finally:
                self.var_storage.del_masked_scope()

        def setup(self, *args, **kwds):
            pass

        def accept(self, visitor):
            return visitor.visit_script(self)

        def _prepare(self):
            self.script = self.scriptfactory() # 実体化は遅延して置かないと再帰コマンドの実体化ができない
            self.script.set_facility(self.facilities)
            self.script.set_var_storage(self.var_storage)
            self._prepare_opts()
            self._set_profile()
            self._finish_opts()

        def set_var_storage(self, storage):
            Command.set_var_storage(self, storage)

        def set_facility(self, facilities, target_app=None):
            Command.set_facility(self, facilities, target_app)
            self.facilities = facilities

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
        self.opts['_OPTS'] = opts if opts is not None else {}
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
    def __init__(self, opts_ref, args_ref):
        self.opts = opts_ref if opts_ref else []
        self.args = args_ref if args_ref else []

    def load_arg0(self, opt, storage):
        opts = storage.opts
        if opt.type == 'option':
            if opt.value != UNDEFINED:
                return opt.value
            else:
                return True
        elif opt.type == 'var':
            if opt.value.name in opts:
                return opts[opt.value.name]
            else:
                if not opt.optional:
                    raise KeyError(opt.value.name)
                elif opt.default is not UNDEFINED:
                    return opt.default
            elif opt.type == 'var_arg':
                i = int(opt.value.name)
                if i < len(args):
                    return args[i]
                else:
                    if not opt.optional:
                        raise Exception(u'Argument %%%d is not defined' % i)
                    elif opt.default is not UNDEFINED:
                        return opt.default

        elif opt.type == 'glob':
            return opts['_OPTS']
        else:
            if opt.key in opts:
                return opts[opt.key]
            else:
                if not opt.optional:
                    raise Exception(u'%%%s is not defined' % opt.key)

    def load(self, storage):
        from caty.core.spectypes import reduce_undefined
        opts = self._load_opts(storage.opts, storage.args)
        args = self._load_args(storage.opts, storage.args)
        return reduce_undefined(opts), reduce_undefined(args)

    def _load_opts(self, opts, args):
        o = MultiMap()
        for opt in self.opts:
            if opt.type == 'option':
                o[opt.key] = opt.value
            elif opt.type == 'var':
                if opt.value.name in opts:
                    o[opt.key] = opts[opt.value.name]
                else:
                    if not opt.optional:
                        raise Exception(u'Variable %%%s is not defined' % opt.value.name)
                    elif opt.default is not UNDEFINED:
                        o[opt.key] = opt.default
            elif opt.type == 'var_arg':
                i = int(opt.value.name)
                if i < len(args):
                    o[opt.key] = args[i]
                else:
                    if not opt.optional:
                        raise Exception(u'Argument %%%d is not defined' % i)
                    elif opt.default is not UNDEFINED:
                        o[opt.key] = opt.default

            elif opt.type == 'glob':
                o.update(opts['_OPTS'])
            else:
                if opt.key in opts:
                    o[opt.key] = opts[opt.key]
                else:
                    if not opt.optional:
                        raise Exception(u'Variable %%%s is not defined' % opt.key)
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
                        raise Exception(u'Argument %%%d is not defined' % arg.index)
                    elif arg.default is not UNDEFINED:
                        a.append(arg.default)
            elif arg.type == 'glob':
                a.extend(opts['_ARGV'][1:])
            else:
                if arg.key in opts:
                    a.append(opts[arg.key])
                else:
                    if not arg.optional:
                        raise Exception(u'Variable %%%s is not defined' % arg.key)
                    elif arg.default is not UNDEFINED:
                        a.append(arg.default)
                    else:
                        a.append(UNDEFINED)
        return a

