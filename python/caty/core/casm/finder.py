#coding:utf-8
from caty.core.resource import ResourceFinder
from caty.core.facility import ReadOnlyFacility
from caty.core.language import split_colon_dot_path
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
        self.get_type = lambda key: self._get_resource(key, )

    def add_local(self, string):
        u"""ローカルスキーマの追加は一見すると破壊的操作だが、
        実際には永続的な効果を及ぼさず、またそもそも CatyFIT など限られた用途にしか用いない。
        そのため、書き込み処理としては扱わない。
        """
        self._local.compile(string)

    def clone(self):
        return self

    def to_name_tree(self):
        return self._module.to_name_tree()

    def items(self):
        return self._module.command_ns.items()

    def __setitem__(self, key, value):
        raise Exception(ro.i18n.get('Uneable to add command at runtime: $name', name=key))

    def __delitem__(self, key):
        raise Exception(ro.i18n.get('Uneable to add command at runtime: $name', name=key))

    def update(self, arg):
        raise Exception(ro.i18n.get('Uneable to add command at runtime: $name', name=key))



