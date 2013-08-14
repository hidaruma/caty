#coding:utf-8
from __future__ import with_statement
from caty.core.casm.loader import CommandLoader, BuiltinLoader
from caty.core.language import split_colon_dot_path
from caty.core.schema import schemata
from caty.core.schema.base import Annotations, Annotation
from caty.core.casm.language.casmparser import parse, parse_literate
from caty.core.casm.language import xcasmparser as xcasm
from caty.core.casm.language.ast import ClassReference
from caty.core.casm.cursor import (SchemaBuilder, 
                                   ReferenceResolver, 
                                   CycleDetecter, 
                                   ProfileBuilder, 
                                   TypeVarApplier,
                                   TypeParamApplier,
                                   TypeNormalizer, 
                                   TreeDumper,
                                   DependencyAnalizer)
from caty.core.casm.language.ast import IntersectionNode
from caty.core.casm.plugin import PluginMap
from caty.jsontools.path.validator import to_decl_style
from caty.core.exception import throw_caty_exception, CatyException, SystemResourceNotFound
from caty.util import error_to_ustr
from caty.util.path import join
from caty.jsontools import xjson
from threading import RLock
from StringIO import StringIO
from caty.core.facility import Facility
from functools import partial

class Module(Facility):
    class Relation(object):
        def __init__(self):
            self.names = {}

        def __contains__(self, name):
            return name in self.names

        def mark(self, name):
            self.names[name] = True

        def add(self, name):
            self.names[name] = False

        def __getitem__(self, name):
            return self.names[name]

        def is_illegal(self):
            return False in self.names.values()

    is_package = False
    is_class = False
    def __init__(self, app, parent=None):
        from caty.core.casm.module.classmodule import ClassModule
        self._app = app
        self.schema_ns = {}
        self.annotation_ns = {}
        self.annotation_proto_ns = {}
        self.command_ns = {}
        self.class_ns = {}
        self.facility_ns = {}
        self.entity_ns = {}
        self.command_loader = None
        self.sub_modules = {}
        self.sub_packages = {}
        self.parent = parent
        self.force = False
        self._name = u'public' # デフォルト値
        self._system = app._system
        self._lazy_resolve = []
        self._plugin = PluginMap()
        self._type = u'casm'
        self._literate = False
        self._fragment = False
        self.ast_ns = {}
        self.proto_ns = {}
        self.saved_st = {}
        self.const_ns = {}
        self.compiled = False
        self.docstring = u''
        self.last_modified = 0
        self.timing = u'boot'
        self.attaches = None
        self.loaded = True
        self.annotations = Annotations([])
        self.package_root_path = u'/'
        self.facility_classes = {}
        self.assertions = []

        self.add_schema = partial(self._add_resource, scope_func=lambda x:x.schema_ns, type=u'Type')
        self.get_type = partial(self._get_resource, scope_func=lambda x:x.schema_ns, type=u'Type')
        self.has_schema = partial(self._has_resource, scope_func=lambda x:x.schema_ns, type=u'Type')

        self.add_kind = partial(self._add_resource, scope_func=lambda x:x.ast_ns, type=u'Kind', see_register_public=True)
        self.get_kind = partial(self._get_resource, scope_func=lambda x:x.ast_ns, type=u'Kind')
        self.has_kind = partial(self._has_resource, scope_func=lambda x:x.ast_ns, type=u'Kind')

        self.add_command = partial(self._add_resource, scope_func=lambda x:x.command_ns, type=u'Command')
        self.get_command = partial(self._get_resource, scope_func=lambda x:x.command_ns, type=u'Command')
        self.has_command_type = partial(self._has_resource, scope_func=lambda x:x.command_ns, type=u'Command')
        
        self.add_proto_type = partial(self._add_resource, scope_func=lambda x:x.proto_ns, type=u'Command', see_register_public=True, see_filter=True)
        self.get_proto_type = partial(self._get_resource, scope_func=lambda x:x.proto_ns, type=u'Command')
        self.has_proto_type = partial(self._has_resource, scope_func=lambda x:x.proto_ns, type=u'Command')
        
        self.add_ast = partial(self._add_resource, scope_func=lambda x:x.ast_ns, type=u'Type', see_register_public=True, ignore_undefined=True)
        self.get_ast = partial(self._get_resource, scope_func=lambda x:x.ast_ns, type=u'Type')
        self.has_ast = partial(self._has_resource, scope_func=lambda x:x.ast_ns, type=u'Type')
        
        self.get_syntax_tree = partial(self._get_resource, scope_func=lambda x:x.saved_st, type=u'Type')
        self.has_syntax_tree = partial(self._has_resource, scope_func=lambda x:x.saved_st, type=u'Type')
        
        self.add_class = partial(self._add_resource, scope_func=lambda x:x.class_ns, type=u'Class', see_register_public=True, callback=lambda target: ClassModule(self._app, self, target))
        self.get_class = partial(self._get_resource, scope_func=lambda x:x.class_ns, type=u'Class')
        self.has_class = partial(self._has_resource, scope_func=lambda x:x.class_ns, type=u'Class')
 
        self.add_facility = partial(self._add_resource, scope_func=lambda x:x.facility_ns, type=u'Facility', see_register_public=True)
        self.get_facility = partial(self._get_resource, scope_func=lambda x:x.facility_ns, type=u'Facility')
        self.has_facility = partial(self._has_resource, scope_func=lambda x:x.facility_ns, type=u'Facility')
        self.get_facility_classes = partial(self._get_resource, scope_func=lambda x:x.facility_classes, type=u'Facility')

        self.add_entity = partial(self._add_resource, scope_func=lambda x:x.entity_ns, type=u'Entity', see_register_public=True)
        self.get_entity = partial(self._get_resource, scope_func=lambda x:x.entity_ns, type=u'Entity')
        self.has_entity = partial(self._has_resource, scope_func=lambda x:x.entity_ns, type=u'Entity')

        

        self.declare_annotation = partial(self._add_resource, scope_func=lambda x:x.annotation_proto_ns, type=u'Annotation')
        self.get_annotation_proto = partial(self._get_resource, scope_func=lambda x:x.annotation_proto_ns, type=u'Annotation')
        self.add_annotation = partial(self._add_resource, scope_func=lambda x:x.annotation_ns, type=u'Annotation')
        self.get_annotation = partial(self._get_resource, scope_func=lambda x:x.annotation_ns, type=u'Annotation')
        self.has_annotation = partial(self._has_resource, scope_func=lambda x:x.annotation_ns, type=u'Annotation')

        self.type_params = []
        self.__related = Module.Relation()

    @property
    def type(self):
        return self._type

    @property
    def app(self):
        return self._app

    @property
    def system(self):
        return self._system

    @property
    def name(self):
        return self._name
 
    @property
    def literate(self):
        return self._literate

    @property
    def related(self):
        return self.__related

    def _get_full_name(self):
        return self.canonical_name+'.'+self.type

    def _get_mod_and_app(self, t):
        a = t.module.application.name
        m = t.module.canonical_name + '.' + t.module.type
        return m, a

    def _add_resource(self, target, scope_func=None, type=u'', see_register_public=False, see_filter=False, callback=None, force=False, ignore_undefined=False):
        scope = scope_func(self)
        name = target.name
        if name in scope and not force:
            t = scope[name]
            if (t.defined and not target.redifinable) or (type == u'Type' and target.defined == t.defined and t.redifinable == target.redifinable):
                m, a = self._get_mod_and_app(t)
                raise Exception(self.application.i18n.get(u'%s $name of $this is already defined in $module of $app' % type, 
                                                   name=name, 
                                                   this=self._get_full_name(),
                                                   module=m,
                                                   app=a))
            else:
                if type == u'Type':
                    target.body = IntersectionNode(scope[name].body, target.body)
                    target.defined = False
                    target.redifinable = False
                elif type == u'Class':
                    if isinstance(target.expression, ClassReference):
                        target = self.get_class(target.expression.name)._clsobj
                    for m in target.member:
                        m.clone().declare(t)
                    return
        if see_register_public and ('register-public' in target.annotations or (not self.is_class and 'register-public' in self.annotations)):
            if not self.is_root:
                self.parent._add_resource(target, scope_func, type, see_register_public=True, see_filter=False, callback=callback)
        if see_register_public and ('override-public' in target.annotations or 'override-public' in self.annotations) and not force:
            if self.force:
                for m in (u'builtin', u'public'):
                    mod = self.find_root().get_module(m)
                    if mod._has_resource(name, set(), scope_func, type):
                        break
                mod._add_resource(target, scope_func, type, see_register_public=True, see_filter=False, callback=callback, force=True)
            else:
                if not self.is_root:
                    self.parent._add_resource(target, scope_func, type, see_register_public=True, see_filter=False, callback=callback)
        if see_register_public and 'override' in target.annotations and not force and self.force:
            tgt = self.get_module(target.annotations['override'].value)
            tgt._add_resource(target, scope_func, type, see_register_public=True, see_filter=False, callback=callback, force=True)
        if see_register_public and 'override' in self.annotations and not force and self.force:
            tgt = self.get_module(self.annotations['override'].value)
            tgt._add_resource(target, scope_func, type, see_register_public=True, see_filter=False, callback=callback, force=True)
        if see_filter and 'filter' in target.annotations:
            if self.name != 'filter':
                fm = self.get_module('filter')
                fm._add_resource(target, scope_func, type, see_register_public=False, see_filter=False)
        if not callback:
            scope[name] = target
        else:
            scope[name] = callback(target)

    def _get_resource(self, rname, tracked=(), scope_func=None, type=u''):
        rname = rname.rstrip(':.') # 正規化された名前の一部は:.で終わっているのでそれを取り除く
        if self in tracked:
            raise SystemResourceNotFound(u'%sNotFound'%type, u'$name', name=rname)
        scope = scope_func(self)
        app_name, mod_name, name = split_colon_dot_path(rname, u'ignore')
        if app_name:
            if app_name in ('this', 'caty', self._app.name):
                pass
            else:
                return self._another_app_callback(rname, tracked, scope_func, type)
        if mod_name:
            if mod_name == self.name:
                r = self._get_resource(name, tracked, scope_func, type)
                if is_valid_call(r, mod_name):
                    return r
                raise SystemResourceNotFound(u'%sNotFound' % type, u'$name', name=rname)
            mod = self.get_module(mod_name)
            r = mod._get_resource(name, tracked, scope_func, type)
            if is_valid_call(r, mod_name):
                return r
            raise SystemResourceNotFound(u'%sNotFound' % type, u'$name', name=rname)
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
                return self.parent._get_resource(name, tracked, scope_func, type)
        raise SystemResourceNotFound(u'%sNotFound' % type, u'$name', name=rname)

    def _has_resource(self, name, tracked=(), scope_func=None, type=u''):
        try:
            o = self._get_resource(name, tracked, scope_func, type)
        except CatyException as e:
            return False
        return True

    def _another_app_callback(self, rname, tracked=(), scope_func=None, type=u''):
        raise Exception(u'To call another application\'s %s is forbidden at compile-time' % type)

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
        if self.parent and self.parent.is_package:
            return self.parent.canonical_name + '.' + self.name
        else:
            return self.name

    def get_plugin(self, name):
        return self._plugin.get_plugin(name)

    def find_public_module(self):
        if self.is_root:
            return self
        elif self.parent:
            return self.parent.find_public_module()
        else:
            return self

    def has_module(self, name):
        from operator import truth
        return truth(self.find_public_module()._get_module(name))

    def get_module(self, name):
        name = name.rstrip(':')
        m = self.find_public_module()._get_module(name)
        if not m:
            raise SystemResourceNotFound(u'ModuleNotFound', u'$name', name=name)
        return m

    def _get_module(self, name, tracked=None):
        tracked = set() if tracked is None else tracked
        if name == self.name:
            return self
        if name in self.sub_modules:
            return self.sub_modules[name]
        if '.' in name:
            pkg, rest = name.split('.', 1)
            pm = self._get_package(pkg, tracked)
            if pm:
                return pm._get_module(rest, tracked)
        if self.parent:
            if self.canonical_name in tracked:
                return None
            tracked.add(self.canonical_name)
            return self.parent._get_module(name)
        return None

    def load_on_demand(self, name):
        m = self.find_public_module().get_module(name)
        if not m:
            raise SystemResourceNotFound(u'ModuleNotFound', u'$name', name=name)
        trunk = m.canonical_name.replace('.', '/')
        path = u'/' + trunk + u'.casm' if not m._literate else u'.casm.lit'
        if not m.is_root:
            for k, v in m.ast_ns.items():
                if u'register-public' in v.annotations:
                    m.find_root().ast_ns.pop(k)
        for k in m.facility_ns.keys() + m.entity_ns.keys():
            m.app._facility_classes.pop(k)
        m.ast_ns = {}
        m.proto_ns = {}
        m.class_ns = {}
        m.facility_ns = {}
        m.entity_ns = {}
        m.clear_namespace()
        try:
            m.force = True
            m._compile(path, force=True)
        finally:
            m.force = False
        m.loaded = True

    def discard_module(self, name):
        m = self.find_public_module().get_module(name)
        if not m:
            raise SystemResourceNotFound(u'ModuleNotFound', u'$name', name=name)
        trunk = m.canonical_name.replace('.', '/')
        path = u'/' + trunk + u'.casm' if not m._literate else u'.casm.lit'
        if not m.is_root:
            for k, v in m.ast_ns.items():
                if u'register-public' in v.annotations:
                    r = m.find_root()
                    if k in r.ast_ns:
                        r.ast_ns.pop(k)
        for k in m.facility_ns.keys() + self.entity_ns.keys():
            if k in m.app._facility_classes:
                m.app._facility_classes.pop(k)
        m.ast_ns = {}
        m.proto_ns = {}
        m.class_ns = {}
        m.facility_ns = {}
        m.entity_ns = {}
        m.clear_namespace()

    def has_package(self, name):
        from operator import truth
        return truth(self.find_public_module()._get_package(name))

    def get_package(self, name):
        name = name.rstrip('.')
        m = self.find_public_module()._get_package(name)
        if not m:
            raise SystemResourceNotFound(u'PackageNotFound', u'$name', name=name)
        return m

    def _get_package(self, name, tracked=None):
        tracked = set() if tracked is None else tracked
        if name == self.name:
            return self
        if name in self.sub_packages:
            return self.sub_packages[name]
        if '.' in name:
            pkg, rest = name.split('.', 1)
            pm = self._get_package(pkg, tracked)
            if pm:
                tracked.add(pm.canonical_name)
                return pm._get_package(rest, tracked)
        if self.parent:
            if self.canonical_name in tracked:
                return None
            tracked.add(self.canonical_name)
            return self.parent._get_package(name)
        return None

    def get_modules(self):
        if not self.is_package:
            yield self
        for m in self.sub_modules.values():
            for r in m.get_modules():
                yield r
        for p in self.sub_packages.values():
            for r in p.get_modules():
                yield r

    def list_modules(self, rec=False):
        for m in self.sub_modules.values():
            yield m
            if rec:
                for r in m.list_modules(rec):
                    yield r
        if rec:
            for p in self.sub_packages.values():
                for r in p.list_modules(rec):
                    yield r

    def list_packages(self, rec=False):
        for p in self.sub_packages.values():
            yield p
            if rec:
                for r in p.list_packages(rec):
                    yield r

    def get_packages(self):
        if self.is_package:
            yield self
        for p in self.sub_packages.values():
            for r in p.get_packages():
                yield r

    def add_sub_module(self, module):
        module.parent = self
        if self.has_module(module.name) and self.get_module(module.name).canonical_name == module.canonical_name:
            raise Exception(self.application.i18n.get(u'Can not register $name.$type1. $name.$type2 is already defined in $app', 
                                                      name=module.name, 
                                                      type1=module.type,
                                                      app=self._app.name,
                                                      type2=self.get_module(module.name).type))
        self.sub_modules[module.name] = module

    def resolve(self):
        u"""型参照の解決
        """
        self._attache_module()
        #self._resolve_alias()
        self._build_schema_tree()
        self._resolve_reference()
        self._check_dependency()
        self._detect_cycle()
        self._apply_type_var()
        self._normalize()
        self._post_process()
        self._register_command()
        self._register_facility()
        self._validate_signature()
        self.set_compiled(True)

    def set_compiled(self, v):
        self.compiled = True
        for m in self.sub_modules.values() + self.class_ns.values():
            m.set_compiled(v)

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

    def make_dep_analizer(self):
        return DependencyAnalizer(self)

    def make_profile_builder(self):
        return ProfileBuilder(self)

    def _attache_module(self):
        if self.attaches:
            target = self.get_module(self.attaches)
            if target._type != self._type:
                throw_caty_exception(u'SCHEMA_COMPILE_ERROR', 
                                     u'Module type missmatched: $name=$type, $name2=$type2',
                                     name=self.name, type=self._type, name2=self.attaches, type2=target.type)
            for c in self.class_ns.values():
                c._clsobj.declare(target)
            self.class_ns = {}
            for t in self.ast_ns.values():
                t.declare(target)
            self.ast_ns = {}
            for p in self.proto_ns.values():
                p.declare(target)
            self.proto_ns = {}
            for f in self.facility_ns.values():
                p.declare(target)
            self.facility_ns = {}
            for e in self.entity_ns.values():
                p.declare(target)
            self.entity_ns = {}
            for a in self.annotation_proto_ns.values():
                a.declare(target)
            self.annotation_proto_ns = {}
            r = True
        else:
            r = False

        for m in self.sub_modules.values():
            if m._attache_module():
                del self.sub_modules[m.name]
        for v in self.sub_packages.values():
            m._attache_module()
        return r

    def _resolve_alias(self):
        for k, c in self.class_ns.items():
            if c.is_alias:
                o = self.get_class(c.reference).clone()
                o._name = c.name
                self.class_ns[k] = o
        for k, c in self.ast_ns.items():
            if c.is_alias:
                o = self.get_ast(c.reference).clone()
                o._name = c.name
                self.ast_ns[k] = o
        for k, c in self.proto_ns.items():
            if c.is_alias:
                o = self.get_proto_type(c.reference)
                o.name = c.name
                self.proto_ns[k] = o
        for m in self.sub_modules.values() + self.class_ns.values() + self.sub_packages.values():
            m._resolve_alias()

    def _build_schema_tree(self):
        self.saved_st.update(self.ast_ns)
        if not self.compiled:
            if self.is_root:
                self.application.cout.write(u'  * ' + self.application.i18n.get(u'Initializing types') + '...')
            try:
                self._loop_exec(self.ast_ns, self.make_schema_builder, lambda k, v:self.add_schema(v))
                self._loop_exec(self.annotation_proto_ns, self.make_schema_builder, lambda k, v:self.add_annotation(v))
            except:
                self.application.cout.writeln(u'NG')
                raise
        for m in self.sub_modules.values() + self.class_ns.values() + self.sub_packages.values():
            m._build_schema_tree()
        if self.is_root and not self.compiled:
            self.application.cout.writeln(u'OK')

    def _resolve_reference(self):
        if not self.compiled:
            if self.is_root:
                self.application.cout.write(u'  * ' + self.application.i18n.get(u'Resolving type references') + '...')
            try:
                self._loop_exec(self.schema_ns, self.make_reference_resolver, lambda k, v:self.schema_ns.__setitem__(k, v))
                self._loop_exec(self.annotation_ns, self.make_reference_resolver, lambda k, v:self.annotation_ns.__setitem__(k, v))
            except:
                self.application.cout.writeln(u'NG')
                raise
        for m in self.sub_modules.values() + self.class_ns.values() + self.sub_packages.values():
            m._resolve_reference()
        if self.is_root and not self.compiled:
            self.application.cout.writeln(u'OK')

    def _apply_type_var(self):
        if not self.compiled:
            if self.is_root:
                self.application.cout.write(u'  * ' + self.application.i18n.get(u'Applying type parameters') + '...')
            try:
                self._loop_exec(self.schema_ns, self.make_typevar_applier, lambda k, v:self.schema_ns.__setitem__(k, v))
                self._loop_exec(self.annotation_ns, self.make_typevar_applier, lambda k, v:self.annotation_ns.__setitem__(k, v))
            except:
                self.application.cout.writeln(u'NG')
                raise
        for m in self.sub_modules.values() + self.class_ns.values() + self.sub_packages.values():
            m._apply_type_var()
        if self.is_root and not self.compiled:
            self.application.cout.writeln(u'OK')

    def _detect_cycle(self):
        if not self.compiled:
            if self.is_root:
                self.application.cout.write(u'  * ' + self.application.i18n.get(u'Detecting illegal cyclic type definition') + '...')
            try:
                self._loop_exec(self.schema_ns, self.make_cycle_detecter, lambda k, v: v)
                self._loop_exec(self.annotation_ns, self.make_cycle_detecter, lambda k, v: v)
            except:
                self.application.cout.writeln(u'NG')
                raise
        for m in self.sub_modules.values() + self.class_ns.values() + self.sub_packages.values():
            m._detect_cycle()
        if self.is_root and not self.compiled:
            self.application.cout.writeln('OK')

    def _normalize(self):
        if not self.compiled:
            if self.is_root:
                self.application.cout.write(u'  * ' + self.application.i18n.get(u'Normalizing types') + '...')
            try:
                self._loop_exec(self.schema_ns, self.make_type_normalizer, lambda k, v:self.schema_ns.__setitem__(k, v))
                self._loop_exec(self.annotation_ns, self.make_type_normalizer, lambda k, v:self.annotation_ns.__setitem__(k, v))
            except:
                self.application.cout.writeln(u'NG')
                raise
        for m in self.sub_modules.values() + self.class_ns.values() + self.sub_packages.values():
            m._normalize()
        if self.is_root and not self.compiled:
            self.application.cout.writeln('OK')

    def _check_dependency(self):
        msg = []
        if not self.compiled:
            if self.is_root:
                self.application.cout.write(u'  * ' + self.application.i18n.get(u'Checking dependencies') + '...')
            graph = set()
            self._loop_exec(self.schema_ns, self.make_dep_analizer, lambda k, v: graph.update(v) if v else v)
            self._loop_exec(self.annotation_ns, self.make_dep_analizer, lambda k, v: graph.update(v) if v else v)
            marked = set()
            for a, b in graph:
                if (b, a) in graph:
                    if b.name not in a.related or a.name not in b.related:
                        self.application.cout.writeln('NG')
                        throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'A cyclic dependency between $mod1 and $mod2 was detected', mod1=a.name, mod2=b.name)
                    else:
                        if a.related[b.name] or b.related[a.name]:
                            continue
                        a.related.mark(b.name)
                        b.related.mark(a.name)
                        msg.append(u'    [WARNING] ' + self.application.i18n.get(u'A cyclic dependency between $mod1 and $mod2 was detected', mod1=a.name, mod2=b.name))
        for name in self.related.names:
            mod = self.get_module(name)
            if self.name not in mod.related:
                self.application.cout.writeln('NG')
                throw_caty_exception(u'SCHEMA_COMPILE_ERROR', 
                                     u'Illegal `related` declaration at $name',
                                     name=self.name)
        for m in self.sub_modules.values() + self.class_ns.values() + self.sub_packages.values():
            msg.extend(m._check_dependency())
        if self.is_root and not self.compiled:
            self.application.cout.writeln('OK')
            for m in msg:
                self.application.cout.writeln(m)
        else:
            return msg

    def _register_command(self):
        if not self.compiled:
            import re
            ptn = re.compile(u'_assert_[0-9]+$')
            nums = []
            for a in self.assertions:
                if ptn.match(a.name):
                    nums.append(int(a.name.rsplit('_', 1)[1]))
            if nums:
                max_num = nums[-1] + 1
            else:
                max_num = 1
            usables = []
            for i in range(1, max_num):
                if i not in nums:
                    usables.append(i)
            for a in self.assertions:
                if not a.name:
                    if usables:
                        a.name = u'_assert_' + str(usables.pop(0))
                    else:
                        a.name = u'_assert_' + str(max_num)
                        max_num += 1
                a.re_declare(self)
            if self.is_root:
                self.application.cout.write(u'  * ' + self.application.i18n.get(u'Initializing commands') + '...')
            try:
                for k, v in self.proto_ns.items():
                    try:
                        cursor = v.module.make_profile_builder()
                        self.add_command(cursor.visit(v))
                    except:
                        print '    [DEBUG]', k
                        raise

            except:
                self.application.cout.writeln('NG')
                print '    [ERROR]', u'%s::%s (%s)' % (self._app.name, self.canonical_name, self.type)
                raise

        for m in self.class_ns.values() + self.sub_modules.values() + self.sub_packages.values():
            m._register_command()
        if self.is_root and not self.compiled:
            self.application.cout.writeln('OK')

    def _register_facility(self):
        emsgs = []
        if not self.compiled:
            if self.is_root:
                self.application.cout.write(u'  * ' + self.application.i18n.get(u'Initializing facilities') + '...')
            for k, v in self.facility_ns.items():
                if not v.clsname:
                    emsgs.append(self.application.i18n.get(u'Facility class not specified: $name', name=k))

                    facility_class = None
                    config = {}
                else:
                    try:
                        facility_class = self._load_facility_class(k, v.clsname)
                        try:
                            config = self._load_facility_config(k)
                        except:
                            import traceback
                            traceback.print_exc()
                            emsgs.append(self.application.i18n.get(u'Failed to load facility config: $name', name=v.clsname))
                            config = {}
                    except:
                        import traceback
                        traceback.print_exc()
                        emsgs.append(self.application.i18n.get(u'Failed to load facility class: $name', name=v.clsname))
                        facility_class = None
                if facility_class:
                    facility_class.__system_config__ = config
                self.facility_classes[v.name] = facility_class
        for m in self.sub_modules.values() + self.sub_packages.values() + self.class_ns.values():
            m._register_facility()
        if self.is_root and not self.compiled:
            self.application.cout.writeln('OK')

        if not self.compiled:
            for k, v in self.entity_ns.items():
                if not v.facility_name:
                    continue
                if '__master' not in v.annotations:
                    continue
                self._app.register_facility(v.name, self.get_facility_classes(v.facility_name), v.user_param)

            for k, v in self.entity_ns.items():
                if not v.facility_name:
                    continue
                if '__master' in v.annotations:
                    continue
                self._app.register_entity(v.name, v.facility_name, v.user_param)
        if emsgs:
            self.application.cout.writeln(u'')
        for e in emsgs:
            self.application.cout.writeln(u'  [Warning] ' + e)

    def _load_facility_class(self, name, uri):
        from caty.core.casm.loader import dynamic_load
        if not uri.startswith(u'python:'):
            raise Exception(self.application.i18n.get(u'Invalid reference: $ref, $name, $mod', ref=uri, name=name, mod=self.name))
        uri = uri.replace('python:', '')
        loader = _FaciltyLoader(uri, name, self)
        return loader.load()

    def _load_facility_config(self, fclname):
        return self.system._global_config.facilities.get(fclname, {})

    def get_facility_or_entity(self, name):
        if self.has_facility(name):
            return self.get_facility(name)
        if self.has_entity(name):
            return self.get_entity(name)

    def _validate_signature(self):
        for m in self.class_ns.values() + self.sub_modules.values() + self.sub_packages.values():
            m._validate_signature()

    def _loop_exec(self, target, cursor_factory, callback):
        try:
            for k, v in target.items():
                try:
                    cursor = cursor_factory()
                    callback(k, cursor.visit(v))
                except:
                    print '[DEBUG]', k
                    raise

        except:
            print '[ERROR]', u'%s::%s (%s)' % (self._app.name, self.canonical_name, self.type)
            raise

    def _post_process(self):
        # 型計算の後処理
        # 現状ではコレクション型のうちid-typeが不明の物の処理を行う
        # identifiedで指定されたパスからidの型を特定し、アノテーションに付け加える
        from caty.core.typeinterface import dereference
        from caty.core.casm.language.schemaparser import CasmJSONPathSelectorParser
        from caty.core.casm.cursor.dump import TreeDumper
        from caty.core.casm.language.ast import ClassIntersectionOperator, ClassReference, ScalarNode
        for k, v in self.schema_ns.items():
            if u'__collection' in v.annotations and u'__identified' in v.annotations and u'__id-type' not in v.annotations:
                path = CasmJSONPathSelectorParser().run(v.annotations[u'__identified'].value)
                try:
                    p = path.select(dereference(v.body)).next()
                    v.annotations.add(Annotation(u'__id-type', p.type))
                except Exception as e:
                    print u'[Warning]', v.canonical_name, e
                else:
                    clsnames = [k, k.replace(u'Record', u'')]
                    for c in clsnames:
                        if self.has_class(c):
                            cls = self.get_class(c)._clsobj
                            if isinstance(cls.expression, ClassIntersectionOperator):
                                for n in [cls.expression.left, cls.expression.right]:
                                    if isinstance(n, ClassReference) and n.name == u'Collection' and len(n.type_params) == 1:
                                        n.type_params.append(ScalarNode(p.type))
                                        break
                            break
        for m in self.class_ns.values() + self.sub_modules.values() + self.sub_packages.values():
            m._post_process()

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
        return make_structured_doc(self.docstring or u'')

    def find_root(self):
        if self.is_root:
            return self
        else:
            return self.parent.find_root()

    def iter_parents(self):
        if self.parent:
            yield self.parent
            for p in self.parent.iter_parents():
                yield p

    def clear_namespace(self):
        self.compiled = False
        self.schema_ns = {}
        self.command_ns = {}
        self.saved_st = {}
        self.annotation_ns = {}

        for k, v in self.proto_ns.items():
            v.profile_container = None
        for m in self.sub_modules.values():
            m.clear_namespace()
        for k, m in self.sub_packages.items():
            m.clear_namespace()
        for m in self.class_ns.values():
            m.clear_namespace()
        for k in self.facility_ns.keys() + self.entity_ns.keys():
            m.app._facility_classes.pop(k)

    def is_runaway_exception(self, e):
        try:
            return u'runaway' in self.get_type(e.tag).annotations
        except:
            return False

    def is_runaway_signal(self, e):
        import caty.jsontools as json
        return e.is_runaway

    def apply(self, ignore):
        return ignore

class _FaciltyLoader(object):
    def __init__(self, clsref, facility_name, module):
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

class LocalModule(Module):
    def __init__(self, parent):
        Module.__init__(self, parent._app)
        self.parent = parent
        self.is_root = False
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
        self.annotation_ns = {}
        self.annotation_proto_ns = {}
        self.proto_ns = {}
        self.class_ns = {}
        self.saved_st = {}
        self.const_ns = {}
        self.schema_ns = {}
        self.command_ns = {}

        self._name = as_parser(modname).run(schema_string)
        for t in parse(schema_string):
            t.declare(self)
            
        self.resolve()

    def _another_app_callback(self, rname, tracked=(), scope_func=None, type=u''):
        app_name, rname = rname.split('::', 1)
        return self._app._system.get_app(app_name).schema_finder._get_resource(rname, tracked, scope_func, type)

    def clone(self):
        return self

def is_valid_call(res, mod_name):
    if res.module.name == mod_name:
        return True
    if mod_name in ('builtin', 'public'):
        return True
    if res.module.parent and res.module.parent.name == mod_name:
        return True
    return False
