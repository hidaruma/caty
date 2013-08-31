#coding: utf-8
from caty.core.resource import Resource
from caty.jsontools import TaggedValue, tag, tagged, untagged, obj2path
from caty.util import merge_dict, error_to_ustr, bind2nd, to_unicode
from caty.core.schema.errors import *
import caty
import caty.core.runtimeobject as ro
from caty.core.typeinterface import *
from caty.core.spectypes import UNDEFINED, INDEF, Indef

import copy
import random
from decimal import Decimal
from caty.jsontools import TaggedValue, TagOnly, prettyprint
from types import NoneType

class SchemaBase(Resource):
    u"""あらゆるスキーマクラスのベースクラス。
    スキーマオブジェクトは以下の振る舞いについて何らかの定義がなされていなければならない。

    * validate(v): 値の検証。実際には _validate をオーバーライドすることが殆どである。
    * convert(v): 値の変換。実際には _convert をオーバーライドすることが殆どである。
    * name: スキーマの名称。デフォルトでは type と同じ値を返す。
    * definition: スキーマの定義名。型変数を用いるスキーマの場合、 name<型変数名> の形になる。デフォルトでは name と同じ。
    * type: スキーマの型名。デフォルトではエラーなので必ずオーバーライドすること。
    * union(s): スキーマのユニオン。デフォルトのままで問題ないはずである。
    * intersect(s): スキーマのインターセクション。 object と型変数以外は未定義であるべきである。
    * update(s): スキーマの合成。 object と型変数以外は未定義であるべきである。
    * _clone(*args, **kwds): 新たなスキーマオプションと型変数へのスキーマ割り当てによるクローン。
    * apply(type_vars): 型変数の適用。型変数適用後のスキーマオブジェクトを返す。デフォルトではただ自身を返す。

    スキーマ固有のオプションは全てコンストラクタ、あるいは clone に対して辞書で渡される。
    また、このオプションは全て read-only なプロパティとして外部からアクセス可能であるべきである。

    スキーマの名称と型名と定義名の違いに注意すること。組み込み型は三つが一致するが、非組み込み型は異なる。
    例えば以下の場合、 restrictedString はスキーマの名称及び定義名であるが、型名は string であり、
    同様に list はスキーマの名称であるが定義名は list<_T> であり、型名は array である。

    {{{
    type restrictedString = string(maxLength=255);
    type list<T> = [T*];
    }}}

    ユーザ定義型はオプションを取ることができず、組み込み型は型変数を取る事ができない。
    ユーザ定義型も上記の restrictedString のように型変数を定義時に宣言していない場合、
    型変数を受け取る事ができない。

    また、スキーマオブジェクトは以下の規約に沿って動作しなければならない。

    * 引数無しでインスタンス化できる
    * 引数無しで _clone メソッドが呼べる
    * 引数無しの clone が呼ばれた場合、あるいは引数の値が全て空の場合単に自身を返す
    * インスタンス化された後は常に不変オブジェクトとして振る舞う

    """

    __options__ = set(['remark', 'minCount', 'maxCount', 'subName'])

    def __init__(self, options=None):
        Resource.__init__(self)
        self._options = options if options else {}
        self._annotations = Annotations([])
        self._verify_option()
        self._docstring = u''

    def annotations():
        def _get(self):
            return self._annotations
        def _set(self, v):
            assert isinstance(v, Annotations)
            self._annotations = v
        return _get, _set
    annotations = property(*annotations())

    def docstring():
        def _get(self):
            assert isinstance(self._docstring, unicode)
            return self._docstring
        def _set(self, v):
            assert isinstance(v, unicode)
            self._docstring = v
        return _get, _set
    docstring = property(*docstring())

    def _verify_option(self):
        d = set(self._options.keys()) - self.__class__.__options__
        if d:
            raise JsonSchemaError(dict(msg=u'Undefined schema attribute: $name', name=(', '.join(d))))

    @property
    def optional(self):
        return False
    
    @property
    def dereferenced(self):
        return self

    @property
    def app(self):
        return None

    @property
    def is_extra_tag(self):
        return False

    def remarks():
        def _get(self):
            return self._options.get('remark', False)
        def _set(self, v):
            self._options['remark'] = v
        return _get, _set
    remarks = property(*remarks())

    def minCount():
        def _get(self):
            return self._options.get('minCount', 1)
        def _set(self, v):
            self._options['minCount'] = v
        return _get, _set
    minCount = property(*minCount())

    def maxCount():
        def _get(self):
            return self._options.get('maxCount', 1)
        def _set(self, v):
            self._options['maxCount'] = v
        return _get, _set
    maxCount = property(*maxCount())

    def subName():
        def _get(self):
            return self._options.get('subName', None)
        def _set(self, v):
            self._options['subName'] = v
        return _get, _set
    subName = property(*subName())


    def format():
        def _get(self):
            return self._options.get('format', u'')
        def _set(self, v):
            self._options['format'] = v
        return _get, _set
    format = property(*format())

    def fill_default(self, value):
        # object でのみ意味のあるメソッドだが、全スキーマで定義しておく
        return value

    def normalize(self, queue):
        u"""スキーマの正規化。
        正規化処理は
        * ?をユニオンの最外に移動
        * ++と&の消去
        * neverの消去(never|integerは単にintegerとなる)
        スカラー型や参照型の場合、単にoptionalでなくなればよい。
        normalizeは破壊的変更を伴うが、never消去規則のために戻り値を持つこととする。
        """
        return self

    def _get_resource_type():
        return 'schema'

    @property
    def options(self):
        return copy.deepcopy(self._options)

    @property
    def name(self):
        return self.type

    @property
    def definition(self):
        return self.type

    def _get_canonical_name(self):
        return self.name

    @property
    def canonical_name(self):
        return self.name

    @property
    def type(self):
        raise NotImplementedError(str(self.__class__) + '#type')

    @property
    def type_vars(self):
        return []

    @property
    def type_args(self):
        return []

    @property
    def tag(self):
        raise NotImplementedError(str(self.__class__) + '#tag')

    def convert(self, value):
        u"""convert メソッドの実装。
        実際の処理は _convert メソッドで行い、その結果を検証した結果を返すことになる。
        デフォルトの _convert の実装では何もせずに値をそのまま返す。
        """
        try:
            self.validate(value)
        except:
            try:
                r = self._convert(value)
            except JsonSchemaError, e:
                raise
            except Exception, e:
                raise JsonSchemaError(dict(msg=u'Unexpected error: $error', error=error_to_ustr(e)))
        else:
            return value
        self.validate(r)
        return r

    def _convert(self, value):
        return value

    def clone(self, checked, *args, **kwds):
        u"""スキーマのクローン。
        いわゆるプロトタイプパターン。
        """
        #if self._empty(args) and self._empty(kwds):
        if not args and not kwds:
            return self._deepcopy(checked)
        n = self._clone(checked, *args, **kwds)
        n.annotations = self.annotations
        return n

    def _empty(self, obj):
        if obj is None:
            return True
        if obj == []:
            return True
        if obj == {}:
            return True
        if isinstance(obj, (list, tuple)):
            return all([self._empty(x) for x in obj])
        if isinstance(obj, dict):
            return all([self._empty(x) for x in obj.values()])
        return False

    def _clone(self, checked, *args, **kwds):
        raise NotImplementedError()

    def validate(self, value, path=None):
        u"""スキーマ処理のベース。
        タグ付きの値は基本的に共通でエラーとし、タグを扱う場合はこのメソッドをサブクラスでオーバーライドする。
        """
        if isinstance(value, TaggedValue):
            raise JsonSchemaError(dict(msg=u'Tagged value is passed: $tag', tag=tag(value)))
        if self.optional and (value is caty.UNDEFINED):
            return
        self._validate(value)

    def to_tagged(self, tag):
        return TagSchema(tag, self)

    def apply(self, type_vars):
        pass

    def resolve_reference(self):
        pass

    def has_attribute(self, k):
        o = self.__class__.__dict__.get(k, None)
        if o:
            if isinstance(o, SchemaAttribute):
                return True
        return False

    def pp(self):
        return 'type %s = %s' % (self.name, self.dump(0, []))

    def check_type_variable(self):
        try:
            self._check_type_variable([t.name for t in self.type_vars], [])
        except KeyError, e:
            raise JsonSchemaError(dict(msg=u'Undeclared type variable at $this: $name', name=', '.join(e.args), this=self.name))
        except RuntimeError, e:
            print '[ERROR]', self.name
            raise e

    def _check_type_variable(self, declared_type_vars, checked):
        pass

    def _dump_option(self):
        o = u''
        minc = self.minCount
        maxc = self.maxCount
        if minc is not None and maxc is not None:
            if minc != 1 and maxc != 1:
                o += u'{%d, %d}' % (minc, maxc)
        elif maxc is not None:
            o += u'{0, %d}' % (maxc)
        elif minc is not None:
            o += u'{%d,}' % (minc)
        return o

    def is_never(self):
        return self.type != 'never'

    def set_reference(self, referent):
        pass

    def __or__(self, another):
        return UnionSchema(self, another)

    def __and__(self, another):
        if isinstance(another, (TypeReference, NamedSchema)):
            another = another.body
        return IntersectionSchema(self, another)

    def __pow__(self, another):
        if isinstance(another, (TypeReference, NamedSchema)):
            another = another.body
        return UpdatorSchema(self, another)

class PseudoTag(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def exclusive(self, another):
        return self.name == another.name and self.value != another.value

    def defined(self):
        return self.name

    def __str__(self):
        return '%s=%s' % (self.name, repr(self.value))

class SchemaAttribute(property):
    def __init__(self, name, default=None):
        property.__init__(self, lambda obj: obj.options.get(name, default), lambda obj, v: obj._options.__setitem__(name, v))

attribute = SchemaAttribute


class OperatorSchema(SchemaBase):
    def __init__(self, a, b, options=None):
        self._left = a
        self._right = b
        SchemaBase.__init__(self, options)

    @property
    def left(self):
        return self._left

    @property
    def right(self):
        return self._right

class UnionSchema(OperatorSchema, Union):
    u"""union 型に対応するスキーマ。
    union 型は二つのスキーマによってインスタンス化され、
    それらのスキーマのいずれか一方に適合するデータであれば妥当なデータとみなす。
    両方のスキーマで妥当性検証に失敗したときのみがエラーである。
    """

    def operate(self, l, r):
        return l | r

    def validate(self, value, path=None):
        u"""union 型に対するスキーマ適用処理。
        """
        if path is None:
            path = set()
        if self.optional and (value is caty.UNDEFINED):
            return
        try:
            self._left.validate(value, path)
        except JsonSchemaError, e1:
            try:
                self._right.validate(value, path)
            except JsonSchemaError, e2:
                raise JsonSchemaUnionError(e1, e2)
            else:
                return
        else:
            return

    def intersect(self, another):
        if isinstance(another, UnionSchema):
            x, y = another.branch
            try:
                n = (x & self._left) | (y & self._right)
            except Exception, e:
                n = (y & self._left) | (x & self._right)
        else:
            n = (self._left & another) | (self._right & another)
        return n

    def convert(self, value):
        try:
            return self._left.convert(value)
        except JsonSchemaError, e1:
            try:
                return self._right.convert(value)
            except JsonSchemaError, e2:
                raise JsonSchemaError(dict(msg='Failed to convert to union type' + ':' + error_to_ustr(e1) + '/' + error_to_ustr(e2)))


    def dump(self, depth=0, node=[]):
        v = self._left.dump(depth, node) + ' | ' + self._right.dump(depth, node)
        return v

    def clone(self, checked=None, options={}):
        if not options:
            options = {}
        s = UnionSchema(self._left.clone(checked), self._right.clone(checked))
        if self.optional or options.get('optional', False):
            s.optional = True
        s.annotations = self.annotations
        return s

    def apply(self, type_vars):
        self._left.apply(type_vars)
        self._right.apply(type_vars)

    @property
    def type(self):
        return '__union__'

    @property
    def name(self):
        return u'%s | %s' % (self._left.name, self._right.name)

    @property
    def definition(self):
        return u'%s | %s' % (self._left.definition, self._right.definition)

    @property
    def branch(self):
        return self._left, self._right

    @property
    def type_vars(self):
        return self._left.type_vars + self._right.type_vars

    def _check_type_variable(self, declared_type_vars, checked):
        if self.canonical_name in checked: return
        checked.append(self.canonical_name)
        self._left._check_type_variable(declared_type_vars, checked)
        self._right._check_type_variable(declared_type_vars, checked)

    def set_reference(self, referent):
        a = self._left.set_reference(referent)
        b = self._right.set_reference(referent)
        if a or b:
            return (a if a else self._left) | (b if b else self._right)

    def resolve_reference(self):
        self._left.resolve_reference()
        self._right.resolve_reference()

    def normalize(self, queue):
        o = self._left.optional or self._right.optional
        self._left = self._left.normalize(queue)
        self._right = self._right.normalize(queue)
        self._options['optional'] = o
        if self._left.type != 'never':
            if self._right.type != 'never':
                return self
            else:
                return self._left
        else:
            if self._right.type != 'never':
                return self._right
            else:
                return NeverSchema()

class IntersectionSchema(OperatorSchema, Intersection):
    u"""インターセクションスキーマ。
    通常、インターセクションは即座に計算されて IntersectionSchema でないスキーマになる。
    ただし、型変数を含めた演算は後の型解析のステップにならない限りは計算できない。
    実際にパイプラインが構築されて型解析が行われた場合、このスキーマは消滅して他のスキーマで置換される。
    """

    def operate(self, l, r):
        return l & r

    @property
    def type(self):
        return '__intersection__'

    @property
    def name(self):
        return u'%s & %s' % (self._left.name, self._right.name)

    def clone(self, checked, *args, **kwds):
        s = IntersectionSchema(self._left.clone(checked), self._right.clone(checked))
        s.annotations = self.annotations
        s._options = self._options
        return s

    @property
    def definition(self):
        return u'%s & %s' % (self._left.definition, self._right.definition)

    @property
    def type_vars(self):
        return self._left.type_vars + self._right.type_vars

    def set_reference(self, referent):
        self._left.set_reference(referent)
        self._right.set_reference(referent)

    def resolve_reference(self):
        self._left.resolve_reference()
        self._right.resolve_reference()

class UpdatorSchema(OperatorSchema, Updator):
    u"""型アップデータスキーマ。
    インターセクション同様、型変数を含んだアップデート演算に対応するためのスキーマである。
    """

    def operate(self, l, r):
        return l ** r

    @property
    def type(self):
        return '__merging__'

    @property
    def name(self):
        return u'%s ++ %s' % (self._left.name, self._right.name)

    @property
    def definition(self):
        return u'%s ++ %s' % (self._left.definition, self._right.definition)

    def clone(self, checked=None, *args, **kwds):
        s = UpdatorSchema(self._left.clone(checked), self._right.clone(checked))
        s.annotations = self.annotations
        s._options = self.options
        return s

    def set_reference(self, referent):
        self._left.set_reference(referent)
        self._right.set_reference(referent)
    
    @property
    def type_vars(self):
        return self._left.type_vars + self._right.type_vars

    def resolve_reference(self):
        self._left.resolve_reference()
        self._right.resolve_reference()

_builtin_tags = [
    u'integer',
    u'number',
    u'string',
    u'binary',
    u'boolean',
    u'array',
    u'object',
    u'any',
    u'null',
    u'void',
    u'never',
    u'enum',
    u'undefined',
    u'foreign',
    u'indef',
    ]

class TagSchema(SchemaBase, Tag):
    u"""タグ付き union で使われるスキーマ。
    通常のスキーマに tag プロパティが付いたものである。
    """
    def __init__(self, tag, schema, options=None):
        self.__tag = tag
        self.__schema = schema
        assert isinstance(schema, SchemaBase), schema
        SchemaBase.__init__(self, self.__schema.options)
        self.annotations = schema.annotations

    @property
    def body(self):
        return self.__schema

    def clone(self, checked=None, *args, **kwds):
        s = TagSchema(self.__tag, self.__schema.clone(checked, *args, **kwds))
        s.annotations = self.annotations
        return s

    @property
    def tag(self):
        return self.__tag

    def validate(self, value, path=None):
        if self.optional and (value is caty.UNDEFINED):
            return
        t = tag(value)
        if isinstance(self.tag, SchemaBase):
            self.tag.validate(t, path)
        elif t != self.tag:
            if self.tag == '*!' and t in _builtin_tags:
                raise JsonSchemaError(dict(msg='Wildcard tag is not able to used to builtin types: $type', type=t))
            if self.tag not in ('*', '*!'):
                raise JsonSchemaError(dict(msg='Unmatched tag: $another, $this', this=self.tag, another=t))
        self.__schema.validate(untagged(value), path)

    def intersect(self, another):
        if self._unmatched(another):
            return NeverSchema()

        nt = self.tag if self.tag not in ('*!', '*') else another.tag
        return TagSchema(nt, self._dereference(self.__schema) & self._dereference(another))

    def _unmatched(self, another):
        return not (self.tag == another.tag 
                    or (self.tag == '*!' and another.tag not in _builtin_tags)
                    or (another.tag == '*!' and self.tag not in _builtin_tags)
                    or self.tag == '*'
                    or another.tag == '*')

    def _dereference(self, scm):
        if scm.tag in ('*!', '*'):
            return self._dereference(scm.body)
        return scm

    @property
    def dereferenced(self):
        return self._dereference(self)

    def _convert(self, value):
        return tagged(self.__tag, self.__schema.convert(value))

    def fill_default(self, value):
        import caty.jsontools as json
        if self.__tag not in ('*', '*!'):
            return tagged(value.tag, self.__schema.fill_default(json.untagged(value)))
        else:
            try:
                t = json.tag(value, explicit=True)
                return tagged(t, self.__schema.fill_default(json.untagged(value)))
            except:
                return self.__schema.fill_default(value)

    def dump(self, depth, node=[]):
        return u'@%s %s' % (self.__tag, self.__schema.dump(depth, node))

    @property
    def type(self):
        #XXX: 再帰的な型定義の問題があるので、タグ付きの型のインスペクションに制限をかけた
        if isinstance(self.__tag, basestring):
            return u'@' + self.__tag
        else:
            return u'@' + self.__tag.type
        #return '@%s %s' % (self.__tag, self.__schema.type)

    @property
    def is_extra_tag(self):
        return not isinstance(self.__tag, basestring)

    @property
    def canonical_type(self):
        return u'@%s %s' % (self.__tag, self.__schema.canonical_type)

    def apply(self, vars):
        self.__schema.apply(vars)

    def _check_type_variable(self, declared_type_vars, checked):
        self.__schema._check_type_variable(declared_type_vars, checked)

    def _verify_option(self):
        self.__schema._verify_option()

    def set_reference(self, referent):
        self.__schema.set_reference(referent)

    def normalize(self, queue):
        self.__schema = self.__schema.normalize(queue)
        return self

    def resolve_reference(self):
        self.__schema.resolve_reference()

class ScalarSchema(SchemaBase, Scalar):
    @property
    def tag(self):
        return self.type

    def convert(self, value):
        u"""Web からの入力は常にリスト形式となる。
        そのため、1要素のリストは常にスカラー値に変換する。
        """
        if isinstance(value, list) and len(value) == 1:
            return SchemaBase.convert(self, value[0])
        else:
            return SchemaBase.convert(self, value)

    def _deepcopy(self, checked=None):
        return self.__class__(self.options)

    def _clone(self, checked, options):
        return self.__class__(options if options else self.options)


class UnivSchema(SchemaBase, Scalar):
    u"""あらゆる型を受け付けるスキーマ。
    つまり何もしない。
    """

    def intersect(self, another):
        return another.clone(None)

    def validate(self, value, path=None):
        pass

    def _convert(self, value):
        return value

    def dump(self, depth, node=[]):
        return u'univ'


    def clone(self, checked=None, *args, **kwds):
        s = UnivSchema(*args, **kwds)
        s.annotations = self.annotations
        return s

    @property
    def type(self):
        return u'univ'

    @property
    def tag(self):
        return self.type

class ForeignSchema(SchemaBase, Scalar):
    u"""フォーリンデータ型を受け付けるスキーマ。
    """

    def intersect(self, another):
        return another.clone(None)

    def validate(self, value, path=None):
        if value is caty.UNDEFINED:
            raise JsonSchemaError(dict(msg='undefined value'))
        if type(value) in (dict, list, tuple, unicode, NoneType, str, int, bool, Decimal, TagOnly, TaggedValue):
            raise JsonSchemaError(dict(msg='Not a foreign data'))

    def _convert(self, value):
        return value

    def dump(self, depth, node=[]):
        return u'foreign'


    def clone(self, checked=None, *args, **kwds):
        s = ForeignSchema(*args, **kwds)
        s.annotations = self.annotations
        return s

    @property
    def type(self):
        return u'foreign'

    @property
    def tag(self):
        return self.type

class AnySchema(SchemaBase, Scalar):
    u"""undefined、foreign以外のあらゆる型を受け付けるスキーマ。
    """

    def intersect(self, another):
        return another.clone(None)

    def validate(self, value, path=None):
        if value is caty.UNDEFINED:
            raise JsonSchemaError(dict(msg='undefined value'))
        if type(value) not in (dict, list, tuple, unicode, NoneType, str, int, bool, Decimal, TagOnly, TaggedValue, Indef):
            raise JsonSchemaError(dict(msg='Not a json value: $value', value=repr(value)), repr(value))

    def _convert(self, value):
        return value

    def dump(self, depth, node=[]):
        return u'any'


    def clone(self, checked=None, *args, **kwds):
        s = AnySchema(*args, **kwds)
        s.annotations = self.annotations
        return s

    @property
    def type(self):
        return u'any'

    @property
    def tag(self):
        return self.type

class NullSchema(SchemaBase, Scalar):
    u"""値が null 値、つまり None であれば良とするスキーマ。
    """
    def validate(self, value, path=None):
        if self.optional and (value is caty.UNDEFINED):
            return
        if value is not None:
            raise JsonSchemaError(dict(msg='Not a null'))

    def intersect(self, another):
        if type(another) != NullSchema:
            raise JsonSchemaError(dict(msg='Unsupported operand types for $op: $type1, $type2', op='&', type1='null', type2=another.type))
        return NullSchema()

    def _convert(self, value):
        return value


    def clone(self, checked=None, *args, **kwds):
        s = NullSchema(*args, **kwds)
        s.annotations = self. annotations
        return s

    def dump(self, depth, node=[]):
        return u'null'

    @property
    def type(self):
        return u'null'

    @property
    def tag(self):
        return self.type

class IndefSchema(SchemaBase, Scalar):
    u"""値がindefであれば良とするスキーマ。
    """
    def validate(self, value, path=None):
        if self.optional and (value is UNDEFINED):
            return
        if value is not INDEF:
            raise JsonSchemaError(dict(msg='Not a indef'))

    def intersect(self, another):
        if type(another) != IndefSchema:
            raise JsonSchemaError(dict(msg='Unsupported operand types for $op: $type1, $type2', op='&', type1='null', type2=another.type))
        return IndefSchema()

    def _convert(self, value):
        return value


    def clone(self, checked=None, *args, **kwds):
        s = IndefSchema(*args, **kwds)
        s.annotations = self. annotations
        return s

    def dump(self, depth, node=[]):
        return u'indef'

    @property
    def type(self):
        return u'indef'

    @property
    def tag(self):
        return self.type

class VoidSchema(SchemaBase, Scalar):
    u"""Null と同じ unit だが、値なしを意味するところが違う。
    """
    def validate(self, value, path=None):
        if self.optional and (value is caty.UNDEFINED):
            return
        if value is not None:
            raise JsonSchemaError(dict(msg='Not a null'))

    def intersect(self, another):
        if type(another) != VoidSchema:
            raise JsonSchemaError(dict(msg='Unsupported operand types for $op: $type1, $type2', op='&', type1='void', type2=another.type))
        return VoidSchema()

    def _convert(self, value):
        return None

    def clone(self,checked=None,  *args, **kwds):
        s = VoidSchema(*args, **kwds)
        s.annotations = self.annotations
        return s

    def dump(self, depth, node=[]):
        return u'void'

    @property
    def type(self):
        return u'void'

    @property
    def tag(self):
        return self.type

class NeverSchema(SchemaBase, Scalar):
    u"""そもそもアクセスがあってはいけないスキーマ。
    """
    def validate(self, value, path=None):
        if self.optional and (value is caty.UNDEFINED):
            return
        raise JsonSchemaError(dict(msg='It is an extra element'))

    def intersect(self, another):
        return NeverSchema()

    def _convert(self, value):
        raise JsonSchemaError(dict(msg='It is an extra element'))

    def dump(self, depth, node=[]):
        return u'never'

    def clone(self, checked=None, *args, **kwds):
        s = NeverSchema(*args, **kwds)
        s.annotations = self.annotations
        return s

    @property
    def type(self):
        return u'never'

    @property
    def tag(self):
        return self.type

class UndefinedSchema(SchemaBase, Scalar):
    u"""undefinedのみを受け付けるシングルトン
    """
    @property
    def type(self):
        return u'undefined'

    def validate(self, value, path=None):
        if not (value is caty.UNDEFINED):
            raise JsonSchemaError(dict(msg='It must undefined element'))

    def intersect(self, another):
        return another

    def _convert(self, value):
        raise JsonSchemaError(dict(msg='It must undefined element'))

    def dump(self, depth, node=[]):
        return u'undefined'

    def clone(self, checked=None, *args, **kwds):
        s = UndefinedSchema()
        s.annotations = self.annotations
        return s

    def normalize(self, queue):
        return NeverSchema(options={'optional': True})

    @property
    def tag(self):
        return self.type

class EmptySchema(SchemaBase, Scalar):
    u"""宣言のみされたスキーマ。
    """
    def __init__(self, name):
        self.__name = name
        SchemaBase.__init__(self)

    def validate(self, value, path=None):
        raise JsonSchemaError(dict(msg='$name is declared but not defined', name=self.__name))

    def intersect(self, another):
        return NeverSchema()

    def _convert(self, value):
        raise JsonSchemaError(dict(msg='$name is declared but not defined', name=self.__name))

    def dump(self, depth, node=[]):
        return u'__empty__'

    def clone(self, checked=None, *args, **kwds):
        s = EmptySchema(self.__name)
        s.annotations = self.annotations
        return s

    @property
    def type(self):
        return u'__empty__'

    @property
    def tag(self):
        return self.type

class TypeVariable(SchemaBase, Scalar):
    def __init__(self, var_name, type_arguments, kind, default, options, module):
        self.var_name = var_name
        self._type_arguments = type_arguments
        self._schema = None
        self._module = module
        self._kind = kind
        self._default = default
        self._default_schema = None
        self._constraint = None
        SchemaBase.__init__(self, options)

    def __repr__(self):
        return 'Var<%s>: %s, %s, %s %s' % (self.var_name, repr(self._type_arguments), repr(self._schema), repr(self._default), str(id(self)))

    @property
    def default(self):
        return self._default

    @property
    def kind(self):
        return self._kind

    @property
    def type_args(self):
        return self._type_arguments

    @property
    def name(self):
        return self.var_name if not self._schema else self._schema.name
    
    @property
    def canonical_name(self):
        return self.var_name if not self._schema else self._schema.canonical_name

    @property
    def definition(self):
        return self.name

    @property
    def type(self):
        return self._schema.type if self._schema else u'__variable__'

    @property
    def tag(self):
        return self._schema.tag if self._schema else u'any'

    @property
    def type_vars(self):
        return self._schema.type_vars if self._schema else []

    @property
    def is_extra_tag(self):
        return self._schema.is_extra_tag if self._schema else False

    def set_default(self, schema):
        self._default_schema = schema

    def validate(self, value, path=None):
        if self.optional and value is caty.UNDEFINED:
            return 
        if self._schema:
            self.__validate(self._schema, value, path)
        elif self._default_schema:
            self.__validate(self._default_schema, value, path)
        else:
            raise JsonSchemaError(dict(msg=u'Type variable which neither instantiated nor a default value was given: $name', name=self.name))

    def __validate(self, s, value, path):
        s.validate(value, path)
        if s.format: # フォーマットの指定がある場合
            r = self._module.get_plugin(s.format).validate(value)
            if r:
                raise JsonSchemaError(r)


    def convert(self, value):
        return self._schema.convert(value) if self._schema else AnySchema().convert(value)

    def fill_default(self, value):
        return self._schema.fill_default(value) if self._schema else value

    def intersect(self, another):
        return NeverSchema()

    def update(self, another):
        return NeverSchema()

    def clone(self, checked=None, options=None):
        t = TypeVariable(self.var_name, self._type_arguments, self._kind, self._default, options or self.options, self._module)
        if self._schema:
            s = self._schema.clone(checked, options=(options or self.options))
            s.annotations = self.annotations
            t._schema = s
        if self._default_schema:
            s = self._default_schema.clone(checked, options=(options or self.options))
            s.annotations = self.annotations
            t._default_schema = s
        return t

    @property
    def definition(self):
        if not self._type_arguments:
            return self.var_name
        else:
            names = []
            for v in self._type_arguments:
                names.append(v.name)
            return u'%s<%s>' % (self._name, ', '.join(names))

    def __getattr__(self, name):
        if self._schema:
            return getattr(self._schema, name)
        else:
            raise AttributeError('%s: %s' % (str(type(self)), name))

    def __getitem__(self, k):
        return self._schema[k]

    def __iter__(self):
        return iter(self._schema)

    def dump(self, depth, node):
        if self._schema is None:
            return self.var_name
        else:
            return self._schema.dump(depth, node+[self.name])

    def __setattr__(self, n, v):
        if '_schema' in self.__dict__ and self._schema is not None and self._schema.has_attribute(n):
            setattr(self._schema, n, v)
        else:
            object.__setattr__(self, n, v)

    def _verify_option(self):
        if self._schema is not None:
            self._schema._verify_option()

    def dump(self, depth, node=[]):
        return self.var_name

    def update(self, another):
        return UpdatorSchema(self, another)

    def intersect(self, another):
        return IntersectionSchema(self, another)
    
    def set_tag_constraint(self, extag):
        self._constraint = extag

class OptionalSchema(SchemaBase, Optional):
    def __init__(self, schema):
        SchemaBase.__init__(self)
        self._schema = self.__reduce_option(schema)
        self._annotations = Annotations([])
        self._docstring = u''

    def __reduce_option(self, schema):
        if schema.optional:
            return self.__reduce_option(schema.body)
        else:
            return schema

    @property
    def name(self):
        return self._schema.name

    @property
    def body(self):
        return self._schema

    @property
    def options(self):
        return self._schema.options

    def validate(self, value, path=None):
        if not (value is caty.UNDEFINED):
            self._schema.validate(value, path)

    def convert(self, value):
        if not (value is caty.UNDEFINED):
            return self._schema.convert(value)

    @property
    def optional(self):
        return True

    def _clone(self, *args, **kwds):
        return OptionalSchema(self.body.clone(*args, **kwds))

    def _deepcopy(self, checked):
        return OptionalSchema(self.body.clone(checked))

    def intersect(self, another):
        if another.optional:
            return OptionalSchema(self.__reduce_option(self.body) & self.__reduce_option(another))
        else:
            return self.body & another

    @property
    def type(self):
        return self.body.type

    @property
    def tag(self):
        return self.body.tag

class NamedSchema(SchemaBase, Root):
    u"""名称付きスキーマ。
    組み込みでないスキーマは全て以下のように宣言される。

    {{{
    type list<T> = [T];
    type Person = {
        "name": string,
        "birth": integer
    };
    }}}

    これらはそれぞれ array, object と言ったスキーマであると同時に名称付きスキーマである。
    名称付きのスキーマは、型名の他に名称と定義名を値として持つ。
    名称とは list, Person のようなそのスキーマを参照する際に使う名前であり、
    定義名とは名称に型変数を加えたもの、即ち type 直後から = までの間に出現するトークンを指す。

    名称付きスキーマは型変数を持ちうる。上記の list の他、次のような tuple の定義も考えられる。

    {{{
    type tuple<X, Y> = [X, Y];
    type flipped<A, B> = tuple<B, A>; <- clone
    type x = flipped<integer, string>; 
    }}}

    二番目の例は単に要素の出現順序を逆転させただけで実用的な例ではないが、
    一応こういうことも可能となっている。

    """
    def __init__(self, name, type_params, schema, module):
        SchemaBase.__init__(self)
        Resource.__init__(self, module.application)
        self._name = name
        self._type_params = type_params if type_params else ()
        self._type_args = None
        self._schema = schema
        self._module = module
        self._applied = False
        self._ref_set = False
        if isinstance(schema, SchemaBase):
            self._options.update(schema.options)
        schema._options = self.options

    @property
    def dereferenced(self):
        return self._dereference(self)

    def _dereference(self, scm):
        if isinstance(scm, Root):
            return self._dereference(scm.body)
        else:
            return scm

    @property
    def body(self):
        return self._schema

    @property
    def type_params(self):
        return self._type_params

    @property
    def module(self):
        return self._module

    @property
    def app(self):
        return self.module.app

    @property
    def canonical_name(self):
        mn = self._module.canonical_name
        name = self.name
        if mn and mn != 'public':
            name = '%s:%s' % (mn, name)
        return name

    @property
    def name(self):
        return self._name
    
    @property
    def definition(self):
        if not self._type_params:
            return self._name
        else:
            names = []
            for v in self._type_params:
                if self._type_args and v.name in self._type_args:
                    continue
                else:
                    names.append(v.name)
            return u'%s<%s>' % (self._name, ', '.join(names))

    @property
    def type(self):
        return self._schema.type

    @property
    def tag(self):
        return self._schema.tag

    @property
    def type_vars(self):
        return list(self._type_vars)

    def validate(self, value, path=None):
        if self.optional and value is caty.UNDEFINED:
            return 
        self._schema.validate(value, path)
        if self._schema.format: # フォーマットの指定がある場合
            try:
                r = self._module.get_plugin(self._schema.format).validate(value)
                if r:
                    raise JsonSchemaError(r)
            except KeyError, e:
                pass #XXX: formatの仕様変更が予定されているので一旦無視

    def convert(self, value):
        return self._schema.convert(value)

    def fill_default(self, value):
        return self._schema.fill_default(value)

    def intersect(self, another):
        return self._schema & another

    def update(self, another):
        return self._schema ** another

    def union(self, another):
        return UnionSchema(self, another)

    def clone(self, checked=None, options=None):
        if not checked:
            checked = set()
        if self.canonical_name in checked:
            return self
        else:
            checked.add(self.canonical_name)
        s = NamedSchema(self._name, 
                        self._type_params, 
                        self._schema.clone(checked, options=(options or self.options)), 
                        self._module)
        s.annotations = self.annotations
        if self._type_args:
            s.apply(self._type_args)
        return s

    def __getattr__(self, name):
        if '_schema' in self.__dict__:
            return getattr(self._schema, name)
        else:
            raise AttributeError('%s: %s' % (str(type(self)), name))

    def __getitem__(self, k):
        return self._schema[k]

    def __iter__(self):
        return iter(self._schema)

    def apply(self, vars):
        u"""型変数をスキーマに適用する。
        """
        if self._applied: return
        self._applied = True
        self._type_args = vars
        v = [a for a in self._type_vars if a.name not in vars]
        self._schema.apply(vars)

    def dump(self, depth, node):
        if self.name in node:
            return self.name
        else:
            return self._schema.dump(depth, node+[self.name])

    def __setattr__(self, n, v):
        if '_schema' in self.__dict__ and self._schema.has_attribute(n):
            setattr(self._schema, n, v)
        else:
            object.__setattr__(self, n, v)

    def _check_type_variable(self, declared_type_vars, checked):
        if self.canonical_name in checked: return
        checked.append(self.canonical_name)
        if hasattr(self, '_schema'):
            self._schema._check_type_variable(declared_type_vars, checked)

    def _verify_option(self):
        if hasattr(self, '_schema'):
            self._schema._verify_option()

    def set_reference(self, referent):
        if self._ref_set: return
        self._ref_set = True
        referent[self.canonical_name] = self
        v = self._schema.set_reference(referent)
        if v:
            self._schema = v

    def __repr__(self):
        return 'NamedSchema:' + self.name + repr(self.body)

    @property
    def optional(self):
        return self._schema.optional
    

class TypeReference(SchemaBase, Scalar, Ref):

    # 参照先がオブジェクトの可能性もあるので擬似タグをサポート
    pseudoTag = attribute('pseudoTag', PseudoTag(None, None))
    __options__ = SchemaBase.__options__ | set(['pseudoTag'])
    def __init__(self, name, type_args, module):
        SchemaBase.__init__(self)
        self._name = name
        self._type_args = type_args
        self.module = module
        self.annotations = Annotations([])
        self.body = None
        self.recursive = False

    def intersect(self, another):
        return self.body & another

    def update(self, another):
        return self.body ** another

    def union(self, another):
        return UnionSchema(self, another)

    @property
    def type_params(self):
        return self.body.type_params

    @property
    def name(self):
        return self._name

    @property
    def canonical_name(self):
        return self._name if self.body is None else self.body.canonical_name
    
    @property
    def type(self):
        return self.body.type if self.body else u'__reference__'

    @property
    def tag(self):
        return self.body.tag

    @property
    def definition(self):
        return self._name

    @property
    def app(self):
        return self.module.app

    def type_args():
        def get(self):
            return self._type_args

        def set(self, type_args):
            self._type_args = type_args

        return get, set
    type_args = property(*type_args())

    def validate(self, value, path=None):
        self.body.validate(value, path)
        if isinstance(value, dict): 
            errors = {}
            is_error = False
            for k, v in value.iteritems():
                if self.pseudoTag.name == k:
                    if self.pseudoTag.value != v:
                        errors[k] = ErrorObj(True, u'', u'', dict(msg=u'Not matched to pseudo tag $tag: $value', tag=str(self.pseudoTag), value=v))
                        is_error = True
            if is_error:
                e = JsonSchemaErrorObject({u'msg': u'Failed to validate object'})
                e.update(errors)
                raise e

    def convert(self, value):
        return self.body.convert(value)

    def _clone(self, checked, options):
        t = TypeReference(self._name, self.type_args, self.module)
        if self.body is None:
            raise
        b = self.body.clone(checked, options)
        t.body = b
        return t

    def _deepcopy(self, checked):
        t = TypeReference(self._name, self.type_args, self.module)
        b = self.body.clone(checked)
        t.body = b
        return t

    def intersect(self, another):
        return self.body & another

    def update(self, another):
        return self.body ** another

    def __repr__(self):
        return 'Ref: ' + self.name + repr(self.body)

    def fill_default(self, value):
        return self.body.fill_default(value)

    @property
    def optional(self):
        return self.body.optional if self.body else False
    
class UnaryOpSchema(SchemaBase, UnaryOperator):
    def __init__(self, operator, schema, type_args):
        SchemaBase.__init__(self)
        self._schema = schema
        self._annotations = Annotations([])
        self._docstring = u''
        self._operator = operator
        self._type_args = type_args

    @property
    def type_args(self):
        return self._type_args

    @property
    def operator(self):
        return self._operator

    @property
    def name(self):
        return self._schema.name

    @property
    def body(self):
        return self._schema

    @property
    def options(self):
        return self._schema.options

    def validate(self, value, path=None):
        if not (value is caty.UNDEFINED):
            self._schema.validate(value, path)

    def convert(self, value):
        if not (value is caty.UNDEFINED):
            return self._schema.convert(value)

    @property
    def optional(self):
        return True

    def _clone(self, *args, **kwds):
        return UnaryOpSchema(self._operator, self.body.clone(*args, **kwds))

    def _deepcopy(self, checked):
        return UnaryOpSchema(self._operator, self.body.clone(*args, **kwds))

    @property
    def type(self):
        return self.body.type

    @property
    def tag(self):
        return self.body.tag

class ExtractorSchema(SchemaBase, UnaryOperator):
    def __init__(self, path, schema):
        SchemaBase.__init__(self)
        self._schema = schema
        self._annotations = Annotations([])
        self._docstring = u''
        self._operator = u'extract'
        self.path = path

    @property
    def operator(self):
        return self._operator

    @property
    def name(self):
        return self._schema.name

    @property
    def body(self):
        return self._schema

    @property
    def options(self):
        return self._schema.options

    def validate(self, value, path=None):
        if not (value is caty.UNDEFINED):
            self._schema.validate(value, path)

    def convert(self, value):
        if not (value is caty.UNDEFINED):
            return self._schema.convert(value)

    @property
    def optional(self):
        return True

    def _clone(self, *args, **kwds):
        return UnaryOpSchema(self._operator, self.body.clone(*args, **kwds))

    def _deepcopy(self, checked):
        return UnaryOpSchema(self._operator, self.body.clone(*args, **kwds))

    @property
    def type(self):
        return self.body.type

    @property
    def tag(self):
        return self.body.tag

class OverlayedDict(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __getitem__(self, k):
        if k in self.a:
            return self.a[k]
        elif k in self.b:
            return self.b[k]
        raise KeyError(k)

    def __contains__(self, k):
        return k in self.a or k in self.b

class Annotations(dict):
    def __init__(self, annotations):
        self._annotations = annotations
        for a in annotations:
            self[a.name] = a

    def __nonzero__(self):
        return bool(self._annotations)

    def __str__(self):
        return '@[%s]' % ', '.join(map(str, self._annotations))

    def to_str(self):
        if self._annotations:
            return u'@[%s]' % ', '.join(map(Annotation.to_str, self._annotations))
        else:
            return u''
    
    def add(self, annotation):
        self[annotation.name] = annotation
        self._annotations.append(annotation)

    def __add__(self, another):
        n = Annotations([])
        for a in self._annotations:
            n.add(a)
        for b in another._annotations:
            n.add(b)
        return n

    def reify(self):
        return tagged('annotation', [a.reify() for a in self._annotations])

class Annotation(object):
    def __init__(self, name, value=True):
        self.name = name
        self.value = value

    def __str__(self):
        if self.value is not None:
            return '%s(%s)' % (self.name, repr(self.value))
        else:
            return self.name

    def to_str(self):
        import caty.jsontools.xjson as json
        if self.value is not None:
            return '%s(%s)' % (self.name, json.dumps(self.value))
        else:
            return self.name

    def reify(self):
        return {'name': self.name, 'value': self.value}

