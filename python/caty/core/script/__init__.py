# coding:utf-8
from caty.core.casm.module import FilterModule, LocalModule
from caty.core.facility import (FakeFacility, 
                                TransactionAdaptor, 
                                TransactionDiscardAdaptor, 
                                TransactionPendingAdaptor,
                                COMMIT,
                                ROLLBACK,
                                PEND)
from caty.core.script.parser import ScriptParser, NothingTodo
from caty.core.script.builder import CommandBuilder, CommandCombinator
from caty.core.script.inferer import TypeInferer
from caty.core.script.interpreter import CommandExecutor
from caty.core.script import node
from caty.core.std.command import builtin
from caty.core.command import Builtin, Syntax, Command, VarStorage, PipelineInterruption, PipelineErrorExit, ScriptError
from caty.core.command.profile import CommandUsageError
from caty.core.command.usage import CommandUsage
from caty.util.cache import memoize, Cache
from caty.util import error_to_ustr
from caty import util
import types

def initialize(registrar, app, system):
    return ScriptModule(registrar, app, system)

class ScriptModule(object):
    def __init__(self, registrar, app, system):
        #namespace = {}
        filters = FilterModule(system)
        for n, profile_container in registrar.get_module('filter').command_profiles:
            try:
                if 'filter' in profile_container.get_annotations():
                    filters.command_ns[n.split(':')[-1]] = profile_container
            except Exception, e:
                raise
        self._finder = registrar.schema_finder
        self._filter_finder = LocalModule(filters)
        self._enable_cache = system.enable_script_cache
        self._cache = Cache(1000)
        self._app = app
        self._registrar = registrar

    @property
    def enable_cache(self):
        return self._enable_cache

    @property
    def cache(self):
        return self._cache

    @property
    def finder(self):
        return self._finder

    def shell_mode(self, facilities):
        return ShellCommandCompiler(facilities, self)

    def file_mode(self, facilities):
        return ScriptCommandCompiler(facilities, self)

class AbstractCommandCompiler(FakeFacility):
    u"""コマンド文字列からコマンドを構築するためのオブジェクト。
    実際の処理は CommandBuilder や parse_command に移譲し、
    このクラスでは対話シェルからの入力の受付や前二者の紐付けなどを行う。
    """
    def __init__(self, facilities, module):
        self._facilities = facilities
        self.prev_string = u''
        self.prev_opts = None
        self.prev_args = None
        self._cache = module.cache
        self.cache_enabled = module.enable_cache
        self._finder = module.finder
        self.module = module
    
    def facilities():
        def get(self):
            return self._facilities

        def set(self, f):
            self._facilities = f
        return get, set
    facilities = property(*facilities())

    def make_filter(self, name, args):
        if args:
            line = name + ' ' + ' '.join(['%%%d' % (i) for i in range(len(args))])
        else:
            line = name
        parser = ScriptParser(self.facilities)
        pipeline = parser.parse(line)
        if not pipeline:
            raise ScriptError(self.module._app.i18n.get(u'Syntax Error: $name'), failed=name)
        opts = None
        args = map(str, args)
        var_storage = VarStorage(opts, args)
        filter_builder = CommandBuilder(self.facilities, self.module._filter_finder)
        c = pipeline.instantiate(filter_builder)
        c.set_facility(self.facilities)
        c.set_var_storage(var_storage)
        c = CommandExecutor(c, self.module._app, self.facilities)
        return c

    def clone(self):
        return self.__class__(self._facilities.clone(), self.module)

    def build(self, string, opts=None, args=None, transaction=COMMIT, type_check=False, module=None):
        u"""コマンド文字列とコマンドライン引数リストを受け取り、コマンドオブジェクトを構築する。
        """
        proxy = None
        if module is None:
            module = self.module._app._schema_module
        if self.cache_enabled:
            key = string
            proxy = self._cache.get(key)
        if not proxy:
            proxy = self._compile(string)
            if self.cache_enabled:
                self._cache.set(key, proxy)
            if proxy:
                proxy.set_module(module)
        return self._instantiate(proxy, opts, args, transaction, type_check)

    def _instantiate(self, proxy, opts=None, args=None, transaction=COMMIT, type_check=False):
        if proxy is None:
            return None
        builder = CommandBuilder(self.facilities, self.module.finder)
        var_storage = VarStorage(opts, args)
        env = self._facilities['env']
        try:
            c = proxy.instantiate(builder)
        except CommandUsageError as e:
            msg = [e.args[0]]
            msg.append(CommandUsage(e.args[1]).get_usage())
            raise Exception(u'\n'.join(msg))
        c.set_facility(self.facilities)
        c.set_var_storage(var_storage)
        if type_check:
            ti = TypeInferer()
            c.accept(ti)
            if ti.is_error:
                util.cout.writeln(ti.message)
        c = CommandExecutor(c, self.module._app, self._facilities)
        if transaction == COMMIT:
            return TransactionAdaptor(c, self.facilities)
        elif transaction == ROLLBACK:
            return TransactionDiscardAdaptor(c, self.facilities)
        elif transaction == PEND:
            return TransactionPendingAdaptor(c, self.facilities)
        elif transaction == None:
            return c
        else:
            raise Exception(self.module._app.i18n.get(u'Invalid transaction mode: $mode', mode=str(transaction)))

    def _compile(self, string):
        raise NotImplementedError
 
    def has_command(self, pkg, name):
        if pkg == 'builtin':
            return name in self.module.finder
        else:
            return pkg + ':' + name in self.module.finder

    def get_help(self, pkg, name):
        if pkg == 'builtin':
            p = self.module.finder[name]
        else:
            p = self.module.finder[pkg + ':' + name]
        return CommandUsage(p).get_usage()

    def get_modules(self):
        return self.module._registrar.get_modules()

    def get_commands(self, name):
        import types
        if name == 'builtin':
            for k, v in self.module.finder.items():
                c = v.get_command_class()
                if isinstance(c, types.TypeType) and issubclass(c, Syntax):
                    continue
                yield v
        elif name == 'public':
            for k, v in self.module.finder.items():
                c = v.get_command_class()
                if isinstance(c, types.TypeType) and issubclass(c, Syntax):
                    continue
                if v.module.name == name:
                    yield v
        else:
            subm = self.module.sub_modules.get(name)
            for k, v in subm.command_ns.items():
                yield v

class ShellCommandCompiler(AbstractCommandCompiler):
    def _compile(self, string):
        u"""コマンド文字列を受け取り、中間形式のパイプラインを構築する。
        対話シェルから使われることを想定しているので、入力途中で改行されたりなど
        パイプラインが構築し切れていない場合は以前の状態を保存し、
        継続行の入力も受け付けるものとする。
        """
        from topdown import ParseFailed
        string = self.prev_string + '\n' + string if self.prev_string else string
        parser = ScriptParser(self.facilities)
        try:
            pipeline = parser.parse(string)
            if self._ends_with_empty(pipeline):
                self.prev_string = string
                return None
        except NothingTodo:
            self.prev_string = u''
            raise
        except ParseFailed, e:
            self.prev_string = u''
            raise ScriptError(self.module._app.i18n.get(u'Syntax Error: $failed', failed=error_to_ustr(e)))
        if not pipeline:
            self.prev_string = string
            return None
        else:
            self.prev_string = u''
            return pipeline

    def update_facility(self, facilities):
        self.facilities = facilities

    def _ends_with_empty(self, pipeline):
        from caty.core.script.proxy import EmptyProxy as Empty
        from caty.core.script.proxy import CombinatorProxy as Combinator
        from caty.core.script.proxy import DiscardProxy as Discard
        if isinstance(pipeline, Combinator):
            return self._ends_with_empty(pipeline.b)
        elif isinstance(pipeline, Discard):
            return self._ends_with_empty(pipeline.target)
        elif isinstance(pipeline, Empty):
            return True
        return False

class ScriptCommandCompiler(AbstractCommandCompiler):
    def _compile(self, string):
        u"""コマンド文字列を受け取り、中間形式のパイプラインを構築する。
        呼び出し可能な状態のオブジェクトが構築できなかった場合、即座にエラーとする。
        """
        parser = ScriptParser(self.facilities)
        pipeline = parser.parse(string)
        if not pipeline:
            raise ScriptError(self.module._app.i18n.get(u'Syntax Error: $name', name=string))
        else:
            return pipeline

def apply_builder(builder, cmd):
    u"""print コマンドは内部的にアソシエーションを解決する必要があるので、
    実行前に builder （実体は CommandCompiler）を注入する。
    初期化時に行わないのは、オブジェクトの deepcopy 処理での不具合を回避するため。
    """
    if isinstance(cmd, (builtin.Print, builtin.Expand)):
        cmd.builder = builder
    elif isinstance(cmd, CommandCombinator):
        apply_builder(builder, cmd.bf)
        apply_builder(builder, cmd.af)
    return cmd


