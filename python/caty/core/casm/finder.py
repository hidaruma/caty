#coding:utf-8
from caty.core.resource import ResourceFinder
from caty.core.facility import ReadOnlyFacility
from caty.core.casm.language.casmparser import parse
from caty.core.casm.language.ast import ModuleName
import caty.core.runtimeobject as ro
import caty.core.schema as schema
from caty.core.casm.cursor import SchemaBuilder, ReferenceResolver, ProfileBuilder, TypeVarApplier, TypeNormalizer

from topdown import *


class SchemaFinder(ResourceFinder, ReadOnlyFacility):
    u"""スキーマ検索オブジェクト。
    通常のコマンドクラスから参照されるので、ファシリティとして扱う。
    """
    def __init__(self, module, app, system, LocalModule):
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
                if self._local.has_syntax_tree(k):
                    return self._local.get_syntax_tree(key)
            elif self._local.name == 'public':
                if self._local.has_syntax_tree(key):
                    return self._local.get_syntax_tree(key)
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


    def get_proto_type(self, key):
        c = key.count(':')
        if c == 2: #別のアプリケーションを参照している場合
            app_name, cmd = key.split(':', 1)
            if app_name in self.system.app_names:
                app = self.system.get_app(app_name)
                return app.command_finder.get_proto_type(cmd)
        else:
            return self._module.get_proto_type(key)
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



