#coding:utf-8
from caty.core.resource import ResourceFinder
from caty.core.facility import ReadOnlyFacility
from caty.core.casm.language.casmparser import iparse
from caty.core.casm.language.ast import ModuleName
import caty.core.runtimeobject as ro
import caty.core.schema as schema
from caty.core.casm.cursor import SchemaBuilder, ReferenceResolver, ProfileBuilder, TypeVarApplier, TypeNormalizer

from topdown import *


class SchemaFinder(ResourceFinder, ReadOnlyFacility):
    u"""スキーマ検索オブジェクト。
    通常のコマンドクラスから参照されるので、ファシリティとして扱う。
    """
    def __init__(self, module, app, system):
        self._module = module
        ResourceFinder.__init__(self, app, system)
        self._local = LocalModule(self)

    def add_local(self, string):
        u"""ローカルスキーマの追加は一見すると破壊的操作だが、
        実際には永続的な効果を及ぼさず、またそもそも CatyFIT など限られた用途にしか用いない。
        そのため、書き込み処理としては扱わない。
        """
        self._local.compile(string)

    def __getitem__(self, key):
        key = key.lstrip(':')
        c = key.count(':')
        if  c == 2:
            app_name, scm = key.split(':', 1)
            if app_name == self.application.name:
                return self[scm]
            if app_name in self.system.app_names:
                app = self.system.get_app(app_name)
                return app.schema_finder[scm]
        else:
            if key.startswith(self._local.name+':'):
                k = key.split(':')[1]
                if self._local.has_schema(k):
                    return self._local.get_schema(k)
            elif self._local.name == 'public':
                if self._local.has_schema(key):
                    return self._local.get_schema(key)
            return self._module.get_schema(key)

    def __call__(self, key):
        return self[key]

    def get_ast(self, key):
        key = key.lstrip(':')
        c = key.count(':')
        if  c == 2:
            app_name, scm = key.split(':', 1)
            if app_name == self.application.name:
                return self.get_syntax_tree(scm)
            if app_name in self.system.app_names:
                app = self.system.get_app(app_name)
                return app.schema_finder.get_syntax_tree(scm)
        else:
            if key.startswith(self._local.name+':'):
                k = key.split(':')[1]
                if self._local.get_ast(k):
                    return True
            elif self._local.name == 'public':
                if self._local.get_syntax_tree(key):
                    return True
            return self._module.get_syntax_tree(key)


    def get_schema(self, key):
        return self[key]

    def has_schema(self, key):
        key = key.lstrip(':')
        c = key.count(':')
        if  c == 2:
            app_name, scm = key.split(':', 1)
            if app_name == self.application.name:
                return self.has_schema(scm)
            if app_name in self.system.app_names:
                app = self.system.get_app(app_name)
                return app.schema_finder.has_schema(scm)
        else:
            if key.startswith(self._local.name+':'):
                k = key.split(':')[1]
                if self._local.has_schema(k):
                    return True
            elif self._local.name == 'public':
                if self._local.has_schema(key):
                    return True
            return self._module.has_schema(key)

    def __contains__(self, key):
        return self.has_schema(key)

    def clone(self):
        return self

    def to_name_tree(self):
        return self._module.to_name_tree()

class LocalModule(ResourceFinder):
    def __init__(self, finder):
        self.schema_ns = {}
        self.name = u''
        self.ast_ns = {}
        self.saved_st = {}
        self.schema_finder = OverlayedFinder(self, finder)
        ResourceFinder.__init__(self, finder.application, finder.system)
        self.parent = finder._module

    def add_ast(self, ref):
        if ref in self.ast_ns:
            m, a = self._get_mod_and_app(ref)
            raise Exception(self.application.i18n.get('Type $name of $this is already defined in $module of $app', 
                                                      name=ref.name, 
                                                      this=self.name+'.casm',
                                                      module=m,
                                                      app=a))

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
        if self.parent:
            return self.parent.get_ast(name)
        raise KeyError(name)

    def has_ast(self, name, tracked=None):
        if not tracked:
            tracked = []
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
            if self.parent:
                return self.parent.has_ast(name, t)
            else:
                return False

    def add_lazy_resolve(self, f):
        self._lazy_resolvers.append(f)

    def has_schema(self, name, tracked=()):
        if self in tracked:
            return False
        t = list(tracked ) + [self]
        if name in self.schema_ns:
            return True
        else:
            if ':' in name:
                m, n = name.rsplit(':', 1)
                if m == 'public':
                    return self.has_schema(n)
            if self.parent:
                return self.parent.has_schema(name, t)
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
                m, n = name.rsplit(':', 1)
                if m == 'public':
                    return self.get_schema(n)
        return self.parent.get_schema(name)

    def compile(self, schema_string):
        u"""組み込みコマンドの型指定など、オンザフライでスキーマを構築するためのメソッド。
        """
        def modname(cs):
            cs.parse(until('m'))
            cs.parse('module')
            cs.parse(many(' '))
            n = cs.parse(until(';'))
            return n.strip()
        self.ast_ns = {}
        self.saved_st = {}
        self.schema_ns = {}
        self.name = as_parser(modname).run(schema_string)
        for t in iparse(schema_string):
            t.declare(self)
            
        self._build_schema_tree()
        self._resolve_reference()
        self._apply_type_var()
        self._normalize()

    def _build_schema_tree(self):
        self.saved_st.update(self.ast_ns)
        self._loop_exec(self.ast_ns, SchemaBuilder(self), lambda k, v:self.add_schema(v))
    
    def _resolve_reference(self):
        self._loop_exec(self.schema_ns, ReferenceResolver(self), lambda k, v:self.schema_ns.__setitem__(k, v))

    def _apply_type_var(self):
        self._loop_exec(self.schema_ns, TypeVarApplier(self), lambda k, v:self.schema_ns.__setitem__(k, v))

    def _normalize(self):
        self._loop_exec(self.schema_ns, TypeNormalizer(self), lambda k, v:self.schema_ns.__setitem__(k, v))

    def _loop_exec(self, target, cursor, callback):
        try:
            for k, v in target.items():
                try:
                    callback(k, cursor.visit(v))
                except:
                    print '[DEBUG]', k
                    raise

        except:
            print '[ERROR]', u'Application:%s, module:%s' % (self.application.name, self.name)
            raise


    def add_schema(self, schema):
        self.schema_ns[schema.name] = schema

class OverlayedFinder(object):
    
    def __init__(self, module, finder):
        self.module = module
        self.finder = finder

    def __getitem__(self, key):
        if self.module.has_schema(key):
            return self.module.get_schema(key)
        else:
            return self.finder[key]

    __call__ = __getitem__

class CommandFinder(dict, ResourceFinder, ReadOnlyFacility):
    u"""コマンド検索オブジェクト。
    こちらもコマンドから参照される。
    """
    def __init__(self, module, app, system):
        dict.__init__(self)
        ResourceFinder.__init__(self, app, system)
        self._module = module

    def __getitem__(self, key):
        c = key.count(':')
        if c == 2: #別のアプリケーションを参照している場合
            app_name, cmd = key.split(':', 1)
            if app_name in self.system.app_names:
                app = self.system.get_app(app_name)
                return app.command_finder[cmd]
        else:
            return self._module.get_command_type(key)
        raise KeyError(key)

    def __contains__(self, key):
        c = key.count(':')
        if c == 2: #別のアプリケーションを参照している場合
            app_name, cmd = key.split(':', 1)
            if app_name in self.system.app_names:
                app = self.system.get_app(app_name)
                return cmd in app.command_finder
        else:
            return self._module.has_command(key)
        return False

    def items(self):
        return self._module.command_ns.items()


    def __setitem__(self, key, value):
        raise Exception(ro.i18n.get('Uneable to add command at runtime: $name', name=key))

    def __delitem__(self, key):
        raise Exception(ro.i18n.get('Uneable to add command at runtime: $name', name=key))

    def update(self, arg):
        raise Exception(ro.i18n.get('Uneable to add command at runtime: $name', name=key))



