#coding: utf-8
from caty.core.schema.base import *
from caty.util import try_parse
from decimal import Decimal
import caty.core.runtimeobject as ro
from caty.core.typeinterface import Enum
import random

class EnumSchema(SchemaBase, Enum):
    def __init__(self, enum, *args, **kwds):
        SchemaBase.__init__(self, *args, **kwds)
        self.enum = enum

    def _validate(self, value):
        if not self.optional and value is None:
            raise JsonSchemaError(ro.i18n.get(u'null is not allowed'), value, '')
        elif self.optional and value is None:
            return
        for e in self.enum:
            if isinstance(e, SchemaBase):
                try:
                    e.validate(value)
                except:
                    pass
                else:
                    return
            else:
                if e == value:
                    if (type(e) == type(value)) or (not isinstance(value, bool) and not isinstance(e, bool) and isinstance(e, (int, Decimal)) and isinstance(value, (int, Decimal))):
                        return
        t = self._to_str()
        if len(self.enum) > 1:
            raise JsonSchemaError(ro.i18n.get(u'value should be one of $type', type=t), value, '')
        else:
            raise JsonSchemaError(ro.i18n.get(u'value should be $type', type=t), value, '')

    def union(self, another):
        if another.type == 'enum':
            return EnumSchema(self.enum + another.enum, self.options)
        else:
            return SchemaBase.union(self, another)

    def intersect(self, another):
        en = []
        if another.type == 'enum':
            for e in another.enum:
                if e in self.enum:
                    en.append(e)
            return EnumSchema(en, self.options)
        else:
            raise JsonSchemaError(ro.i18n.get(u'Unsupported operand types for $op: $type1, $type2', op='&', type1='enum', type2=another.type))

    def _deepcopy(self, ignore):
        return EnumSchema(self.enum, self.options)

    def _clone(self, ignore, options=None):
        return EnumSchema(self.enum, 
                          options if options else self.options)

    def _convert(self, value):
        for e in self.enum:
            if isinstance(e, unicode):
                if value == e:
                    return e
            else:
                if try_parse(int, value) == e:
                    return e
        if len(self.enum) > 1:
            t = 'one of ' + self._to_str()
        else:
            t = self._to_str()
        raise JsonSchemaError(ro.i18n.get(u'value should be $type', type=t), value, '')

    def apply(self, vars):
        for s in self.enum:
            if isinstance(s, SchemaBase):
                s.apply(vars)

    def set_reference(self, referent):
        found = False
        for n, s in enumerate(self.enum):
            if not isinstance(s, SchemaBase): continue
            v = s.set_reference(referent)
            if v:
                found = True
                self.enum[n] = v

        if found:
            return self

    def _to_str(self):
        r = []
        for e in self.enum:
            if isinstance(e, unicode):
                r.append('"%s"' % e)
            else:
                r.append(str(e))
        return ', '.join(r)

    def dump(self, depth, node=[]):
        r = []
        for e in self.enum:
            if isinstance(e, unicode):
                r.append('"%s"' % e)
            else:
                r.append(str(e))
        return ' | '.join(r)

    @property
    def type(self):
        return 'enum'

    def _check_type_variable(self, declared_type_vars, checked):
        if self.canonical_name in checked: return
        checked.append(self.canonical_name)
        for s in self.enum:
            if isinstance(s, SchemaBase):
                s._check_type_variable(declared_type_vars, checked)


    def resolve_reference(self):
        for s in self.enum:
            if not isinstance(s, SchemaBase): continue
            s.resolve_reference()

    def tag(self):
        return u'enum'

    def __iter__(self):
        return iter(self.enum)

