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

class Provide(object):
    def __init__(self, names):
        self.exports = names

    def declare(self, module):
        module.exports= self.exports

class ModuleName(object):
    def __init__(self, name, annotations, rel, docstring=u'', timing=u'boot'):
        self.name = name
        self.docstring = docstring
        self.annotations = annotations
        self.related = rel
        self.timing = timing

    def declare(self, module):
        if self.name == 'builtin': #ビルトインのみは特別扱い
            if not module.is_builtin:
                raise InternalException("Module name 'builtin' can be used only to Caty builtin module")
        else:
            if self.name != module.canonical_name:
                raise InternalException("Module name $name and path name $path are not matched", name=self.name, path=module.filepath)
        module.docstring = self.docstring
        module.annotations = self.annotations
        module.timing = self.timing
        for r in self.related:
            module.related.add(r)
        if self.timing == u'demand':
            module.loaded = False
            return u'stop'

class ASTRoot(Root):
    def __init__(self, name, type_params, ast, annotation, docstring, kind=None):
        self._name = name
        self._reference_schema = None
        self._type_params = type_params if type_params else []
        self.body = ast
        self.options = None
        self.__annotation = annotation
        self.__docstring = docstring if docstring else u''
        self.kind = None
        self.defined = ast is not None

    #def clone(self):
    #    return TypeLambda(self._name, self._type_params, self.__definition, self.__annotation, self.__docstring)

    @property
    def type_params(self):
        return self._type_params

    @property
    def name(self):
        return self._name

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

class ClassNode(object):
    def __init__(self, name, member, domain, codomain, uri, doc, annotations, type_args):
        self.name = name
        self.member = member
        self.docstring = doc
        self.annotations = annotations
        self.restriction = domain
        self.codomain = codomain
        self.uri = uri
        self.type_args = type_args
        self.defined = True

    def declare(self, module):
        self.module = module
        module.add_class(self)

class FacilityNode(object):
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

    def declare(self, module):
        self.module = module
        module.add_facility(self)

    @property
    def canonical_name(self):
        return self.module.canonical_name + ':' + self.name

class EntityNode(object):
    def __init__(self, name, fname, value, doc, annotations):
        self.name= name
        self.facility_name= fname
        self.user_param = value
        self.docstring = doc
        self.annotations = annotations
        self.defined = fname is not None

    def declare(self, module):
        self.module = module
        module.add_entity(self)

    @property
    def canonical_name(self):
        return self.module.canonical_name + ':' + self.name

class Node(object):
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

class ScalarNode(Scalar, Node):
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
        self.body = node if node else ScalarNode(u'undefined')

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
        self.body = node if node else ScalarNode('any')

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

class EnumNode(Node, Enum):
    reification_type = u'_enum'
    def __init__(self, enum):
        Node.__init__(self)
        #t = type(enum[0])
        #if not all(map(lambda x:t==type(x), enum)):
        #    raise ValueError(t)
        self.enum = enum

    def _reify(self):
        return  {'enum': self.enum if isinstance(self.enum, (list, tuple)) else [self.enum]}

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
        self.wildcard = wildcard if wildcard else ScalarNode(u'never')
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
        self.doc = doc
        self.annotation = annotation
        self.profile_container = None
        self.type_var_names = [n.var_name for n in type_params]
        self.type_params = type_params
        self.type_params_ast = type_params
        self.command_type = command_type
        self.defined = self.reference_to_implementation is not None and self.reference_to_implementation.defined

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
            raise JsonSchemaError('\n'.join(msg))


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
        

class CallPattern(object):
    def __init__(self, opts, args, decl):
        self.opts = opts
        self.args = args
        self.decl = decl

    def clone(self):
        return CallPattern(self.opts, self.args, self.decl.clone())

    def build(self, cursors):
        if self.opts:
            o = self.opts
            for cursor in cursors:
                o = o.accept(cursor)
            self.opt_schema = o
        else:
            self.opt_schema = schemata['null']
        if self.args:
            a = self.args
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
    elif not obj.name in names:
        return obj.name

class CommandDecl(object):
    u"""コマンドの宣言部分の構造体。以下の要素それぞれのリストを持つ構造体クラスである。
    型宣言 type -> type
    大域脱出宣言 throws, breaks
    資源使用宣言 uses, reads, updates
    コマンドURI参照 refers
    """
    def __init__(self, profile, jump, resource):
        self.uri = None # 後で挿入される
        self.profile_ast = profile
        self.profile = None
        self.jump_decl = jump
        self.resource = resource if isinstance(resource, list) else [resource]
        self.__initialized = False

    def clone(self):
        new = CommandDecl(self.profile_ast, self.jump_decl, self.resource)
        new.uri = self.uri
        return new

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
        if isinstance(o, ScalarNode) and o.name == '_' and cursors[0].module.is_class and cursors[0].module._clsobj.codomain:
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

class KindReference(object):
    def __init__(self, name, annotations, docstring=u''):
        self.name = name
        self.annotations = annotations
        self.docstring = docstring

    def declare(self, module):
        self.module = module
        module.add_kind(self)

    def accept(self, visitor):
        return visitor._visit_kind(self)

class TypeParam(object):
    def __init__(self, name, kind, default_type):
        self._name = name
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
                                                    (ScalarNode(u'void'), type if type is not None else schema),
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
        #                                            (type if type is not None else schema, ScalarNode(u'void')),
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
    def __init__(self, name, coltype, keypath, keytype, doc, ann):
        from caty.core.script.parser import ScriptParser
        self.name = name
        self.docstring = doc
        self.annotations = ann
        a = Annotations([])
        for c in ann._annotations:
            a.add(c)
        a.add(Annotation(u'__collection'))
        a.add(Annotation(u'key-getter', keypath))
        if keytype:
            a.add(Annotation(u'key-type', keytype))
        self.type = ASTRoot(name, None, coltype, ann, doc)
        self.command1 = CommandNode('_' + name, 
                                     [CallPattern(None, 
                                                 None, 
                                                 CommandDecl(
                                                    (ScalarNode(u'void'), ScalarNode(u'Classed')),
                                                    [], 
                                                    []
                                                 ), 
                                     )],
                                     CommandURI([(u'python', 'caty.core.command.Dummy')], False),
                                     doc, 
                                     Annotations([Annotation(u'__collection')]),
                                     [])
        self.command2 = CommandNode(name, 
                                     [CallPattern(None, 
                                                 None, 
                                                 CommandDecl(
                                                    (ScalarNode(u'void'), ScalarNode(u'sequence', None, [coltype])),
                                                    [], 
                                                    []
                                                 ), 
                                     )],
                                     CommandURI([(u'python', 'caty.core.command.Dummy')], False),
                                     doc, 
                                     Annotations([Annotation(u'__collection')]),
                                     [])
        self.catyclass = ClassNode(name, [], ScalarNode(u'univ'), ScalarNode(u'univ'), CommandURI([(u'python', 'caty.core.command.DummyClass')], False), None, Annotations([]), [])
        self.entity = FacilityNode(name, None, u'null', ScalarNode(u'null'), {}, None, Annotations([]))

    def declare(self, module):
        self.type.declare(module)
        self.command1.declare(module)
        self.command2.declare(module)
        self.catyclass.declare(module)
        self.entity.declare(module)
