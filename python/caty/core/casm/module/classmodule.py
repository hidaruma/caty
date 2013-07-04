#coding:utf-8
from caty.core.casm.module.basemodule import *
from caty.core.casm.language.ast import *

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
        self._declared = set()
        self.type_params = clsobj.type_args
        for m in clsobj.member:
            m.declare(self)
            self._declared.add(m)
        self._clsrestriction_proto = clsobj.restriction
        self.is_root = False
        self.annotations = clsobj.annotations
        self.count = 0
        self.docstring = clsobj.docstring
        self.defined = True
        self.redifinable = False
        self.refered_module = None

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
        self.refered_modules = list(self._load_refered_modules())
        for cmd in self.proto_ns.values():
            self._attache_class(cmd)
        Module._register_command(self)
        for v in self.command_ns.values():
            for p in v.type_params:
                for p2 in self.type_params:
                    if p.var_name == p2.var_name:
                        throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'Conflicted type parameter: %s<%s>' % (v.canonical_name, p.var_name))
            v.set_arg0_type(self._clsrestriction)
        class_expr_interpreter = ClassExprInterpreter(self)
        class_body = class_expr_interpreter.visit(self._clsobj.expression)
        for m in class_body.member:
            if m in self._declared:
                pass
            else:
                if isinstance(m, CommandNode):
                    if m.module is None:
                        m.module = self
                    if m.application is None:
                        m.application = self.application
                    cursor = m.module.make_profile_builder()
                    self.add_command(cursor.visit(m))
                else:
                    pass

    def _attache_class(self, cmd):
        for modname, refered_module in self.refered_modules:
            if refered_module is None:
                continue
            for name, obj in refered_module.items():
                if self._is_same_name(name, cmd.name):
                    cmd.uri = modname + u'.' + name

    def _is_same_name(self, a, b):
        return a.lower().replace('-', '') == b.lower().replace('-', '')

    def _validate_signature(self):
        pass

    def reify(self):
        import caty.jsontools as json
        r = Module.reify(self)
        t, v = json.split_tag(r)
        if 'classes' in v:
            del v['classes']
        return json.tagged(u'_class', v)

    def _load_refered_modules(self):
        if self.uri is None:
            raise StopIteration()
        if 'python' not in self.uri:
            raise StopIteration()
        for mod in self.uri.python:
            modname = mod.split(u':')[-1]
            if modname == 'caty.core.command':
                yield None, None
            elif self.command_loader and modname in self.command_loader.command_dict:
                yield modname, self.command_loader.command_dict[modname]

class ClassExprInterpreter(object):
    def __init__(self, class_module):
        self.module = class_module

    def visit(self, obj):
        return obj.accept(self)

    def visit_class_body(self, obj):
        return obj

    def visit_class_intersection(self, obj):
        l = obj.left.accept(self)
        r = obj.right.accept(self)
        new = ClassBody([], None)
        if not l.opened:
            throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'closed class')
        if not r.opened:
            throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'closed class')
        for m in l.member:
            new.member.append(m)
        for m in r.member:
            new.member.append(m)
        return new.accept(self)

    def visit_class_use(self, obj):
        r = obj.cls.accept(self)
        new_mem = set([])
        for n, a in obj.names: # ワイルドカードの処理
            if n == '*':
                new_mem = set(r.member)
                break
        for n, a in obj.names:
            if n == '*':
                continue
            for m in r.member:
                if m.name == n:
                    if a is not None:
                        m = m.clone()
                        m.name = a
                    new_mem.add(m)
        r.member = list(new_mem)
        return r

    def visit_class_unuse(self, obj):
        r = obj.cls.accept(self)
        new_mem = set(r.member)
        for n in obj.names: # ワイルドカードの処理
            if n == '*':
                new_mem = []
                break
            for m in r.member:
                if m.name == n:
                    new_mem.remove(m)
        r.member = list(new_mem)
        return r

    def visit_class_close(self, obj):
        n = obj.cls.accept(self)
        n.opened = False
        return n
    
    def visit_class_open(self, obj):
        n = obj.cls.accept(self)
        n.opened = True
        return n

    def visit_class_ref(self, obj):
        return ClassBody([], None)
