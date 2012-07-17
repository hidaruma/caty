#coding:utf-8
from __future__ import with_statement
from caty.core.casm.loader import CommandLoader, BuiltinLoader
from caty.core.language import split_colon_dot_path
from caty.core.schema import schemata
from caty.core.schema.base import Annotations
from caty.core.casm.language.casmparser import parse, parse_literate
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
from caty.core.exception import throw_caty_exception, CatyException, SystemResourceNotFound
from threading import RLock
from StringIO import StringIO
from caty.core.facility import Facility
from functools import partial

class Module(Facility):
    is_package = False
    def __init__(self, app, parent=None):
        self._app = app
        self.kind_ns = {}
        self.schema_ns = {}
        self.command_ns = {}
        self.class_ns = {}
        self.facility_ns = {}
        self.command_loader = None
        self.sub_modules = {}
        self.sub_packages = {}
        self.parent = parent
        self._name = u'public' # デフォルト値
        self._system = app._system
        self._lazy_resolve = []
        self._plugin = PluginMap()
        self._type = u'casm'
        self.ast_ns = {}
        self.kind_ns = {}
        self.proto_ns = {}
        self.saved_st = {}
        self.const_ns = {}
        self.compiled = False
        self.docstring = u'undocumented'
        self.last_modified = 0
        self.annotations = Annotations([])
        self.package_root_path = u'/'

        self.add_schema = partial(self._add_resource, scope_func=lambda x:x.schema_ns, type=u'Type')
        self.get_type = partial(self._get_resource, scope_func=lambda x:x.schema_ns, type=u'Type')
        self.has_schema = partial(self._has_resource, scope_func=lambda x:x.schema_ns, type=u'Type')

        self.add_kind = partial(self._add_resource, scope_func=lambda x:x.kind_ns, type=u'Kind', see_register_public=True)
        self.get_kind = partial(self._get_resource, scope_func=lambda x:x.kind_ns, type=u'Kind')
        self.has_kind = partial(self._has_resource, scope_func=lambda x:x.kind_ns, type=u'Kind')

        self.add_command = partial(self._add_resource, scope_func=lambda x:x.command_ns, type=u'Command', see_register_public=True, see_filter=True)
        self.get_command = partial(self._get_resource, scope_func=lambda x:x.command_ns, type=u'Command')
        self.has_command_type = partial(self._has_resource, scope_func=lambda x:x.command_ns, type=u'Command')
        
        self.add_proto_type = partial(self._add_resource, scope_func=lambda x:x.proto_ns, type=u'Command')
        self.get_proto_type = partial(self._get_resource, scope_func=lambda x:x.proto_ns, type=u'Command')
        self.has_proto_type = partial(self._has_resource, scope_func=lambda x:x.proto_ns, type=u'Command')
        
        self.add_ast = partial(self._add_resource, scope_func=lambda x:x.ast_ns, type=u'Type', see_register_public=True)
        self.get_ast = partial(self._get_resource, scope_func=lambda x:x.ast_ns, type=u'Type')
        self.has_ast = partial(self._has_resource, scope_func=lambda x:x.ast_ns, type=u'Type')
        
        self.get_syntax_tree = partial(self._get_resource, scope_func=lambda x:x.saved_st, type=u'Type')
        self.has_syntax_tree = partial(self._has_resource, scope_func=lambda x:x.saved_st, type=u'Type')
        
        self.add_class = partial(self._add_resource, scope_func=lambda x:x.class_ns, type=u'Class', see_register_public=True, callback=lambda target: ClassModule(self._app, self, target))
        self.get_class = partial(self._get_resource, scope_func=lambda x:x.class_ns, type=u'Class')
        self.has_class = partial(self._has_resource, scope_func=lambda x:x.class_ns, type=u'Class')
 
        self.add_facility = partial(self._add_resource, scope_func=lambda x:x.facility_ns, type=u'Facility')
        self.get_facility = partial(self._get_resource, scope_func=lambda x:x.facility_ns, type=u'Facility')
        self.has_facility = partial(self._has_resource, scope_func=lambda x:x.facility_ns, type=u'Facility')

    @property
    def type(self):
        return self._type

    @property
    def system(self):
        return self._system

    @property
    def name(self):
        return self._name
 
    def _get_full_name(self):
        return self.name+'.'+self.type

    def _get_mod_and_app(self, t):
        a = t.module.application.name
        m = t.module.name + '.' + t.module.type
        return m, a

    def _add_resource(self, target, scope_func=None, type=u'', see_register_public=False, see_filter=False, callback=None):
        scope = scope_func(self)
        name = target.name
        if name in scope:
            t = scope[name]
            m, a = self._get_mod_and_app(t)
            raise Exception(self.application.i18n.get(u'%s $name of $this is already defined in $module of $app' % type, 
                                                       name=name, 
                                                       this=self._get_full_name(),
                                                       module=m,
                                                       app=a))
        if see_register_public and ('register-public' in target.annotations or 'register-public' in self.annotations):
            if not self.is_root:
                self.parent._add_resource(target, scope_func, type, see_register_public=False, see_filter=False, callback=callback)
        if see_filter and 'filter' in target.annotations:
            if self.name != 'filter':
                fm = self.get_module('filter')
                fm._add_resource(target, scope_func, type, see_register_public=False, see_filter=False)
        if not callback:
            scope[name] = target
        else:
            scope[name] = callback(target)

    def _get_resource(self, rname, tracked=(), scope_func=None, type=u''):
        if self in tracked:
            raise SystemResourceNotFound(u'%sNotFound'%type, u'$name', name=rname)
        scope = scope_func(self)
        app_name, mod_name, name = split_colon_dot_path(rname)
        if app_name:
            if app_name in ('this', 'global', 'caty', self._app.name):
                pass
            else:
                return self._another_app_callback(rname, tracked, scope_func, type)
        if mod_name:
            if mod_name == self.name:
                return self._get_resource(name, tracked, scope_func, type)
            mod = self.get_module(mod_name)
            return mod._get_resource(name, tracked, scope_func, type)
        if '.' in name:
            c, n = name.split('.', 1)
            if c == self.name:
                return self._get_resource(n, tracked, scope_func, type)
            if c in self.class_ns:
                return self.class_ns[c]._get_resource(n, tracked, scope_func, type)
            tracked = list(tracked) + [self]
            if self.parent:
                return self.parent._get_resource(name, tracked, scope_func, type)
            raise SystemResourceNotFound(u'ClassNotFound', u'$name', name=c)
        if name in scope:
            return scope[name]
        else:
            if self.parent:
                return self.parent._get_resource(rname, tracked, scope_func, type)
        raise SystemResourceNotFound(u'%sNotFound' % type, u'$name', name=rname)

    def _has_resource(self, name, tracked=(), scope_func=None, type=u''):
        try:
            o = self._get_resource(name, tracked, scope_func, type)
        except CatyException as e:
            return False
        return True

    def _another_app_callback(self, rname, tracked=(), scope_func=None, type=u''):
        throw_caty_exception('RUNTIME_ERROR', u'To call another application\'s %s is forbidden at compile-time' % type)

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
        return LocalModule(self)

    @property
    def canonical_name(self):
        if self.parent.is_package:
            return self.parent.canonical_name + '.' + self.name
        else:
            return self.name

    def get_plugin(self, name):
        return self._plugin.get_plugin(name)

    def has_module(self, name, tracked=None):
        tracked = set() if tracked is None else tracked
        assert self not in tracked
        if name == self.name:
            return self
        tracked.add(self)
        if '.' in name:
            pkg, rest = name.rsplit('.', 1)
            return self.get_package(pkg).has_module(rest, tracked)
        for m in self.sub_modules.values():
            if m.name == name:
                return True
        if self.parent:
            return self.parent.has_module(name, tracked)
        return False

    def get_module(self, name, tracked=None):
        tracked = set() if tracked is None else tracked
        assert self not in tracked
        if name == self.name:
            return self
        tracked.add(self)
        if '.' in name:
            pkg, rest = name.rsplit('.', 1)
            return self.get_package(pkg).get_module(rest, tracked)
        for m in self.sub_modules.values():
            if m.name == name:
                return m
        if self.parent:
            return self.parent.get_module(name, tracked)
        raise SystemResourceNotFound(u'ModuleNotFound', u'$name', name=name)

    def has_package(self, name, tracked=None):
        tracked = set() if tracked is None else tracked
        assert self not in tracked
        tracked.add(self)
        if '.' in name:
            pkg, rest = name.rsplit('.', 1)
        else:
            pkg = name
            rest = None
        for p in self.sub_packages.values():
            if p.name == pkg:
                if rest:
                    return p.has_package(rest, tracked)
                else:
                    return True
        if self.parent:
            self.parent.has_package(name, tracked)
        return False

    def get_package(self, name, tracked):
        tracked = set() if tracked is None else tracked
        assert self not in tracked
        tracked.add(self)
        if '.' in name:
            pkg, rest = name.rsplit('.', 1)
        else:
            pkg = name
            rest = None
        for p in self.sub_packages.values():
            if p.name == pkg:
                if rest:
                    return p.get_package(rest)
                else:
                    return p
        if self.parent:
            self.parent.get_package(name)
        raise SystemResourceNotFound(u'PackageNotFound', u'$name', name=name)

    def get_modules(self):
        yield self
        for m in self.sub_modules.values():
            for r in m.get_modules():
                yield m

    def add_sub_module(self, module):
        if self.has_module(module.name):
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
        self._register_facility()
        self.compiled = True
        for m in self.sub_modules.values() + self.class_ns.values():
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
        for m in self.sub_modules.values() + self.class_ns.values():
            m._build_schema_tree()

    def _resolve_reference(self):
        if not self.compiled:
            self._loop_exec(self.schema_ns, self.make_reference_resolver(), lambda k, v:self.schema_ns.__setitem__(k, v))
        for m in self.sub_modules.values() + self.class_ns.values():
            m._resolve_reference()

    def _apply_type_var(self):
        if not self.compiled:
            self._loop_exec(self.schema_ns, self.make_typevar_applier(), lambda k, v:self.schema_ns.__setitem__(k, v))
        for m in self.sub_modules.values() + self.class_ns.values():
            m._apply_type_var()

    def _detect_cycle(self):
        if not self.compiled:
            self._loop_exec(self.schema_ns, self.make_cycle_detecter(), lambda k, v: v)
        for m in self.sub_modules.values() + self.class_ns.values():
            m._detect_cycle()

    def _normalize(self):
        if not self.compiled:
            self._loop_exec(self.schema_ns, self.make_type_normalizer(), lambda k, v:self.schema_ns.__setitem__(k, v))
        for m in self.sub_modules.values() + self.class_ns.values():
            m._normalize()

    def _check_dependency(self):
        if not self.compiled:
            graph = set()
            self._loop_exec(self.schema_ns, DependencyAnalizer(self), lambda k, v: graph.update(v) if v else v)
            for a, b in graph:
                if (b, a) in graph:
                    raise Exception(self.application.i18n.get(u'The cyclic dependency between $mod1 and $mod2 was detected', mod1=a.name, mod2=b.name))
        for m in self.sub_modules.values() + self.class_ns.values():
            m._check_dependency()
    
    def _register_command(self):
        if not self.compiled:
            self._loop_exec(self.proto_ns, ProfileBuilder(self), lambda k, v:self.add_command(v))
        for m in self.class_ns.values() + self.sub_modules.values():
            m._register_command()

    def _register_facility(self):
        if not self.compiled:
            for k, v in self.facility_ns.items():
                cls = self.get_class(v.clsname)
                if u'facility-spec-for' not in cls.annotations:
                    raise Exception(self.application.i18n.get(u'Facility class is not specified: $name, $mod', name=v.clsname, mod=self.name))

                facilty_class = self._load_facility_class(k, cls.annotations['facility-spec-for'].value)
                self._app.register_facility(k, facilty_class, v.system_param)
        for m in self.sub_modules.values():
            m._register_facility()

    def _load_facility_class(self, name, uri):
        from caty.core.casm.loader import dynamic_load
        if not uri.startswith(u'python:'):
            raise Exception(self.application.i18n.get(u'Invalid reference: $ref, $name, $mod', ref=uri, name=name, mod=self.name))
        uri = uri.replace('python:', '')
        loader = _FaciltyLoader(uri, name, self)
        return loader.load()

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

    def reify(self):
        import caty.jsontools as json
        from caty.core.script.proxy import EnvelopeProxy
        o = {'name': self.name, 'document': self.doc_object, 'types': {}, 'commands': {}}
        o['classes'] = {}
        for k, v in self.class_ns.items():
            o['classes'][k] = v.reify()
        for k, v in self.ast_ns.items():
            if '__const' in v.annotations:
                o['types'][k] = self.const_ns[k].reify()
            else:
                o['types'][k] = v.reify()
        for k, v in self.proto_ns.items():
            if '__const' in v.annotation:
                continue
            o['commands'][k] = v.reify()
        return json.tagged(u'casm', o)

    @property
    def doc_object(self):
        from caty.core.language.util import make_structured_doc
        return make_structured_doc(self.docstring or u'undocumented')

    def find_root(self):
        if not self.parent:
            return self
        else:
            return self.parent.find_root()

    def iter_parents(self):
        if self.parent:
            yield self.parent
            for p in self.parent.iter_parents():
                yield p

class _FaciltyLoader(object):
    def __init__(self, clsref, facility_name, module):
        from caty.util.path import join
        self.path = facility_name + '.py'
        self.abspath = join(module._app._physical_path, module.name, self.path)
        self.name = facility_name
        self.modname, self.clsname = clsref.rsplit('.', 1)
        self.code = 'from %s import %s' % (self.modname, self.clsname)

    def load(self):
        import types
        g_dict = {}
        code = self.code
        obj = compile(code, self.path, 'exec')
        g_dict['__file__'] = self.abspath
        exec obj in g_dict
        return g_dict[self.clsname]
        

class ClassModule(Module):
    u"""
    クラスは名前空間を構成するというその機能においてモジュールに近い。
    そのため、実装はモジュールとほぼ同等とする。
    """
    def __init__(self, app, parent, clsobj):
        Module.__init__(self, app, parent)
        self._type = u'class'
        self.command_loader = parent.command_loader
        self._name = clsobj.name
        self._clsobj = clsobj
        self._clsrestriction = clsobj.restriction
        self.annotations = clsobj.annotations
        for m in clsobj.member:
            m.declare(self)
        self.count = 0

    def _get_full_name(self):
        return u'class ' + self.name

    def _get_mod_and_app(self, t):
        a = t.module.application.name
        m = self.parent.name + '.' + t.module.name
        return m, a

    def _build_schema_tree(self):
        Module._build_schema_tree(self)
        b = self.make_schema_builder()
        b._type_params = []
        self._clsrestriction = b.visit(self._clsrestriction)

    def _resolve_reference(self):
        Module._resolve_reference(self)
        self._clsrestriction = self.make_reference_resolver().visit(self._clsrestriction)

    def _normalize(self):
        Module._normalize(self)
        self._clsrestriction = self.make_type_normalizer().visit(self._clsrestriction)

    def _register_command(self):
        Module._register_command(self)
        for v in self.command_ns.values():
            v.set_arg0_type(self._clsrestriction)

    def reify(self):
        import caty.jsontools as json
        r = Module.reify(self)
        t, v = json.split_tag(r)
        if 'classes' in v:
            del v['classes']
        return json.tagged(u'_class', v)

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

    def compile(self, schema_string, name):
        if self.is_root:
            if name is None:
                self._name = u'builtin'
                for t in parse(schema_string):
                    t.declare(self)
            else:
                mod = self.__class__(self._app, self)
                mod.compile(schema_string, name)
                self.sub_modules[mod.name] = mod
        else:
            self._name = name
            for t in parse(schema_string):
                t.declare(self)

class AppModule(Module):
    def __init__(self, app, parent=None, is_root=False):
        Module.__init__(self, app)
        self.fs = app._schema_fs
        self.pcasm_cache = None
        self.parser_cache = None
        self.command_loader = CommandLoader(app._command_fs)
        self.parent = parent
        self.is_root= is_root
        self.is_builtin = False
        self._plugin.set_fs(app._command_fs)

    def _path_to_module(self, path):
        p = path.strip(u'/').rsplit('.')[0]
        return p.replace('/', '.')

    def compile(self):
        # アプリケーションルートのpublicモジュールかパッケージからのみ呼ばれる
        assert self.is_root == True or self.is_package == True
        for e in self.fs.DirectoryObject(self.package_root_path).read():
            if e.is_dir:
                self._compile_dir(e)
            else:
                self._compile_file(e)

    def _compile_file(self, e):
        if self.is_root and e.path == u'/public.casm':
            self.filepath = e.path
            self.application.i18n.write(u'[WARNING] public.casm is obsolete')
            self.application._system.deprecate_logger.warning(u'public.casm is obsolete: %s' % self.application.name)
            # self._compile(e.path)
        elif e.path.endswith(u'.casm') or e.path.endswith(u'.pcasm') or e.path.endswith(u'.casm.lit'):
            mod = self.__class__(self._app, self)
            mod.filepath = e.path
            if e.path.endswith(u'.casm.lit'):
                mod._type = 'casm.lit'
            mod._name = unicode(self._path_to_module(e.basename))
            if mod._name in self.sub_modules:
                raise Exception(self._app.i18n.get(u'Module $name is already defined', 
                                           name=mod._name))
            mod._compile(e.path)

            if self.has_module(mod.name, set()):
                raise Exception(self.application.i18n.get(u'Module $name is already defined in $app', 
                                                          name=mod.name, 
                                                          app=self.get_module(mod.name)._app.name))
            self.sub_modules[mod.name] = mod
            mod.last_modified = e.last_modified
        elif e.path == u'/formats.xjson':
            o = self.fs.open(e.path)
            self._plugin.feed(o.read())

    def _compile_dir(self, e):
        mod = Package(self._app, self)
        mod._name = unicode(self._path_to_module(e.basename.strip(u'/')))
        mod.package_root_path = e.path
        mod.compile()
        if self.has_package(mod.name, set()):
            raise Exception(self.application.i18n.get(u'Package $name is already defined in $app', 
                                                      name=module.name, 
                                                      app=self.get_package(mod.name)._app.name))
        self.sub_packages[mod.name] = mod

    def _compile(self, path):
        o = self.fs.open(path)
        if path.endswith('.casm'):
            for t in self.parse_casm(o):
                t.declare(self)
        elif path.endswith('.pcasm'):
            d = to_decl_style(o)
            if self.pcasm_cache:
                io = self.pcasm_cache
            else:
                io = StringIO(d)
                io.path = o.path
                self.pcasm_cache = io
            for t in self.parse_casm(io):
                t.declare(self)
        elif path.endswith('.xcasm'):
            for t in self.parse_casm(o, 'xcasm'):
                t.declare(self)
        else:
            for t in self.parse_casm(o, 'lit'):
                t.declare(self)

    def parse_casm(self, fo, type='casm'):
        try:
            if type == 'casm':
                self._show_msg(fo)
                self._app.cout.write(u'...')
                r = parse(fo.read())
            elif type == 'xcasm':
                r = xcasm.parse(fo.read())
            elif type == 'lit':
                self._show_msg(fo)
                self._app.cout.write(u'...')
                r = parse_literate(fo.read())
        except:
            self._app.cout.writeln(u'NG')
            raise
        else:
            self._app.cout.writeln(u'OK')
        return r

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

class Package(AppModule):
    is_package = True

class FilterModule(Module):
    def __init__(self, system):
        filterapp = system.dummy_app
        filterapp._name = u'filter'
        Module.__init__(self, filterapp)

class IntegratedModule(object):
    u"""標準モジュールとユーザ定義モジュールの複合モジュール
    """
    def __init__(self, system):
        coreapp = system._core_app
        self._core = CoreModule(coreapp, None, True)
        self._system = system
        self._global = None

    def compile(self, *args):
        self._core.compile(*args)

    def resolve(self):
        self._core.resolve()
    
    def make_blank_module(self, app):
        app_module = AppModule(app, app.parent._schema_module, True)
        return app_module

    def make_app_module(self, app):
        app_module = AppModule(app, app.parent._schema_module, True)
        app_module.compile()
        return app_module



class LocalModule(Module):
    def __init__(self, parent):
        Module.__init__(self, parent._app)
        self.parent = parent
        self._name = u'$local$' # 絶対に使われない名前をデフォルトにしておく
        
    @property
    def schema_finder(self):
        return self

    def add_local(self, schema_string):
        self.compile(schema_string)

    def compile(self, schema_string):
        u"""組み込みコマンドの型指定など、オンザフライでスキーマを構築するためのメソッド。
        """

        self.compiled = False
        from topdown import until, many, as_parser
        def modname(cs):
            cs.parse(until('m'))
            cs.parse('module')
            cs.parse(many(' '))
            n = cs.parse(until(';'))
            return n.strip()

        self.ast_ns = {}
        self.proto_ns = {}
        self.class_ns = {}
        self.saved_st = {}
        self.const_ns = {}
        self.kind_ns = {}
        self.schema_ns = {}
        self.command_ns = {}

        self._name = as_parser(modname).run(schema_string)
        for t in parse(schema_string):
            t.declare(self)
            
        self.resolve()

    def _another_app_callback(self, rname, tracked=(), scope_func=None, type=u''):
        return self._app._system.get_app(app_name).schema_finder._get_resource(rname, tracked, scope_func, type)

    def clone(self):
        return self

