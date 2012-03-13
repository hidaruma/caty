#coding:utf-8
from __future__ import with_statement
from caty.core.casm.finder import SchemaFinder, CommandFinder
from caty.core.casm.loader import CommandLoader, BuiltinLoader
from caty.core.schema import schemata
from caty.core.casm.language.casmparser import iparse, iparse_literate
from caty.core.casm.language import xcasmparser as xcasm
from caty.core.casm.cursor import (SchemaBuilder, 
                                   ReferenceResolver, 
                                   CycleDetecter, 
                                   ProfileBuilder, 
                                   TypeVarApplier, 
                                   TypeNormalizer, 
                                   TreeDumper,
                                   DependencyAnalizer)
from caty.core.casm.plugin import PluginMap
from caty.jsontools.path.validator import to_decl_style
from threading import RLock
from StringIO import StringIO

class Module(object):
    def __init__(self, app):
        self.kind_ns = {}
        self.schema_ns = {}
        self.command_ns = {}
        self.command_loader = None
        self.sub_modules = {}
        self.parent = None
        self._name = u'public' # デフォルト値
        self._app = app
        self._system = app._system
        self._lazy_resolve = []
        self._plugin = PluginMap()
        self._type = u'casm'
        self.ast_ns = {}
        self.proto_ns = {}
        self.saved_st = {}
        self.compiled = False
    
    @property
    def type(self):
        return self._type

    @property
    def application(self):
        return self._app

    @property
    def system(self):
        return self._system

    @property
    def name(self):
        return self._name
 
    def add_ast(self, ref):
        if ref.name in self.ast_ns:
            m, a = self._get_mod_and_app(ref)
            raise Exception(self.application.i18n.get(u'Type $name of $this is already defined in $module of $app', 
                                                      name=ref.name, 
                                                      this=self.name+'.'+self.type,
                                                      module=m,
                                                      app=a))

        if 'register-public' in ref.annotations:
            if not self.is_root:
                self.parent.add_ast(ref)
        self.ast_ns[ref.name] = ref

    def get_ast(self, name, tracked=None):
        if not tracked:
            tracked = set([self])
        else:
            if self in tracked:
                raise KeyError(name)
            else:
                tracked.add(self)
        if name in self.ast_ns:
            return self.ast_ns[name]
        else:
            if ':' in name:
                m, n = name.rsplit(':', 1)
                if m == 'public':
                    return self.get_ast(n)
                if m in self.sub_modules:
                    return self.sub_modules[m].get_ast(n)
        if self.parent:
            return self.parent.get_ast(name)
        raise KeyError(name)

    def add_schema(self, member):
        name = member.name
        annotations = member.annotations
        if name in self.schema_ns:
            t = self.schema_ns[name]
            m, a = self._get_mod_and_app(t)
            raise Exception(self.application.i18n.get(u'Type $name of $this is already defined in $module of $app', 
                                                      name=name, 
                                                      this=self.name+'.'+self.type,
                                                      module=m,
                                                      app=a))
        #if 'register-public' in annotations:
        #    if not self.is_root:
        #        self.parent.add_schema(member)
        member.annotations = annotations
        self.schema_ns[name] = member

    def add_kind(self, name, member, annotations):
        if name in self.kind_ns:
            t = self.kind_ns[name]
            m, a = self._get_mod_and_app(t)
            raise Exception(self.application.i18n.get(u'Kind $name of $this is already defined in $module.casm of $app', 
                                                      name=name, 
                                                      this=self.name+'.'+self.type,
                                                      module=m,
                                                      app=a))
        if 'register-public' in annotations:
            if not self.is_root:
                self.parent.add_schema(name, member, annotations)
        member.annotations = annotations
        self.kind_ns[name] = member

    def add_proto_type(self, proto):
        name = proto.name
        if name in self.proto_ns:
            t = self.proto_ns[name]
            m, a = self._get_mod_and_app(t)
            raise Exception(self.application.i18n.get(u'Command $name of $this is already defined in $module of $app', 
                                                       name=name, 
                                                       this=self.name+'.'+self.type,
                                                       module=m,
                                                       app=a))
        self.proto_ns[name] = proto

    def add_command(self, name, profile):
        if name in self.command_ns:
            t = self.command_ns[name]
            m, a = self._get_mod_and_app(t)
            raise Exception(self.application.i18n.get(u'Command $name of $this is already defined in $module of $app', 
                                                       name=name, 
                                                       this=self.name+'.'+self.type,
                                                       module=m,
                                                       app=a))
        if 'register-public' in profile.annotations:
            if not self.is_root:
                self.parent.add_command(name, profile)
        if 'filter' in profile.annotations:
            if self.name != 'filter':
                fm = self.get_module('filter')
                fm.add_command(name, profile)
        self.command_ns[name] = profile

    def _get_mod_and_app(self, t):
        a = t.module.application.name
        if a != 'builtin':
            m = t.module.name + t.module.type
        else:
            m = t.module.name + '.py'
        return m, a

    def has_ast(self, name, tracked=()):
        if self in tracked:
            return False
        t = list(tracked ) + [self]
        if name in self.ast_ns:
            return True
        else:
            if ':' in name:
                m, n = name.rsplit(':', 1)
                if m == 'public':
                    return self.has_ast(n)
                if m in self.sub_modules and self.sub_modules[m].has_ast(n, t):
                    return True
            if self.parent:
                return self.parent.has_ast(name, t)
            else:
                return False

    def has_schema(self, name, tracked=()):
        if self in tracked:
            return False
        t = list(tracked ) + [self]
        if name in self.schema_ns:
            return True
        else:
            if ':' in name:
                m, n = name.split(':', 1)
                if ':' in n:
                    if m == 'this' or m == 'global' or m == 'caty':
                        m, n = n.split(':', 1)
                    else:
                        throw_caty_exception('RUNTIME_ERROR', u'To call another application\'s command is forbidden')
                if m == 'public':
                    return self.has_schema(n)
                if m == self.name:
                    return self.has_schema(n)
                if m in self.sub_modules and self.sub_modules[m].has_schema(n, t):
                    return True
            if self.parent:
                return self.parent.has_schema(name, t)
            else:
                return False

    def has_command(self, name, tracked=()):
        if self in tracked:
            return False
        t = list(tracked ) + [self]
        if name in self.command_ns:
            return True
        else:
            if ':' in name:
                m, n = name.split(':', 1)
                if ':' in n:
                    if m == 'this' or m == 'global' or m == 'caty':
                        m, n = n.split(':', 1)
                    else:
                        throw_caty_exception('RUNTIME_ERROR', u'To call another application\'s command is forbidden')
                if m == 'public' and self.name != 'public':
                    return self.parent.has_command(n)
                if m == self.name:
                    return self.has_command(n)
                if m in self.sub_modules and self.sub_modules[m].has_command(n, t):
                    return True
            if self.parent:
                return self.parent.has_command(name, t)
            else:
                return False

    def has_kind(self, name, tracked=()):
        if self in tracked:
            return False
        t = list(tracked ) + [self]
        if name in self.kind_ns:
            return True
        else:
            if ':' in name:
                m, n = name.rsplit(':', 1)
                if m == 'public':
                    return self.has_kind(n)
                if m == self.name:
                    return self.has_kind(n)
                if m in self.sub_modules and self.sub_modules[m].has_kind(n, t):
                    return True
            if self.parent:
                return self.parent.has_kind(name, t)
            else:
                return False

    def get_schema(self, name, check_queue=None):
        if not self.has_schema(name):
            raise KeyError(name)
        if name in self.schema_ns:
            r = self.schema_ns[name]
            return r
        else:
            if ':' in name:
                m, n = name.split(':', 1)
                if ':' in n:
                    if m == 'this' or m == 'global' or m == 'caty':
                        m, n = n.split(':', 1)
                    else:
                        throw_caty_exception('RUNTIME_ERROR', u'To call another application\'s command is forbidden')
                if m == 'public':
                    return self.get_schema(n)
                if m == self.name:
                    return self.get_schema(n)
                if m in self.sub_modules:
                    return self.sub_modules[m].get_schema(n)
        return self.parent.get_schema(name)

    def get_command_type(self, name):
        if not self.has_command(name):
            raise KeyError(name)
        if name in self.command_ns:
            return self.command_ns[name]
        else:
            if ':' in name:
                m, n = name.split(':', 1)
                if ':' in n:
                    if m == 'this' or m == 'global' or m == 'caty':
                        m, n = n.split(':', 1)
                    else:
                        throw_caty_exception('RUNTIME_ERROR', u'To call another application\'s command is forbidden')
                if m == 'public' and self.name != 'public':
                    return self.parent.get_command_type(n)
                if m == self.name:
                    return self.get_command_type(n)
                if m in self.sub_modules:
                    return self.sub_modules[m].get_command_type(n)
        return self.parent.get_command_type(name)

    def get_kind(self, name):
        if not self.has_kind(name):
            raise KeyError(name)
        if name in self.kind_ns:
            return self.kind_ns[name]
        else:
            if ':' in name:
                m, n = name.rsplit(':', 1)
                if m == 'public':
                    return self.get_kind(n)
                if m == self.name:
                    return self.get_kind(n)
                if m in self.sub_modules:
                    return self.sub_modules[m].get_kind(n)
        return self.parent.get_kind(name)

    @property
    def command_profiles(self):
        for k, v in self.command_ns.iteritems():
            yield k, v
        for k, m in self.sub_modules.iteritems():
            for a, b in m.command_profiles:
                if k == 'public':
                    yield a, b
                else:
                    yield k + ':' + a, b

    @property
    def schema_finder(self):
        return SchemaFinder(self, self._app, self._system)

    @property
    def command_finder(self):
        return CommandFinder(self, self._app, self._system)

    def get_plugin(self, name):
        return self._plugin.get_plugin(name)

    def get_module(self, name, tracked=None):
        tracked = set() if tracked is None else tracked
        if self.name in tracked: return
        if name == self.name:
            return self
        else:
            tracked.add(self.name)
            for m in self.sub_modules.values():
                r = m.get_module(name, tracked)
                if r:
                    return r
        if self.parent:
            return self.parent.get_module(name, tracked)
        return None

    def get_modules(self):
        yield self
        for m in self.sub_modules.values():
            for r in m.get_modules():
                yield m

    def add_sub_module(self, module):
        if module.name in self.sub_modules:
            raise Exception(self.application.i18n.get(u'Can not register $name.$type1. $name.$type2 is already defined in $app', 
                                                      name=module.name, 
                                                      type1=module.type,
                                                      app=self._app.name,
                                                      type2=self.sub_modules[module.name].type))
        module.parent = self
        self.sub_modules[module.name] = module

    def resolve(self):
        u"""型参照の解決
        """
        self._build_schema_tree()
        self._resolve_reference()
        self._check_dependency()
        self._detect_cycle()
        self._apply_type_var()
        self._normalize()
        self._register_command()
        self.compiled = True
        for m in self.sub_modules.values():
            m.compiled = True

    def make_schema_builder(self):
        return SchemaBuilder(self)

    def make_reference_resolver(self):
        return ReferenceResolver(self)

    def make_typevar_applier(self):
        return TypeVarApplier(self)

    def make_cycle_detecter(self):
        return CycleDetecter(self)

    def make_type_normalizer(self):
        return TypeNormalizer(self)

    def make_dumper(self):
        return TreeDumper()

    def _build_schema_tree(self):
        self.saved_st.update(self.ast_ns)
        if not self.compiled:
            self._loop_exec(self.ast_ns, self.make_schema_builder(), lambda k, v:self.add_schema(v))
        for m in self.sub_modules.values():
            m._build_schema_tree()

    def _resolve_reference(self):
        if not self.compiled:
            self._loop_exec(self.schema_ns, self.make_reference_resolver(), lambda k, v:self.schema_ns.__setitem__(k, v))
        for m in self.sub_modules.values():
            m._resolve_reference()

    def _apply_type_var(self):
        if not self.compiled:
            self._loop_exec(self.schema_ns, self.make_typevar_applier(), lambda k, v:self.schema_ns.__setitem__(k, v))
        for m in self.sub_modules.values():
            m._apply_type_var()

    def _detect_cycle(self):
        if not self.compiled:
            self._loop_exec(self.schema_ns, self.make_cycle_detecter(), lambda k, v: v)
        for m in self.sub_modules.values():
            m._detect_cycle()

    def _normalize(self):
        if not self.compiled:
            self._loop_exec(self.schema_ns, self.make_type_normalizer(), lambda k, v:self.schema_ns.__setitem__(k, v))
        for m in self.sub_modules.values():
            m._normalize()

    def _check_dependency(self):
        if not self.compiled:
            graph = set()
            self._loop_exec(self.schema_ns, DependencyAnalizer(self), lambda k, v: graph.update(v) if v else v)
            for a, b in graph:
                if (b, a) in graph:
                    raise Exception(self.application.i18n.get(u'The cyclic dependency between $mod1 and $mod2 was detected', mod1=a.name, mod2=b.name))
        for m in self.sub_modules.values():
            m._check_dependency()
    
    def _register_command(self):
        if not self.compiled:
            self._loop_exec(self.proto_ns, ProfileBuilder(self), lambda k, v:self.add_command(k, v))
        for m in self.sub_modules.values():
            m._register_command()

    def _loop_exec(self, target, cursor, callback):
        try:
            for k, v in target.items():
                try:
                    callback(k, cursor.visit(v))
                except:
                    print '[DEBUG]', k
                    raise

        except:
            print '[ERROR]', u'Application:%s, module:%s' % (self._app.name, self._name)
            raise


    def has_syntax_tree(self, name, tracked=[]):
        if self in tracked:
            return False
        t = list(tracked ) + [self]
        if name in self.saved_st:
            return True
        else:
            if ':' in name:
                m, n = name.rsplit(':', 1)
                if m == 'public':
                    return self.has_syntax_tree(n)
                if m in self.sub_modules and self.sub_modules[m].has_syntax_tree(n, t):
                    return True
            if self.parent:
                return self.parent.has_syntax_tree(name, t)
            else:
                return False

    def get_syntax_tree(self, name):
        if not self.has_syntax_tree(name):
            raise KeyError(name)
        if name in self.saved_st:
            r = self.saved_st[name]
            return r
        else:
            if ':' in name:
                m, n = name.rsplit(':', 1)
                if m == 'public':
                    return self.get_syntax_tree(n)
                if m in self.sub_modules:
                    return self.sub_modules[m].get_syntax_tree(n)
        return self.parent.get_syntax_tree(name)

class CoreModule(Module):
    u"""Caty付属のモジュール。
    コマンドクラスはすべてライブラリのサーチパス上にあり、
    スキーマはそれらの.pyファイルのdocstringなどから取得される。
    """
    def __init__(self, app, parent, is_root=False):
        Module.__init__(self, app)
        self.schema_ns = {}
        self.schema_ns.update(schemata)
        self.command_loader = BuiltinLoader()
        self.parent = parent
        self.is_root= is_root
        self.is_builtin = True
        self.filepath = u''
        self.compiled = False

    def compile(self, schema_string, module):
        if self.is_root:
            if module is None:
                self._name = 'builtin'
                for t in iparse(schema_string):
                    t.declare(self)
            else:
                mod = self.__class__(self._app, self)
                mod.compile(schema_string, module)
                self.sub_modules[mod.name] = mod
        else:
            self._name = module.name
            for t in iparse(schema_string):
                t.declare(self)

class AppModule(Module):
    def __init__(self, app, parent, core=None, global_module=None, is_root=False):
        Module.__init__(self, app)
        self.fs = app._schema_fs
        self.pcasm_cache = None
        self.parser_cache = None
        self.command_loader = CommandLoader(app._command_fs, global_module.command_loader if global_module else None)
        self.parent = parent
        self.is_root= is_root
        self.is_builtin = False
        self._plugin.set_fs(app._command_fs)
        self._core = core
        self._global_module = global_module
        if self.is_root:
            if self._core:
                core = self._core
                for k, v in core.schema_ns.items():
                    self.schema_ns[k] = v
                for k, v in core.sub_modules.items():
                    self.sub_modules[k] = v
                for k, v in core.saved_st.items():
                    self.saved_st[k] = v
                for k, v in core.command_ns.items():
                    self.command_ns[k] = v
            if self._global_module:
                global_module = self._global_module
                for k, v in global_module.schema_ns.items():
                    self.schema_ns[k] = v
                for k, v in global_module.sub_modules.items():
                    self.sub_modules[k] = v
                for k, v in global_module.saved_st.items():
                    self.saved_st[k] = v
                for k, v in global_module.command_ns.items():
                    self.command_ns[k] = v

    def _path_to_module(self, path):
        p = path[1:].rsplit('.')[0]
        return p.replace('/', '.')

    def _module_to_path(self, modname):
        m = modname.rsplit('.', 1)[0]
        return '/' + m.replace('.', '/')

    def compile(self):
        for e in self.find(self.fs.DirectoryObject('/')):
            if self.is_root and e.path == u'/public.casm':
                self.filepath = e.path
                self._compile(e.path)
            elif e.path.endswith(u'.casm') or e.path.endswith(u'.pcasm') or e.path.endswith(u'.casm.lit'):
                mod = self.__class__(self._app, self)
                mod.filepath = e.path
                if e.path.endswith(u'.casm.lit'):
                    mod._type = 'casm.lit'
                mod._name = self._path_to_module(mod.filepath)
                if mod._name in self.sub_modules:
                    raise Exception(self._app.i18n.get(u'Module $name is already defined', 
                                               name=mod._name))
                mod._compile(e.path)
                self.sub_modules[mod.name] = mod
            elif e.path == u'/formats.xjson':
                o = self.fs.open(e.path)
                self._plugin.feed(o.read())


    def _compile(self, path):
        o = self.fs.open(path)
        if path.endswith('.casm'):
            for t in self.find_or_create_cache(o):
                t.declare(self)
        elif path.endswith('.pcasm'):
            d = to_decl_style(o)
            if self.pcasm_cache:
                io = self.pcasm_cache
            else:
                io = StringIO(d)
                io.path = o.path
                self.pcasm_cache = io
            for t in self.find_or_create_cache(io):
                t.declare(self)
        elif path.endswith('.xcasm'):
            for t in self.find_or_create_cache(o, 'xcasm'):
                t.declare(self)
        else:
            for t in self.find_or_create_cache(o, 'lit'):
                t.declare(self)

    def find_or_create_cache(self, fo, type='casm'):
        if not self.parser_cache:
            if type == 'casm':
                try:
                    self._show_msg(fo)
                    self._app.cout.write(u'...')
                    self.parser_cache = iparse(fo.read())
                    self._app.cout.writeln(u'OK')
                except:
                    self._app.cout.writeln(u'NG')
                    raise
            elif type == 'xcasm':
                self.parser_cache = xcasm.iparse(fo.read())
            elif type == 'lit':
                try:
                    self._show_msg(fo)
                    self._app.cout.write(u'...')
                    self.parser_cache = iparse_literate(fo.read())
                    self._app.cout.writeln(u'OK')
                except:
                    self._app.cout.writeln(u'NG')
                    raise
        return self.parser_cache

    def find(self, do):
        for e in do.read():
            if not e.is_dir:
                yield e
            else:
                for se in self.find(e):
                    yield se

    def _show_msg(self, fo, error=False):
        msg = self._app.i18n.get('Schema: $path', path=fo.path.strip('/'))
        self._app.cout.write(u'  * ' + msg)

    def to_name_tree(self):
        c = {}
        for k, v in self.schema_ns.items():
            if self.__in_core_or_global_schema(k):
                continue
            c[k] = {
                u'kind': u'i:type',
                u'id': unicode(str(id(v))),
                u'childNodes': {}
            }
        for k, v in self.command_ns.items():
            if self.__in_core_or_global_command(k):
                continue
            if '.' not in k:
                c[k] = {
                    u'kind': u'i:cmd',
                    u'id': unicode(str(id(v))),
                    u'childNodes': {}
                }
        for k, v in self.sub_modules.items():
            if v._type not in ('cara', 'cara.lit') and not self.__in_core_or_global_module(k):
                if '.' not in k:
                    c[k] = v.to_name_tree()
                else:
                    c[k] = {
                        u'kind': u'ns:pkg',
                        u'id': unicode(str(id(v))),
                        u'childNodes': {
                            k.rsplit('.', 1)[-1]: v.to_name_tree()
                        }
                    }
        return {
            u'kind': u'c:mod',
            u'id': unicode(str(id(self))),
            u'childNodes': c
        }

    def __in_core_or_global_schema(self, k):
        if self._core:
            if k in self._core.schema_ns:
                return True
        if self._global_module:
            if k in self._global_module.schema_ns:
                return True
        return False

    def __in_core_or_global_command(self, k):
        if self._core:
            if k in self._core.command_ns:
                return True
        if self._global_module:
            if k in self._global_module.command_ns:
                return True
        return False

    def __in_core_or_global_module(self, k):
        if self._core:
            if k in self._core.sub_modules:
                return True
        if self._global_module:
            if k in self._global_module.sub_modules:
                return True
        return False

class FilterModule(Module):
    def __init__(self, system):
        filterapp = system.dummy_app
        filterapp._name = u'filter'
        Module.__init__(self, filterapp)

class IntegratedModule(object):
    u"""標準モジュールとユーザ定義モジュールの複合モジュール
    """
    def __init__(self, system):
        coreapp = system.dummy_app
        coreapp._name = u'builtin'
        self._core = CoreModule(coreapp, None, True)
        self._system = system
        self._global = None

    def set_global(self, global_app):
        if global_app:
            self._global = global_app._schema_module
        else:
            self._global = None

    def compile(self, *args):
        self._core.compile(*args)
        self._core.resolve()
    
    def make_blank_module(self, app):
        app_module = AppModule(app, None, self._core, self._global, True)
        return app_module

    def make_app_module(self, app):
        app_module = AppModule(app, None, self._core, self._global, True)
        app_module.compile()
        return app_module



