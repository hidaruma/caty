# coding:utf-8
from caty.core.casm.module import FilterModule
from caty.core.casm.finder import CommandFinder
from caty.core.facility import (FakeFacility, 
                                TransactionAdaptor, 
                                TransactionDiscardAdaptor, 
                                TransactionPendingAdaptor,
                                COMMIT,
                                ROLLBACK,
                                PEND)
from caty.core.script.parser import ScriptParser, NothingTodo
from caty.core.script.builder import CommandBuilder, CommandCombinator
from caty.core.script import node
from caty.core.std.command import builtin
from caty.core.command import Builtin, Syntax, Command, VarStorage, PipelineInterruption, PipelineErrorExit, ScriptError
from caty.util.cache import memoize, Cache
from caty.util import error_to_ustr
import types

def initialize(registrar, app, system):
    return ScriptModule(registrar, app, system)

class ScriptModule(object):
    def __init__(self, registrar, app, system):
        #namespace = {}
        filters = FilterModule(system)
        for n, profile_container in registrar.command_profiles:
            try:
                cmd = profile_container.get_command_class()
                cmd.profile_container = profile_container
                #namespace[n] = cmd
                if 'filter' in cmd.profile_container.get_annotations():
                    filters.command_ns[n.split(':')[-1]] = profile_container
            except Exception, e:
                raise
        self._finder = registrar.command_finder#CommandFinder(namespace, app, system)
        self._filter_finder = CommandFinder(filters, app, system)
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
        return ShellCommandInterpreter(facilities, self)

    def file_mode(self, facilities):
        return ScriptCommandInterpreter(facilities, self)

class AbstractCommandInterpreter(FakeFacility):
    u"""コマンド文字列からコマンドを構築するためのオブジェクト。
    実際の処理は CommandBuilder や parse_command に移譲し、
    このクラスでは対話シェルからの入力の受付や前二者の紐付けなどを行う。
    """
    def __init__(self, facilities, module):
        self.builder = CommandBuilder(facilities, module.finder)
        self.filter_builder = CommandBuilder(facilities, module._filter_finder)
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
            self.builder = CommandBuilder(self._facilities, self._finder)
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
        c = pipeline.instantiate(self.filter_builder)
        c.set_facility(self.facilities)
        c.set_var_storage(var_storage)
        return c

    def clone(self):
        return self.__class__(self._facilities.clone(), self.module)

    def build(self, string, opts=None, args=None, transaction=COMMIT):
        u"""コマンド文字列とコマンドライン引数リストを受け取り、コマンドオブジェクトを構築する。
        """
        proxy = None
        if self.cache_enabled:
            key = string
            proxy = self._cache.get(key)
        if not proxy:
            proxy = self._compile(string)
            if self.cache_enabled:
                self._cache.set(key, proxy)
        return self._instantiate(proxy, opts, args, transaction)

    def _instantiate(self, proxy, opts=None, args=None, transaction=COMMIT):
        if proxy is None:
            return None
        var_storage = VarStorage(opts, args)
        env = self._facilities['env']
        for k, v in env.items():
            var_storage.opts[k] = v
        c = proxy.instantiate(self.builder)
        c.set_facility(self.facilities)
        c.set_var_storage(var_storage)
        if transaction == COMMIT:
            return TransactionAdaptor(c, self.facilities)
        elif transaction == ROLLBACK:
            return TransactionDiscardAdaptor(c, self.facilities)
        elif transaction == PEND:
            return TransactionPendingAdaptor(c, self.facilities)
        else:
            raise Exception(self.module._app.i18n.get(u'Invalid transaction mode: $mode', mode=str(transaction)))

    def _compile(self, string):
        raise NotImplementedError
 
    def has_command(self, pkg, name):
        if pkg == 'builtin':
            return name in self.builder.namespace
        else:
            return pkg + ':' + name in self.builder.namespace

    def get_help(self, pkg, name):
        if pkg == 'builtin':
            return self.builder.namespace[name].usage
        else:
            return self.builder.namespace[pkg + ':' + name].usage
   
    def get_modules(self):
        return self.module._registrar.get_modules()

    def get_commands(self, name):
        import types
        if name == 'builtin':
            for k, v in self.builder.namespace.items():
                c = v.get_command_class()
                if isinstance(c, types.TypeType) and issubclass(c, Syntax):
                    continue
                yield v
        else:
            subm = self.builder.namespace._module.sub_modules.get(name)
            for k, v in subm.command_ns.items():
                yield v

class ShellCommandInterpreter(AbstractCommandInterpreter):
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
        self.builder.facilities = facilities
        self.facilities = facilities


class ScriptCommandInterpreter(AbstractCommandInterpreter):
    def _compile(self, string):
        u"""コマンド文字列を受け取り、中間形式のパイプラインを構築する。
        呼び出し可能な状態のオブジェクトが構築できなかった場合、即座にエラーとする。
        """
        parser = ScriptParser(self.facilities)
        pipeline = parser.parse(string)
        if not pipeline:
            raise ScriptError(self.module._app.i18n.get(u'Syntax Error: $name'), failed=string)
        else:
            return pipeline

def apply_builder(builder, cmd):
    u"""print コマンドは内部的にアソシエーションを解決する必要があるので、
    実行前に builder （実体は CommandInterpreter）を注入する。
    初期化時に行わないのは、オブジェクトの deepcopy 処理での不具合を回避するため。
    """
    if isinstance(cmd, (builtin.Print, builtin.Expand)):
        cmd.builder = builder
    elif isinstance(cmd, CommandCombinator):
        apply_builder(builder, cmd.bf)
        apply_builder(builder, cmd.af)
    return cmd


