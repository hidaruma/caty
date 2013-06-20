#coding:utf-8
from caty.core.casm.module.basemodule import *

class ClassModule(Module):
    u"""
    クラスは名前空間を構成するというその機能においてモジュールに近い。
    そのため、実装はモジュールとほぼ同等とする。
    """
    is_class = True
    is_alias = False
    def __init__(self, app, parent, clsobj):
        Module.__init__(self, app, parent)
        self._type = u'class'
        self.command_loader = parent.command_loader
        self._name = clsobj.name
        self._clsobj = clsobj
        for m in clsobj.member:
            m.declare(self)
        self._clsrestriction_proto = clsobj.restriction
        self.is_root = False
        self.annotations = clsobj.annotations
        self.count = 0
        self.type_params = clsobj.type_args
        self.docstring = clsobj.docstring
        self.defined = True
        self.redifinable = False

    def clone(self):
        return ClassModule(self.app, self.parent, self.clsobj)

    @property
    def uri(self):
        return self._clsobj.uri

    @property
    def module(self):
        return self.parent

    @property
    def canonical_name(self):
        return self.parent.canonical_name + u':' + self.name

    @property
    def conforms(self):
        return self._clsobj.conforms

    def _get_full_name(self):
        return u'class ' + self.name

    def _get_mod_and_app(self, t):
        a = t.module.application.name
        m = self.parent.name + '.' + t.module.name
        return m, a

    def _attache_module(self):
        return False

    def _build_schema_tree(self):
        if self._clsobj.is_ref:
            ref = self.parent.get_class(self._clsobj.ref)
            self._clsobj.member = ref._clsobj.member
            self._clsobj.is_ref = False
            ClassModule.__init__(self, self.app, self.parent, self._clsobj)
        Module._build_schema_tree(self)
        b = self.make_schema_builder()
        b._type_params = []
        self._clsrestriction = b.visit(self._clsrestriction_proto)

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

    def _validate_signature(self):
        pass

    def reify(self):
        import caty.jsontools as json
        r = Module.reify(self)
        t, v = json.split_tag(r)
        if 'classes' in v:
            del v['classes']
        return json.tagged(u'_class', v)

