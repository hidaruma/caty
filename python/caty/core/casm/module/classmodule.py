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
        self.refered_module = self._load_refered_module()
        if self.refered_module:
            for cmd in self.proto_ns.values():
                self._attache_class(cmd)
        Module._register_command(self)
        for v in self.command_ns.values():
            v.set_arg0_type(self._clsrestriction)

    def _attache_class(self, cmd):
        modname = self.uri.python.split(u':')[-1]
        for name, obj in self.refered_module.__dict__.items():
            if self._is_same_name(name, cmd.name):
                cmd.uri = modname + '.' + name
                if modname not in self.command_loader.command_dict:
                    self.command_loader.command_dict[modname] = {}
                self.command_loader.command_dict[modname][name] = obj

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

    def _load_refered_module(self):
        if self.uri is None:
            return 
        if 'python' not in self.uri:
            return
        modname = self.uri.python.split(u':')[-1]
        if modname == u'caty.core.command':
            return 
        code = u'import %s as _module' % (modname)
        relpath = modname.replace(u'.', u'/')+u'.py'
        g_dict = {}
        abspath = join(self.module._app._physical_path, u'lib', relpath)
        obj = compile(code, relpath, u'exec')
        g_dict[u'__file__'] = abspath
        exec obj in g_dict
        return g_dict[u'_module']

