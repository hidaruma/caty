#coding:utf-8
from caty.core.casm.module.basemodule import *
from caty.core.casm.language.ast import *
from caty.core.casm.cursor.base import check_named_type_param

def error_wrapper(f):
    def _(self, *args, **kwds):
        try:
            return f(self, *args, **kwds)
        except:
            self.application.cout.writeln('NG')
            print '    [ERROR]', u'%s::%s (%s)' % (self._app.name, self.canonical_name, self.type)
            raise
    return _

class ClassModule(Module):
    u"""
    クラスは名前空間を構成するというその機能においてモジュールに近い。
    そのため、実装はモジュールとほぼ同等とする。
    """
    is_class = True
    is_alias = False
    def __init__(self, app, parent, clsobj, auto_decl=True):
        Module.__init__(self, app, parent)
        self._type = u'class'
        self.command_loader = parent.command_loader
        self._name = clsobj.name
        self._clsobj = clsobj
        self._declared = set()
        self.type_params = clsobj.type_args
        if auto_decl:
            for m in clsobj.member:
                m.declare(self)
                self._declared.add(m.name)
        self._clsrestriction_proto = clsobj.restriction
        self.is_root = False
        self.annotations = clsobj.annotations
        self.count = 0
        self.docstring = clsobj.docstring
        self.defined = True
        self.redifinable = False
        self.refered_module = None
        self.module_and_type_param_map = {}

    def clone(self):
        r = ClassModule(self.app, self.parent, self._clsobj.clone(), False)
        return r

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

    def get_origin_module_type_params(self, name):
        return self.module_and_type_param_map[name]

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
        try:
            refered_modules = list(self._load_refered_modules(self))
            for cmd in self.proto_ns.values():
                self._attache_class(cmd, refered_modules)
        except:
            print '    [ERROR]', u'%s::%s' % (self._app.name, self.canonical_name)
            raise
        Module._register_command(self)
        try:
            for v in self.command_ns.values():
                for p in v.type_params:
                    for p2 in self.type_params:
                        if p.var_name == p2.var_name:
                            throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'Conflicted type parameter: %s<%s>' % (v.canonical_name, p.var_name))
                v.set_arg0_type(self._clsrestriction)
            class_expr_interpreter = ClassExprInterpreter(self)
            class_body = class_expr_interpreter.visit(self._clsobj.expression)
            if self._clsobj.conforms:
                conform_cls = class_expr_interpreter.visit(self._clsobj.conforms)
            else:
                conform_cls = None
            for m in class_body.member:
                if m.name in self._declared:
                    pass
                else:
                    if isinstance(m, AssertionNode):
                        m.re_declare(self)
                    if isinstance(m, CommandNode):
                        self.add_proto_type(m)
                        if m.module is None:
                            m.module = self
                        if m.application is None:
                            m.application = self.application

                        try:
                            refered_modules = list(self._load_refered_modules(class_body))
                            self._attache_class(m, refered_modules)
                        except:
                            print '    [ERROR]', u'%s::%s' % (self._app.name, self.canonical_name)
                            raise
                        cursor = m.module.make_profile_builder()
                        self.add_command(cursor.visit(m))
                    else:
                        pass
            if not conform_cls:
                return
            for m in conform_cls.member:
                if isinstance(m, AssertionNode):
                    m.re_declare(self)
                if isinstance(m, CommandNode):
                    self.add_proto_type(m)
                    if m.module is None:
                        m.module = self
                    if m.application is None:
                        m.application = self.application

                    try:
                        refered_modules = list(self._load_refered_modules(conform_cls))
                        self._attache_class(m, refered_modules)
                    except:
                        print '    [ERROR]', u'%s::%s' % (self._app.name, self.canonical_name)
                        raise
                    cursor = m.module.make_profile_builder()
                    if not m.implemented:
                        if m.name not in self._declared:
                            print '    [Warning]', u'%s is not implemented at %s' % (m.name, self.canonical_name)
                        continue # XXX: 本来ならシグネチャのチェック
                    o = cursor.visit(m)
                    self.add_command(o)
                else:
                    pass
        except:
            print '    [ERROR]', u'%s::%s' % (self._app.name, self.canonical_name)
            raise

    def _attache_class(self, cmd, refered_modules):
        for modname, refered_module in refered_modules:
            if refered_module is None:
                continue
            for name, obj in refered_module.items():
                if u'__origin_module' in cmd.annotations:
                    return
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

    def _load_refered_modules(self, cls):
        if cls.uri is None:
            raise StopIteration()
        if 'python' not in cls.uri:
            raise StopIteration()
        for mod in cls.uri.python:
            modname = mod.split(u':')[-1]
            if modname == 'caty.core.command':
                yield None, None
            elif self.command_loader and self.command_loader.has_module(modname):
                yield modname, self.command_loader.get_module(modname)

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
        new = ClassBody([], ClassURI([('python', ['caty.core.command'])], False))
        if not l.opened:
            throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'closed class')
        if not r.opened:
            throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'closed class')
        for m in l.member:
            new.member.append(m)
        for m in r.member:
            new.member.append(m)
        self._append_uri(new, l)
        self._append_uri(new, r)
        return new.accept(self)

    def _append_uri(self, dest, src):
        if src.uri:
            us = src.uri.get('python')
            for u in us:
                if u not in dest.uri['python']:
                    dest.uri['python'].append(u)
            if len(dest.uri['python']) > 1 and 'caty.core.command' in dest.uri['python']:
                dest.uri['python'].remove('caty.core.command')
                dest.uri.defined = True

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
                    for i in new_mem:
                        if i.name == m.name:
                            break
                    else:
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
        from caty.core.casm.language.ast import ASTRoot, CommandNode
        from caty.core.script.builder import ClassModuleWrapper
        COLLECTION_COMMANDS = set([u'lookup', u'get', u'belongs', u'exists', u'keys', u'all', u'insert', u'replace', u'delete', u'count', u'dump', u'delete-all', u'list', u'mget', u'multi-get', u'next-index', u'poke', u'set', u'choose'])
        try:
            cls = self.module.get_class(obj.name)
        except:
            print u'[Error]', self.module.canonical_name
            raise
        tp = []
        member = []
        origin_module = cls.module
        default_named_params = []
        check_named_type_param(cls.type_params, obj.type_params)
        for p in [a for a in cls.type_params if isinstance(a, NamedTypeParam)]:
            for p2 in [b for b in obj.type_params if isinstance(b, NamedParameterNode)]:
                if p.arg_name == p2.name:
                    sb = self.module.make_schema_builder()
                    sb._type_params = []
                    rr = self.module.make_reference_resolver()
                    tn = self.module.make_type_normalizer()
                    t = tn.visit(p2.accept(sb).accept(rr))
                    x = TypeVariable(p.var_name, [], p.kind, p.default, {}, self.module)
                    x._schema = t
                    tp.append(x)
                    break
            else:
                default_named_params.append(TypeVariable(p.var_name, [], p.kind, p.default, {}, self.module))
        for p ,p2 in zip([a for a in cls.type_params if not isinstance(a, NamedTypeParam)], 
                         [b for b in obj.type_params if not isinstance(b, NamedParameterNode)]):
            sb = self.module.make_schema_builder()
            sb._type_params = []
            rr = self.module.make_reference_resolver()
            tn = self.module.make_type_normalizer()
            sb._root_name = cls.name
            rr._root_name = cls.name
            tn._root_name = cls.name
            t = tn.visit(p2.accept(sb).accept(rr))
            x = TypeVariable(p.var_name, [], p.kind, p.default, {}, self.module)
            x._schema = t
            tp.append(x)
        exp = cls._clsobj.expression.clone()
        ClassExpTypeVarApplier(tp, default_named_params).visit(exp)
        for m in exp.accept(self).member:
            if isinstance(m, ASTRoot):
                print m
            elif isinstance(m, CommandNode):
                m = m.clone()
                m.module = self.module
                if isinstance(m, AssertionNode):
                    if m.name in self.module.command_ns:
                        m.name = u''
                    if m not in self.module.assertions:
                        self.module.assertions.append(m)
                if m.script_proxy:
                    m.script_proxy = m.script_proxy.clone()
                    m.reference_to_implementation = m.script_proxy
                    ScriptTypeVarApplier(tp, default_named_params, cls).visit(m.script_proxy)
                for ptn in m.patterns:
                    try:
                        self.__build_profile(ptn, cls, tp, m.type_params, m.name)
                    except:
                        print 'debug', tp
                        print 'debug', cls.type_params
                        print 'debug', [p.name if isinstance(p, ScalarNode) else p for p in obj.type_params]
                        raise
                    if u'__collection' in self.module.annotations and m.name in COLLECTION_COMMANDS:
                        ptn.decl.resource.append((u'uses', [FacilityDecl(self.module.name, None, u'arg0')]))
                if origin_module and origin_module != self.module and origin_module.name != u'collection':
                    m.annotations.add(Annotation(u'__origin_module', origin_module.name))

                member.append(m)
            else:
                member.append(m)
        return ClassBody(member, cls.uri)

    def __build_profile(self, pat, cls, tp, type_params, cmdname):
        from caty.core.casm.language.ast import FacilityDecl
        from caty.core.casm.cursor.base import SchemaBuilder
        from caty.core.casm.cursor.resolver import ReferenceResolver
        from caty.core.casm.cursor.typevar import TypeVarApplier
        from caty.core.casm.cursor.normalizer import TypeNormalizer
        rr = ReferenceResolver(cls)
        params = []
        # 型パラメータのデフォルト値を設定
        for p in type_params:
            schema = TypeVariable(p.var_name, [], p.kind, p.default, {}, cls)
            v = schema.accept(rr)
            if isinstance(v, TypeVariable):
                params.append(v)
        sb = SchemaBuilder(cls)
        sb._type_params = params
        pat.build([sb, rr])
        names = [reduce_type_var_nest(q).var_name for q in tp] + [reduce_type_var_nest(p).var_name for p in type_params] + [t.var_name for t in cls.type_params]
        e = pat.verify_type_var(names)
        if e:
            raise CatyException(u'SCHEMA_COMPILE_ERROR', 
                                u'Undeclared type variable `$name` in the definition of $this',
                                this=cmdname, name=e)
        tc = TypeVarApplier(cls)
        tn = TypeNormalizer(cls)
        tc.real_root = False
        tc._init_type_params(Dummy(tp))
        pat.opt_schema = tn.visit(pat.opt_schema.accept(tc))
        tc._init_type_params(Dummy(tp))
        pat.arg_schema = tn.visit(pat.arg_schema.accept(tc))
        p = pat.decl.profile
        new_prof = [None, None]
        tc = TypeVarApplier(cls)
        tc._init_type_params(Dummy(tp))
        new_prof[0] = tn.visit(p[0].accept(tc)) 
        tc = TypeVarApplier(cls)
        tc._init_type_params(Dummy(tp))
        new_prof[1] = tn.visit(p[1].accept(tc))
        pat.decl.profile = tuple(new_prof)

                
class Dummy(object):
    def __init__(self, params):
        self.type_params = params

class ScriptTypeVarApplier(object):
    def __init__(self, type_params, default_named_params, class_module):
        self.type_params = type_params
        self.class_module = class_module
        self.default_named_params = default_named_params

    def visit(self, node):
        node.accept(self)

    def _visit_command(self, node):
        l = len(node.type_args)
        for i, t in enumerate(node.type_args):
            for p in self.type_params:
                if p.var_name == t.name:
                    node.type_args[i] = TypeVariable(p.var_name, [], p.kind, p.default, {}, self.class_module)
                    node.type_args[i]._schema = p._schema
                    break
            for n in self.default_named_params:
                if n.var_name == t.name:
                    scm = self.class_module.get_type(n.default)
                    node.type_args[i] = TypeVariable(n.var_name, [], n.kind, n.default, {}, self.class_module)
                    node.type_args[i]._schema = scm
                    break

class ClassExpTypeVarApplier(object):
    def __init__(self, type_params, default_named_params):
        self.type_params = type_params
        self.default_named_params  = default_named_params
     
    def visit_class_body(self, obj):
        pass

    def visit_class_intersection(self, obj):
        obj.left.accept(self)
        obj.right.accept(self)

    def visit_class_ref(self, obj):
        if self.type_params:
            obj.type_params = self.type_params
        #for p in reversed(self.default_named_params):
        #    obj.type_params.insert(0, NamedParameterNode(p.var_name, p.default))

    def visit_class_use(self, obj):
        obj.cls.accept(self)
    
    def visit_class_unuse(self, obj):
        obj.cls.accept(self)
    
    def visit_class_open(self, obj):
        obj.cls.accept(self)

    def visit_class_close(self, obj):
        obj.cls.accept(self)

    def visit(self, node):
        node.accept(self)

def reduce_type_var_nest(obj):
    if isinstance(obj, TypeVariable):
        if isinstance(obj._schema, TypeVariable):
            return reduce_type_var_nest(obj._schema)
    return obj

