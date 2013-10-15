#coding: utf-8
from caty.core.schema.base import *
from caty.core.typeinterface import Object
import caty.core.runtimeobject as ro
import caty.jsontools as json
import random
from caty.core.spectypes import UNDEFINED
from caty.util.dev import debug

class ObjectSchema(SchemaBase, Object):
    u"""JSON オブジェクトの妥当性検証を行うクラス。
    """
    maxProperties = attribute('maxProperties', -1)
    minProperties = attribute('minProperties', -1)
    propNameFormat = attribute('propNameFormat', u'')
    pseudoTag = attribute('pseudoTag', PseudoTag(None, None))
    __options__ = SchemaBase.__options__ | set(['maxProperties', 'minProperties', 'pseudoTag', 'propNameFormat'])

    def __init__(self, schema_obj=None, wildcard=None, options=None):
        SchemaBase.__init__(self, options)
        self._wildcard = wildcard if wildcard else UndefinedSchema()
        if not isinstance(self._wildcard, (UndefinedSchema, OptionalSchema)):
            self._wildcard = OptionalSchema(self._wildcard)
        self.schema_obj = schema_obj if schema_obj else {}
        assert all(map(lambda x:isinstance(x, SchemaBase), self.schema_obj.values())), repr(self.schema_obj.values())

    def wildcard():
        def _get(self):
            return self._wildcard

        def _set(self, v):
            self._wildcard = v

        return _get, _set
    wildcard = property(*wildcard())
    

    def union(self, schema):
        if schema.type == 'object':
            if not self.pseudoTag.exclusive(schema.pseudoTag):
                raise JsonSchemaError(dict(msg='Pseudo tag is not exclusive: $tag1, $tag2', tag1=str(self.pseudoTag), tag2=str(schema.pseudoTag)))
        return UnionSchema(self, schema)

    def intersect(self, another):
        cls = type(another)
        if not (cls in (UnionSchema, IntersectionSchema, UpdatorSchema, TypeVariable, ObjectSchema)
                or (cls in(TypeReference, NamedSchema) and another.type == 'object')):
            raise JsonSchemaError(dict(msg=u'Unsupported operand types for $op: $type1, $type2', op='&', type1='object', type2=another.type))

        if cls == ObjectSchema:
            return self._intersect_obj(another)
        elif cls == TypeVariable:
            return IntersectionSchema(self, another)
        return another.intersect(self)

    def _intersect_obj(self, another):
        if self.wildcard.type in (u'any', u'univ') and not self.schema_obj:
            return another
        if another.wildcard.type in (u'any', u'univ') and not another.schema_obj:
            return self
        newobj = ObjectSchema()
        newschema_obj = {}
        for k, v in self.items():
            if k in another:
                newschema_obj[k] = v & another[k]
            else:
                newschema_obj[k] = v & another.wildcard
        for k, v in another.items():
            if k in newschema_obj: continue
            else:
                newschema_obj[k] = v & self.wildcard
        newobj.schema_obj = newschema_obj
        wild = self.wildcard & another.wildcard
        newobj.wildcard = wild
        ps1 = self.pseudoTag
        ps2 = another.pseudoTag
        if ps1.defined and ps2.defined:
            if ps1.exclusive(ps2):
                return NeverSchema()
            newobj.pseudoTag = ps1
        elif ps.defined and not ps2.defined:
            newobj.pseudoTag = ps1
        else:
            newobj.pseudoTag = ps2
        return newobj

    def update(self, another):
        if another.type != 'object' or (isinstance(another.type, tuple) and not all(map(lambda x:x.type == 'object', another.type))):
            t = str(another.type) if another.type != '__variable__' else str(another.name)
            raise JsonSchemaError(dict(msg=u'Unsupported operand types for $op: $type1, $type2', op='++', type1='object', type2=t))
        if not isinstance(another, ObjectSchema):
            return another ** self
        newschema_obj = {}
        if self._has_common_properties(another):
            raise JsonSchemaError(dict(msg=u'Can not calculate ++: optional property which is not undefined might appear at both side', prop='some property'))
        for k, v in another.items():
            if k in self:
                if self[k].type not in ('undefined', 'never') and v.type not in ('undefined', 'never'):
                    raise JsonSchemaError(dict(msg=u'Can not calculate ++: $prop which is not undefined appears at both side', prop=k))
                else:
                    newschema_obj[k] = v
            elif self.wildcard.type not in ('never', 'undefined'):
                raise JsonSchemaError(dict(msg=u'Can not calculate ++: $prop which is not undefined might appear at both side', prop=k))
            else:
                newschema_obj[k] = v
        for k, v in self.items():
            if k not in newschema_obj:
                newschema_obj[k] = v
            elif newschema_obj[k].type == 'undefined':
                newschema_obj[k] = v

        newobj = ObjectSchema()
        newobj.schema_obj = newschema_obj
        newobj.wildcard = self.wildcard
        return newobj

    def _has_common_properties(self, another):
        s, _s = self._list_properties(self)
        t, _t = self._list_properties(another)
        if s.intersection(t):
            return True
        if '*' in s and not _s.intersection(t):
            return True
        if '*' in t and not _t.intersection(s):
            return True
        return False

    def _list_properties(self, o):
        s = set([])
        _s = set([])
        for k, v in o.items():
            if v.type not in ('undefined', 'never'):
                s.add(k)
            else:
                _s.add(k)
        if o.wildcard.type not in ('never', 'undefined'):
            s.add('*')
        return s, _s

    def _validate(self, value):
        errors = {}
        is_error = False
        if not self.optional and value == None:
            raise JsonSchemaError(dict(msg='null is not allowed'))
        elif self.optional and value is None:
            return
        if not isinstance(value, dict):
            raise JsonSchemaError(dict(msg='value should be $type: $data', type='object', data=value))
        if self.minProperties > -1 and self.minProperties > len(value):
            raise JsonSchemaError(dict(msg=u"Number of property should be greater than $min", min=self.minProperties), {})
        if self.maxProperties > -1 and self.maxProperties < len(value):
            raise JsonSchemaError(dict(msg=u"Number of property should be smaller than $max", max=self.maxProperties), {})
        for k, v in value.iteritems():
            if k not in self.schema_obj:
                if self.wildcard is None:
                    errors[k] = ErrorObj(True, u'', u'', dict(msg=u'Unknown property: $name', name=k))
                    is_error = True
                else:
                    try:
                        self.wildcard.validate(v)
                    except JsonSchemaError, e:
                        is_error = True
                        errors[k] = e
            else:
                if self.pseudoTag.name == k:
                    if self.pseudoTag.value != v:
                        errors[k] = ErrorObj(True, u'', u'', dict(msg=u'Not matched to pseudo tag $tag: $value', tag=str(self.pseudoTag), value=v))
                        is_error = True
                else:
                    eo = self.__check_with_ann(value, k)
                    if eo:
                        errors[k] = eo
                        is_error = True
                        continue
                    eo = self.__check_without_ann(value, k)
                    if eo:
                        errors[k] = eo
                        is_error = True
                        continue                    
                    try:
                        self.schema_obj[k].validate(v)
                    except JsonSchemaError, e:
                        is_error = True
                        errors[k] = e

        # optional でないメンバーで漏れがないかチェック
        for k, v in self.schema_obj.iteritems():
            if not v.optional and k not in value and v.type != u'univ':
                errors[k] = ErrorObj(True, u'', u'', dict(msg=u'Property not exists: $name', name=k))
                is_error = True
        # 擬似タグ
        if self.pseudoTag:
            for k, v in self.pseudoTag.validate(value).items():
                if k not in errors:
                    errors[k] = v
        if is_error:
            e = JsonSchemaErrorObject({u'msg': u'Failed to validate object'})
            e.update(errors)
            raise e

    def __check_with_ann(self, value, k):
        mode, withtypes = self.__get_ann(k, 'with')
        if not withtypes:
            return None
        d = self.schema_obj[k].annotations.get('default')
        if d and value[k] == d.value:
            return None
        errored_keys = []
        for withtype in withtypes:
            if withtype and withtype not in value:
                errored_keys.append(withtype)
        if mode == '_AND':
            if errored_keys:
                return ErrorObj(True, u'', u'', dict(msg=u'$key1 must appear with $key2', key1=k, key2=', '.join(withtypes)))
        else:
            if errored_keys == withtypes:
                return ErrorObj(True, u'', u'', dict(msg=u'$key1 must appear with one of $key2', key1=k, key2=', '.join(withtypes)))

    def __check_without_ann(self, value, k):
        mode, withtypes = self.__get_ann(k, 'without')
        if not withtypes:
            return None
        errored_keys = []
        for withtype in withtypes:
            if withtype and withtype in value:
                wt = self.schema_obj.get(withtype)
                if wt:
                    default = wt.annotations.get('default')
                    if default and default.value == value[withtype]:
                        continue
                d = self.schema_obj[k].annotations.get('default')
                if d and value[k] == d.value:
                    continue
                errored_keys.append(withtype)
        if mode == '_AND':
            if errored_keys:
                return ErrorObj(True, u'', u'', dict(msg=u'$key1 must not appear with $key2', key1=k, key2=', '.join(withtypes)))
        else:
            if errored_keys == withtypes:
                return ErrorObj(True, u'', u'', dict(msg=u'$key1 must not appear with one of $key2', key1=k, key2=', '.join(withtypes)))
    def __get_ann(self, k, t):
        withann = self.schema_obj[k].annotations.get(t)
        if withann:
            val = withann.value
        else:
            val = None
        if isinstance(val, basestring):
            withtypes = [val]
            mode = '_AND'
        else:
            mode, withtypes = json.split_tag(val)
            if mode != '_OR':
                mode = '_AND'
        return mode, withtypes

    def _format(self, errors):
        r = []
        for k, v in errors:
            r.append(u'    %s: %s\n' % (k, v.msg))
        return ''.join(r)

    def _convert(self, value):
        result = {}
        errors = {}
        orig_info = {}
        is_error = False
        if not isinstance(value, dict):
            raise JsonSchemaError(dict(msg='value should be $type', type='object'))
        for k, v in value.iteritems():
            if v is UNDEFINED:
                result[k] = v
            elif k not in self.schema_obj:
                if self.wildcard is None:
                    errors[k] = ErrorObj(True, u'', u'', dict(msg=u'Unknown property: $name', name=k))
                    is_error = True
                else:
                    try:
                        result[k] = self.wildcard.convert(v)
                    except JsonSchemaError, e:
                        is_error = True
                        errors[k] = e
            else:
                try:
                    result[k] = self.schema_obj[k].convert(v)
                except JsonSchemaError, e:
                    is_error = True
                    errors[k] = e
        for k, v in self.schema_obj.iteritems():
            if k not in value:
                if not v.optional and v.type != u'univ':
                    is_error = True
                    errors[k] = ErrorObj(True, u'', u'', dict(msg=u'Property not exists: $name', name=k))
                elif v.optional and 'default' in v.annotations:
                    result[k] = v.annotations['default'].value
        if is_error:
            e = JsonSchemaErrorObject({u'msg': u'Failed to convert object'})
            e.update(errors)
            e.succ = result
            raise e
        return result

    def fill_default(self, value, fill_undef=False):
        from caty import UNDEFINED
        result = {}
        for k, v in value.items():
            result[k] = v
        for k, v in self.schema_obj.iteritems():
            if k not in value:
                if not v.optional:
                    pass
                elif v.optional:
                    if 'default' in v.annotations:
                        result[k] = v.annotations['default'].value
                    elif fill_undef:
                        result[k] = UNDEFINED
            else:
                result[k] = value[k]
        return result

    def __iter__(self):
        return iter(self.schema_obj.keys())

    def __getitem__(self, key):
        return self.schema_obj[key]

    def __setitem__(self, key, value):
        raise Exception(u'スキーマは不変オブジェクトです')
    
    def keys(self):
        return self.schema_obj.keys()

    def values(self):
        return self.schema_obj.values()

    def items(self):
        return self.schema_obj.items()

    def iterkeys(self):
        return self.schema_obj.iterkeys()

    def itervalues(self):
        return self.schema_obj.itervalues()

    def iteritems(self):
        return self.schema_obj.iteritems()

    def __contains__(self, k):
        return k in self.schema_obj

    def dump(self, depth=0, node=[]):
        s = []
        s.append('    ' * depth)
        s.append('{\n')
        depth += 1
        for k, v in self.schema_obj.iteritems():
            s.append('    ' * depth)
            s.append('"%s"' % k)
            s.append(':')
            s.append(v.dump(depth, node))
            if v.optional:
                s.append('?')
            s.append('\n')
        if self.wildcard:
            s.append('    ' * depth)
            s.append('*')
            s.append(':')
            s.append(self.wildcard.dump(depth, node))
            s.append('?')
            s.append('\n')
        else:
            s.append('    ' * depth)
            s.append('*:never')
            s.append('?')
            s.append('\n')
        s.append('    ' * (depth - 1))
        s.append('}')
        return ''.join(s)

    @property
    def type(self):
        return u'object'

    def apply(self, vars):
        for k, v in self.schema_obj.items():
            v.apply(vars)
        self.wildcard.apply(vars)

    def set_reference(self, referent):
        found = False
        for k, v in self.schema_obj.items():
            x = v.set_reference(referent)
            if x:
                found = True
                self.schema_obj[k] = x
            x = self.schema_obj[k]
            if k == 'x':
                if not x.optional:
                    raise 
        x = self.wildcard.set_reference(referent)
        if x:
            self.wildcard = x
            found = True
        if found:
            return self

    def _deepcopy(self, checked=None):
        return self._clone(checked)

    def _clone(self, checked, options=None):
        o = {}
        for k, v in self.schema_obj.items():
            o[k] = v.clone(checked)
        return ObjectSchema(o, 
                            self.wildcard.clone(checked),
                            options if options else self.options)

    def __eq__(self, o):
        return id(self) == id(o)

    def __ne__(self, o):
        return id(self) != id(o)

    #@property
    #def type_vars(self):
    #    v = []
    #    for s in self.schema_obj.values():
    #        if s.type != '__variable__': continue
    #        for t in s.type_vars:
    #            if t not in v:
    #                v.append(t)
    #    return v


    def __repr__(self):
        return object.__repr__(self)

    __str__ = __repr__

    def _check_type_variable(self, declared_type_vars, checked):
        for s in self.schema_obj.values():
            s._check_type_variable(declared_type_vars, checked)
        if self.wildcard:
            self.wildcard._check_type_variable(declared_type_vars, checked)

    def resolve_reference(self):
        for k ,v in self.schema_obj.items():
            v.resolve_reference()
        if self.wildcard:
            self.wildcard.resolve_reference()

    @property
    def tag(self):
        return u'object'

