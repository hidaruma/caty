#coding: utf-8
from caty.core.schema import schemata, TypeVariable, NamedSchema, PseudoTag, UnionSchema
from caty.core.schema.base import SchemaBase, TypeVariable, Annotations, Annotation, IntersectionSchema, UpdatorSchema, UnionSchema
from caty.core.schema.array import ArraySchema
from caty.core.schema.object import ObjectSchema
from caty.core.schema.errors import JsonSchemaError
from caty.core.command.profile import CommandProfile, ProfileContainer, ScriptProfileContainer
from caty.core.exception import InternalException
from caty.core.typeinterface import *
import caty.core.runtimeobject as ro
from caty.core.language.util import make_structured_doc
import caty.jsontools as json
from caty.core.spectypes import UNDEFINED

class Provide(object):
    def __init__(self, names):
        self.exports = names

    def declare(self, module):
        module.exports= self.exports

class ModuleName(object):
    def __init__(self, name, annotations, rel, docstring=u'', timing=u'boot', attaches=None):
        self.name = name
        self.docstring = docstring
        self.annotations = annotations
        self.related = rel
        self.timing = timing
        self.attaches = attaches

    def declare(self, module):
        if self.name == 'builtin': #ビルトインのみは特別扱い
            if not module.is_builtin:
                raise InternalException("Module name 'builtin' can be used only to Caty builtin module")
        else:
            if self.name != module.canonical_name:
                raise InternalException("Module name $name and path name $path are not matched", name=self.name, path=module.filepath)
        if not module._fragment and self.attaches:
                raise InternalException("Module $name could not be fragment module", name=self.name, path=module.filepath)
        module.docstring = self.docstring
        module.annotations = self.annotations
        module.timing = self.timing
        module.attaches = self.attaches
        for r in self.related:
            module.related.add(r)
        if self.timing == u'demand':
            module.loaded = False
            return u'stop'

class TypeDefNode(Root):
    is_alias = False
    def __init__(self, name, type_params, attr_params, ast, annotation, docstring, kind=None, defined=True, redifinable=False):
        self._name = name
        self._reference_schema = None
        self._type_params = type_params if type_params else []
        self._attr_params = attr_params if attr_params else []
        self.body = ast if ast else SymbolNode(u'univ')
        self.options = None
        self.__annotation = annotation
        self.__docstring = docstring if docstring else u''
        self.kind = None
        self.defined = defined
        self.redifinable = redifinable

    def clone(self):
        return TypeDefNode(self._name, self._type_params, self._attr_params, self.body, self.__annotation, self.__docstring, self.kind, self.defined, self.redifinable)

    def __repr__(self):
        return 'TypeDefNode<%s>: %s: %s' % (self._type_params, self._name, self.body)

    @property
    def type_params(self):
        return self._type_params

    def name():
        def get(self):
            return self._name
        def set(self, v):
            self._name = v
        return get, set
    name = property(*name())

    @property
    def annotations(self):
        return self.__annotation

    @property
    def docstring(self):
        return self.__docstring

    @property
    def definition(self):
        return self.__definition

    @property
    def canonical_name(self):
        mn = self.module.canonical_name
        name = self.name
        name = '%s:%s' % (mn, name)
        return name

    def declare(self, module):
        self.module = module
        module.add_ast(self)

    def reify(self):
        o = json.tagged(u'type', {
            'name': self._name, 
            'typeParams': [p.reify() for p in self._type_params],
            'typeBody': self.body.reify(),
            'annotation': self.annotations.reify(),
            'document': make_structured_doc(self.docstring),
        })
        if self.options:
            o.value['options'] = self.options
        return o

    @property
    def app(self):
        return self.module.app

from abc import ABCMeta
class ASTRoot(TypeDefNode):
    is_alias = False
    def __init__(self, name, type_params, ast, annotation, docstring, kind=None, defined=True, redifinable=False):
        TypeDefNode.__init__(self, name, type_params, [], ast, annotation, docstring, kind, defined, redifinable)



class ClassNode(object):

    is_alias = False
    def __init__(self, name, expression, domain, codomain, conforms, doc, annotations, type_args, type=u'='):
        self.is_ref = False
        self.name = name
        self.expression = expression
        self.member = []
        self.uri = None
        self.ref = None
        self.docstring = doc
        self.annotations = annotations
        self.restriction = domain
        self.codomain = codomain
        self.type_args = type_args
        self.conforms = conforms
        #if conforms:
        #    self.expression = ClassIntersectionOperator(expression, conforms)
        self.defined = type != u'?='
        self.redifinable = type == u'&='
        self.underlyingtype = None
        self.module = None
        self.__type = type

    def clone(self):
        return ClassNode(self.name, self.expression.clone(), self.restriction, self.codomain, None, self.docstring, self.annotations, self.type_args[:], self.__type)

    def declare(self, module):
        if self.module is None: # 他のモジュールへのアタッチ時には不要な処理
            try:
                self.expression.accept(self) # クラスの定義部のみ摘出する
            except:
                raise
        self.module = module
        if self.redifinable:
            module.add_redif_class(self)
        else:
            module.add_class(self)

    def visit_class_body(self, obj):
        for m in obj.member:
            self.member.append(m)
            if u'__signature' in self.annotations:
                m.defined = False
        self.uri = obj.uri
        obj.visited = True
        return obj

    def visit_class_intersection(self, obj):
        l = obj.left.accept(self)
        r = obj.right.accept(self)
        if isinstance(l, ClassBody):
            return l
        else:
            return r

    def visit_class_use(self, obj):
        return obj.cls

    def visit_class_unuse(self, obj):
        return obj.cls

    def visit_class_close(self, obj):
        return obj.cls

    def visit_class_open(self, obj):
        return obj.cls

    def visit_class_ref(self, obj):
        return None

class ClassBody(object):
    def __init__(self, member, uri):
        self.member = member
        self.uri = uri
        self.opened = True

    def accept(self, visitor):
        return visitor.visit_class_body(self)

    def clone(self):
        r = ClassBody([m.clone() for m in self.member], self.uri)
        r.opened = self.opened
        return self

class ClassReference(object):
    def __init__(self, name, type_params):
        self.name = name
        self.type_params = type_params

    def accept(self, visitor):
        return visitor.visit_class_ref(self)

    def clone(self):
        return ClassReference(self.name, self.type_params[:])

class ClassIntersectionOperator(object):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def accept(self, visitor):
        return visitor.visit_class_intersection(self)

    def clone(self):
        return ClassIntersectionOperator(self.left.clone(), self.right.clone())

class UseOperator(object):
    def __init__(self, names, cls):
        self.names = names
        self.cls = cls

    def accept(self, visitor):
        return visitor.visit_class_use(self)

    def clone(self):
        return UseOperator(self.names, self.cls.clone())

class UnuseOperator(object):
    def __init__(self, names, cls):
        self.names = names
        self.cls = cls

    def accept(self, visitor):
        return visitor.visit_class_unuse(self)

    def clone(self):
        return UnuseOperator(self.names, self.cls.clone())

class CloseOperator(object):
    def __init__(self, cls):
        self.cls = cls

    def accept(self, visitor):
        return visitor.visit_class_close(self)

    def clone(self):
        return CloseOperator(self.cls.clone())

class OpenOperator(object):
    def __init__(self, cls):
        self.cls = cls

    def accept(self, visitor):
        return visitor.visit_class_open(self)

    def clone(self):
        return OpenOperator(self.cls.clone())

class FacilityNode(object):
    is_alias = False
    def __init__(self, 
                 name, 
                 clsname, # ファシリティ実装クラス(Python)
                 sys_param_type, # 抽象エンティティ生成パラメータ型(例: pub = stdmafs("pub"))
                 config_param_type, # ファシリティオブジェクト生成時のパラメータ型
                 indices_param_type, # 具体エンティティ(リクエスター)生成パラメータ型(例: root_dir = pub("/"))
                 doc, annotations):
        self.name= name
        self.clsname= clsname
        self.sys_param_type = sys_param_type
        self.config_param_type = config_param_type
        self.indices_param_type = indices_param_type
        self.docstring = doc
        self.annotations = annotations
        self.defined = True
        self.redifinable = False

    def declare(self, module):
        self.module = module
        module.add_facility(self)

    @property
    def canonical_name(self):
        if self.module.is_class:
            return self.module.canonical_name + '.' + self.name
        else:
            return self.module.canonical_name + ':' + self.name

class EntityNode(object):
    is_alias = False
    def __init__(self, name, fname, value, doc, annotations):
        self.name= name
        self.facility_name= fname
        self.user_param = value
        self.docstring = doc
        self.annotations = annotations
        self.defined = fname is not None
        self.redifinable = False

    def declare(self, module):
        self.module = module
        module.add_entity(self)

    @property
    def canonical_name(self):
        if self.module.is_class:
            return self.module.canonical_name + '.' + self.name
        else:
            return self.module.canonical_name + ':' + self.name

class AliasNode(object):
    is_alias = True
    def __init__(self, name, ref, type):
        self.name = name
        self.reference = ref
        self.type = type
        self.annotations = Annotations([])
        self.docstring = u''
        self.module = None

    def declare(self, module):
        self.module = module
        #if self.type == u'type':
        #    module.add_ast(self)
        #elif self.type == u'command':
        #    module.add_proto_type(self)
        #elif self.type == u'class':
        #    module.add_class(self)

    def clone(self):
        return self

class Node(object):
    is_alias = False
    def __init__(self, options=None):
        self.options = {} if options is None else options
        self.annotations = Annotations([])
        self.docstring = u''
        self.kind = None

    @property
    def optional(self):
        return False

    def apply_type_name(self, t):
        pass

    def reify(self):
        o = self._reify()
        if self.annotations:
            o['annotation'] = self.annotations.reify()
        if self.docstring:
            o['document'] = make_structured_doc(self.docstring)
        o['options'] = self.options
        return json.tagged(self.reification_type, o)

class SymbolNode(Symbol, Node):
    reification_type = u'_scalar'

    def __init__(self, schema_name, options=None, type_args=None):
        Node.__init__(self)
        self.name = schema_name
        self.options = options if options is not None else {}
        self.type_args = type_args if type_args is not None else []

    def _reify(self):
        return {
            'name': self.name, 
            'typeArgs': [t.reify() for t in self.type_args], 
        }


class OperatorNode(Node):
    def __init__(self, node1, node2):
        Node.__init__(self)
        self._left = node1
        self._right = node2

    @property
    def left(self):
        return self._left

    @property
    def right(self):
        return self._right

    def _reify(self):
        return {'left': self.left.reify(), 'right': self.right.reify()}

class UnaryOpNode(Node, UnaryOperator):
    def __init__(self, type, body, type_args=()):
        Node.__init__(self)
        self._operator = type
        self._body = body
        self._type_args = type_args

    def new_node(self, s):
        return UnaryOpNode(self._operator, self._body, self._type_args)

    @property
    def body(self):
        return self._body

    @property
    def operator(self):
        return self._operator

    @property
    def type_args(self):
        return self._type_args

class ExtractorNode(Node, UnaryOperator):
    def __init__(self, path, body):
        Node.__init__(self)
        self.path = path
        self._body = body
        self._operator = u'extract'

    @property
    def body(self):
        return self._body

    @property
    def operator(self):
        return self._operator

    def new_node(self, s):
        return ExtractorNode(self.path, self._body)

class UnionNode(OperatorNode, Union):
    reification_type = u'_union'

class IntersectionNode(OperatorNode, Intersection):
    reification_type = u'_intersection'

class UpdatorNode(OperatorNode, Updator):
    reification_type = u'_updator'

class TaggedNode(Node, Tag):
    reification_type = u'_tag'
    def __init__(self, tag, node):
        Node.__init__(self)
        self._tag = tag
        self.body = node if node else SymbolNode(u'undefined')

    @property
    def tag(self):
        return self._tag

    def _reify(self):
        return {
            'tag': self._tag,
            'body': self.body.reify()
        }

class NamedTaggedNode(TaggedNode):
    def __init__(self, node):
        Node.__init__(self)
        self._tag = None
        self.body = node if node else SymbolNode('any')

class PseudoTaggedNode(Node, PseudoTag):
    def __init__(self, name, value, node):
        Node.__init__(self)
        self._name = name
        self._value = value
        self.body = node

    @property
    def tag(self):
        return self._value

    def reify(self):
        o = self.body.reify()
        t, v = json.split_tag(o)
        p =  json.tagged(u'_pseudoTag', [self._name, self._value])
        if t == '_object':
            v['pseudoTag'] = p
        else:
            v['options']['pseudoTag'] = p
        return o

class ScalarNode(Node, Scalar):
    reification_type = u'_enum'
    def __init__(self, value):
        Node.__init__(self)
        #t = type(enum[0])
        #if not all(map(lambda x:t==type(x), enum)):
        #    raise ValueError(t)
        self.value = value

    def _reify(self):
        return  {'enum': self.value}

class ArrayNode(Node, Array):
    reification_type = u'_array'
    def __init__(self, items, options):
        Node.__init__(self, options)
        self.items = items
        self.options = options
        self.repeat = options.get('repeat', False)
    
    def __iter__(self):
        return iter(self.items)

    def _reify(self):
        items = []
        for v in self.items:
            items.append(v.reify())
        return {
                'items': items,
            }

class BagNode(Node, Bag):
    reification_type = u'_bag'
    def __init__(self, items, options):
        Node.__init__(self, options)
        self.items = items
        self.options = options

    def __iter__(self):
        return iter(self.items)

    def _reify(self):
        return {
            'items': [v.reify() for v in self.items],
        }

class ObjectNode(Node, Object):
    reification_type = u'_object'
    def __init__(self, items=None, wildcard=None, options=None):
        Node.__init__(self, options)
        self.leaves = items if items else {}
        self.wildcard = wildcard if wildcard else SymbolNode(u'undefined')
        self.options = options if options else {}

    def items(self):
        return self.leaves.items()

    def keys(self):
        return self.leaves.keys()
    
    def values(self):
        return self.leaves.values()
    
    def __getitem__(self, key):
        return self.leaves[key]

    def __setitem__(self, key, value):
        raise Exception()

    def _reify(self):
        items = {}
        for k, v in self.leaves.items():
            items[k] = v.reify()
        return {
                'items': items,
                'wildcard': self.wildcard.reify(),
            }

class ExponentNode(Node, Exponent):
    def __init__(self, intype, outtype, argstype, optionstype):
        self._intype = intype
        self._outtype = outtype
        self._argstype = argstype
        self._optstype = optionstype

class OptionNode(Node, Optional):
    reification_type = u'_optional'
    def __init__(self, node):
        self.body = node
        Node.__init__(self, node.options)

    def _reify(self):
        return {'body': self.body.reify()}

    def annotations():
        def get(self):
            return self.body.annotations

        def set(self, v):
            self.body.annotations = v
        return get, set
    annotations = property(*annotations())

class CommandNode(Function):
    is_alias = False
    def __init__(self, name, patterns, uri_or_script, doc, annotation, type_params, command_type=u'command'):
        self.name = name
        self.patterns = patterns
        self.uri = None
        self.script_proxy = None
        self.reference_to_implementation = None
        if isinstance(uri_or_script, CommandURI):
            self.uri = uri_or_script.python
            self.reference_to_implementation = uri_or_script
        else:
            self.script_proxy = uri_or_script
            self.reference_to_implementation = uri_or_script
        self.doc = doc
        self.annotation = annotation
        self.profile_container = None
        self.type_var_names = [n.var_name for n in type_params]
        self.type_params = type_params
        self.type_params_ast = type_params
        self.command_type = command_type
        if uri_or_script is None or (isinstance(uri_or_script, CommandURI) and not uri_or_script.defined):
            self.defined = False
        else:
            self.defined = True
        self.redifinable = False
        self.module = None
        self.application = None
        for p in patterns:
            p.parent = self

    @property
    def implemented(self):
        return not (self.script_proxy is None and self.uri in (None, 'caty.core.command.Dummy'))

    def clone(self):
        r = self.__class__(self.name, 
                           [p.clone() for p in self.patterns], 
                           self.reference_to_implementation, 
                           self.doc, 
                           self.annotation, 
                           self.type_params_ast[:], 
                           self.command_type)
        r.defined = self.defined
        r.redifinable = self.redifinable
        return r

    @property
    def annotations(self):
        return self.annotation

    def declare(self, module):
        self.module = module
        module.add_proto_type(self)
        self.application = module.application

    def check_type_variable(self):
        msg = []
        for p in self.patterns:
            v = p.verify_type_var(self.type_var_names)
            if v is not None:
                msg.append(u'%sは%sで宣言されていない型変数です' % (v, self.name))
                
        if msg:
            throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'\n'.join(msg))


    def reify(self):
        r = {
            'name': self.name,
            'annotation': self.annotation.reify(),
            'typeParams': [p.reify() for p in self.type_params_ast],
            'document': make_structured_doc(self.doc or u''),
        }
        profiles = [pro.reify() for pro in self.patterns]
        r['profiles'] = profiles
        r['exception'] = []
        for jump in self.patterns[0].decl.jump_decl:
            if jump.name == 'throws':
                for e in jump.types:
                    r['exception'].append(e.reify())
        r['resource'] = []
        for t, n in self.patterns[0].decl.get_all_resources():
            r['resource'].append({'facilityName': n.name, 'usageType': t})
        if self.uri:
            if self.uri != 'caty.core.command.Dummy': 
                r['refers'] = self.uri
                t = u'_hostLang'
            else:
                t = u'_stub'
        else:
            r['script'] = self.script_proxy.reify()
            t = u'_script'
        return json.tagged(u'command', json.tagged(t, r))
        
class AssertionNode(CommandNode):
    def __init__(self, name, patterns, uri_or_script, doc, annotation, type_params, command_type=u'command'):
        CommandNode.__init__(self, name or u'', patterns, uri_or_script, doc, annotation, type_params, command_type)

    def declare(self, module):
        module.assertions.append(self)

    def re_declare(self, module):
        self.module = module
        if module.type_params:
            type_params = []
            for tp in self.type_params:
                for tp2 in module.type_params:
                    if tp.var_name == tp2.var_name:
                        break
                else:
                    type_params.append(tp)
            self.type_var_names = [n.var_name for n in type_params]
            self.type_params = type_params
            self.type_params_ast = type_params
        self._reset_assertion_name(module)
        self.application = module.application

    def _reset_assertion_name(self, module):
        import re
        ptn = re.compile(u'_assert_[0-9]+$')
        nums = []
        for a in module.assertions + module.proto_ns.values():
            if '__assert' in a.annotations:
                if ptn.match(a.name):
                    nums.append(int(a.name.rsplit('_', 1)[1]))
        nums.sort()
        if nums:
            max_num = nums[-1] + 1
        else:
            max_num = 1
        usables = []
        for i in range(1, max_num):
            if i not in nums:
                usables.append(i)
        
        if not self.name or module.has_proto_type(self.name):
            if usables:
                self.name = u'_assert_' + str(usables.pop(0))
            else:
                self.name = u'_assert_' + str(max_num)

class CallPattern(object):
    def __init__(self, opts, args, decl):
        self.opts = opts
        self.args = args
        self.decl = decl
        self.opt_schema = None
        self.arg_schema = None
        self.parent = None

    def clone(self):
        r = CallPattern(self.opts, self.args, self.decl.clone())
        r.opt_schema = self.opt_schema
        r.arg_schema = self.arg_schema
        return r

    def build(self, cursors):
        if self.opts:
            o = self.opts
            if self.opt_schema:
                o = self.opt_schema
            for cursor in cursors:
                o = o.accept(cursor)
            self.opt_schema = o
        else:
            self.opt_schema = schemata['null']
        if self.args:
            a = self.args
            if self.arg_schema:
                a = self.arg_schema
            for cursor in cursors:
                a = a.accept(cursor)
            self.arg_schema = a
        else:
            self.arg_schema = schemata['null']
        self.decl.build(cursors)

    def verify_type_var(self, names):
        r = self.decl.verify_type_var(names)
        if r:
            return r
        r = _verify_type_var(self.opt_schema, names)
        if r:
            return r
        r = _verify_type_var(self.arg_schema, names)
        if r:
            return r

    def reify(self):
        r = {
            'input': self.decl.profile_ast[0].reify(),
            'output': self.decl.profile_ast[1].reify(),
        }
        if self.opts:
            r['opts'] = self.opts.reify()
        if self.args:
            r['args'] = self.args.reify()
        return r

def _verify_type_var(obj, names):
    if isinstance(obj, ArraySchema):
        for o in obj:
            x = _verify_type_var(o, names)
            if x:
                return x
    elif isinstance(obj, ObjectSchema):
        for o in obj.values():
            x = _verify_type_var(o, names)
            if x:
                return x
    elif not isinstance(obj, TypeVariable):
        return 
    elif not obj.name in names and not obj._schema and not obj._default_schema:
        return obj.name

class CommandDecl(object):
    u"""コマンドの宣言部分の構造体。以下の要素それぞれのリストを持つ構造体クラスである。
    型宣言 type -> type
    大域脱出宣言 throws, breaks
    資源使用宣言 uses, reads, updates
    コマンドURI参照 refers
    """
    def __init__(self, profile, jump, resource):
        from caty.core.schema import NeverSchema
        self.uri = None # 後で挿入される
        self.profile_ast = profile
        self.profile = None
        self.jump_decl = jump
        self.resource = resource if isinstance(resource, list) else [resource]
        self.__initialized = False
        self.throws = NeverSchema()
        self.signals = NeverSchema()

    def clone(self):
        new = CommandDecl(self.profile_ast, self.jump_decl, self.resource[:])
        new.uri = self.uri
        new.profile = self.profile
        new.throws = self.throws
        new.signals = self.signals
        new._set_initialized(self.__initialized)
        return new

    def _set_initialized(self, v):
        self.__initialized = v

    def get_all_resources(self):
        for res in self.resource:
            t = res[0]
            for r in res[1]:
                yield t, r

    def build(self, cursors):
        from caty.core.casm.language.ast import UnionNode
        from caty.core.schema import NeverSchema
        if self.__initialized:
            return
        i, o = self.profile_ast
        if isinstance(o, SymbolNode) and o.name == '_' and cursors[0].module.is_class and cursors[0].module._clsobj.codomain:
            o = cursors[0].module._clsobj.codomain
        for cursor in cursors:
            i = i.accept(cursor)
            o = o.accept(cursor)
        self.profile = (i, o)

        self.throws = NeverSchema()
        self.signals = NeverSchema()
        for jump in self.jump_decl:
            if jump.types:
                node = reduce(lambda a, b: UnionNode(a, b), jump.types)
                for cursor in cursors:
                    node = node.accept(cursor)
                    self.throws = node
            else:
                node = NeverSchema()
            if jump.only:
                node.annotations.add(Annotation(u'__only'))
            if jump.name == u'signals':
                self.signals = node
            else:
                self.throws = node
        self.__initialized = True

    def verify_type_var(self, names):
        for i in self.profile:
            v = _verify_type_var(i, names)
            if v is not None:
                return v
        return


class FacilityDecl(object):
    def __init__(self, name, param, alias):
        self.name = name
        self.param = param
        self.alias = alias

    def __repr__(self):
        r = []
        r.append(self.name)
        if self.param:
            r.append('("%s")' % self.param)
        if self.alias:
            r.append(' as %s' % self.alias)
        return ''.join(r)

    __str__ = __repr__

class Jump(object):
    def __init__(self, name, types, only, nothing):
        self.name = name
        self.types = types
        self.nothing = nothing
        self.only = only

class CommandURI(dict):
    def __init__(self, types, defined=True):
        for tp, val in types:
            setattr(self, tp, val)
            self[tp] = val
        self.defined = defined

    def clone(self):
        return self

class ClassURI(dict):
    def __init__(self, types, defined=True):
        for tp, val in types:
            setattr(self, tp, val)
            self[tp] = val
            assert(isinstance(val, list)), val
        self.defined = defined

    def clone(self):
        return self

class KindReference(object):
    is_alias = False
    def __init__(self, name, annotations, docstring=u''):
        self.name = name
        self.annotations = annotations
        self.docstring = docstring
        self.optional = False
        self.type_params = []

    def declare(self, module):
        self.module = module
        module.add_kind(self)

    def accept(self, visitor):
        return visitor._visit_kind(self)

class TypeParam(object):
    def __init__(self, name, kind, default_type):
        self._name = name
        self.arg_name = None
        self.var_name = name
        self.kind = kind
        self._default = default_type

    @property
    def default(self):
        return self._default

    @property
    def name(self):
        print '[Error] deprecated property'
        raise

    def __repr__(self):
        return self.var_name + ":" + str(self.kind)

    def reify(self):
        return json.tagged(u'_typeparam', 
        {
            'var_name': self.var_name,
            'kind': self.kind,
            'default': self.default
        })

class NamedTypeParam(TypeParam):
    def __init__(self, arg_name, name, kind, default_type):
        TypeParam.__init__(self, name, kind, default_type)
        self.arg_name = arg_name

    def __repr__(self):
        return self.arg_name + '=' + self.var_name + ":" + str(self.kind)

class ConstDecl(object):
    def __init__(self, name, type, schema, script, doc, ann, value):
        self.name = name
        self.docstring = doc
        self.value = value
        self.annotations = ann
        a = Annotations([])
        for c in ann._annotations:
            a.add(c)
        a.add(Annotation(u'__const'))
        self.__schema = ASTRoot(name, None, schema, a, doc)
        self.__command = CommandNode(name, 
                                     [CallPattern(None, 
                                                 None, 
                                                 CommandDecl(
                                                    (SymbolNode(u'void'), type if type is not None else schema),
                                                    [], 
                                                    []
                                                 ), 
                                     )],
                                     script,
                                     doc, 
                                     a,
                                     [])

    def declare(self, module):
        self.__schema.declare(module)
        self.__command.declare(module)
        module.const_ns[self.name] = self

    def reify(self):
        o = json.tagged(u'const', {
            'name': self.name, 
            'constBody': self.value,
            'annotation': self.annotations.reify(),
            'document': make_structured_doc(self.docstring or u''),
        })
        return o

class AnnotationDecl(object):
    is_class = False
    def __init__(self, name, type, doc, ann):
        from caty.core.script.parser import ScriptParser
        self.name = name
        self.docstring = doc
        self.annotations = ann
        a = Annotations([])
        for c in ann._annotations:
            a.add(c)
        self.type = ASTRoot(name, None, type, ann, doc)
        #a.add(Annotation(u'__annotation'))
        #sp = ScriptParser()
        #script = sp.parse('void')
        #self.__command = CommandNode(name, 
        #                             [CallPattern(None, 
        #                                         None, 
        #                                         CommandDecl(
        #                                            (type if type is not None else schema, SymbolNode(u'void')),
        #                                            [], 
        #                                            []
        #                                         ), 
        #                             )],
        #                             script,
        #                             doc, 
        #                             a,
        #                             [])

    def declare(self, module):
        self.type.module = module
        self.module = module
        module.declare_annotation(self)

    def accept(self, visitor):
        return self.type.accept(visitor)

class CollectionDeclNode(object):
    def __init__(self, name, coltype, mixinclass, keypath, keytype, dbname, doc, ann):
        from caty.core.script.parser import ScriptParser
        self.name = name
        self.dbname = dbname
        self.docstring = doc
        self.annotations = ann
        a = Annotations([])
        for c in ann._annotations:
            a.add(c)
        a.add(Annotation(u'__collection'))
        a.add(Annotation(u'__identified', keypath))
        if keytype:
            a.add(Annotation(u'__id-type', keytype))
        if isinstance(coltype, SymbolNode):
            self.rectype = None
            self.type = ASTRoot(name, None, coltype, a, doc)
        else:
            recname = name+'Record'
            self.rectype = ASTRoot(recname, None, coltype, Annotations([]), None)
            self.type = ASTRoot(name, None, SymbolNode(recname), a, doc)
        self.command1 = CommandNode(name, 
                                     [CallPattern(None, 
                                                 None, 
                                                 CommandDecl(
                                                    (SymbolNode(u'void'), SymbolNode(u'foreign')),
                                                    [], 
                                                    [(u'uses', [FacilityDecl(name, None, u'arg0')])]
                                                 ), 
                                     )],
                                     CommandURI([(u'python', 'caty.core.std.command.collection.GetEntity')], True),
                                     doc, 
                                     Annotations([Annotation(u'__collection')]),
                                     [])
        self.command2 = CommandNode(name, 
                                     [CallPattern(None, 
                                                 None, 
                                                 CommandDecl(
                                                    (SymbolNode(u'void'), SymbolNode(u'sequence', None, [coltype])),
                                                    [], 
                                                    []
                                                 ), 
                                     )],
                                     CommandURI([(u'python', 'caty.core.command.Dummy')], False),
                                     doc, 
                                     Annotations([Annotation(u'__collection')]),
                                     [])
        clsexp = ClassIntersectionOperator(
                                    ClassBody([], ClassURI([(u'python', ['caty.core.command'])], False)),
                                    ClassReference(u'Collection', [SymbolNode(name)]))
        if mixinclass:
            mixinclass.accept(self) # パラメータの_を書き換え
            clsexp = ClassIntersectionOperator(clsexp, mixinclass)
        self.catyclass = ClassNode(name, 
                                  clsexp,
                                  SymbolNode(u'univ'), 
                                  SymbolNode(u'univ'), 
                                  None, None, 
                                  Annotations([Annotation(u'__collection')]), [], u'?=')
        self.entity = lambda m: EntityNode(name, dbname, m.name+':' + name, None, Annotations([]))

    def declare(self, module):
        self.type.declare(module)
        if self.rectype:
            self.rectype.declare(module)
        self.command1.declare(module)
        self.catyclass.declare(module)
        self.entity(module).declare(module)

    def visit_class_intersection(self, obj):
        l = obj.left.accept(self)
        r = obj.right.accept(self)
        if isinstance(l, ClassBody):
            return l
        else:
            return r

    def visit_class_use(self, obj):
        return obj.cls

    def visit_class_unuse(self, obj):
        return obj.cls

    def visit_class_close(self, obj):
        return obj.cls

    def visit_class_open(self, obj):
        return obj.cls

    def visit_class_ref(self, obj):
        vr = _VariableReplacer(self.name)
        for p in obj.type_params:
            p.accept(vr)

from caty.core.typeinterface import TreeCursor
class _VariableReplacer(TreeCursor):
    def __init__(self, name):
        self.target_name = name

    def _visit_root(self, node):
        node.body.accept(self)

    def _visit_symbol(self, node):
        if node.name == u'_':
            node.name = self.target_name

    def _visit_option(self, node):
        node.body.accept(self)

    def _visit_scalar(self, node):
        pass

    def _visit_unary_op(self, node):
        node.body.accept(self)

    def _visit_object(self, node):
        for k, v in node.items():
            v.accept(self)
        node.wildcard.accept(self)

    def _visit_array(self, node):
        for c in node:
            c.accept(self)

    def _visit_bag(self, node):
        r = []
        for c in node:
            c.accept(self)

    def _visit_intersection(self, node):
        node.left.accept(self)
        node.right.accept(self)

    def _visit_union(self, node):
        node.left.accept(self)
        node.right.accept(self)

    def _visit_updator(self, node):
        node.left.accept(self)
        node.right.accept(self)

    def _visit_tag(self, node):
        t = node.tag
        node.body.accept(self)
        if isinstance(t, unicode):
            pass
        elif isinstance(t, (SchemaBase, Node)):
            t.accept(self)

    def _visit_pseudo_tag(self, node):
        node.body.accept(self)

    def _visit_kind(self, node):
        pass

    def _visit_exponent(self, node):
        pass

    def _visit_type_function(self, node):
        node.typename.accept(self)

class TypeFunctionNode(TypeFunction, SchemaBase):
    def __init__(self, funcname, typename):
        self.funcname = funcname
        self.typename = SymbolNode(typename) if isinstance(typename, basestring) else typename
        SchemaBase.__init__(self)
        self._module = None
        self._type = u'<%s>' % funcname

    def _deepcopy(self, ignore):
        return TypeFunctionNode(self.funcname, self.typename)

    @property
    def module(self):
        return self._module

    @property
    def type(self):
        return self._type

class NamedParameterNode(SchemaBase):
    def __init__(self, name, schema):
        SchemaBase.__init__(self)
        self._name = name
        self._schema = schema
        self._annotations = Annotations([])
        self._docstring = u''

    @property
    def name(self):
        return self._name

    @property
    def body(self):
        return self._schema

    @property
    def options(self):
        return self._schema.options

    def validate(self, value, path=None):
        if not (value is UNDEFINED):
            self._schema.validate(value, path)

    def convert(self, value):
        if not (value is UNDEFINED):
            return self._schema.convert(value)

    @property
    def optional(self):
        return False

    def _clone(self, *args, **kwds):
        return NamedParameterNode(self.name, self.body.clone(*args, **kwds))

    def _deepcopy(self, checked):
        return NamedParameterNode(self.name, self.body.clone(checked))

    @property
    def type(self):
        return self.body.type

    @property
    def tag(self):
        return self.body.tag

    def accept(self, visitor):
        if not hasattr(visitor, '_visit_named_parameter'):
            return NamedParameterNode(self.name, self.body.accept(visitor))
        else:
            return visitor._visit_named_parameter(self)

    def __repr__(self):
        return '%s=%s' % (self.name, repr(self._schema))

