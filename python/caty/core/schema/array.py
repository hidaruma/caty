#coding: utf-8
from caty.core.schema.base import *
import caty.core.runtimeobject as ro
from caty.core.typeinterface import Array
import random
import types

class ArraySchema(SchemaBase, Array):
    
    __options__ = SchemaBase.__options__ | set(['maxItems', 'minItems', 'repeat', 'tight'])
    maxItems = attribute('maxItems')
    minItems = attribute('minItems')
    repeat = attribute('repeat')
    tight = attribute('tight')

    def __init__(self, schema_list, *args, **kwds):
        SchemaBase.__init__(self, *args, **kwds)
        self.schema_list = schema_list
        if self.tight is not None and not isinstance(self.tight, types.BooleanType):
            raise JsonSchemaError(dict(msg=u'tight attribute must be boolean type'))

    def _validate(self, value):
        if not self.optional and value == None:
            raise JsonSchemaError(dict(msg='null is not allowed'))
        elif self.optional and value is None:
            return
        if not (isinstance(value, list) or isinstance(value, tuple)):
            raise JsonSchemaError(dict(msg=u'value should be $type', type='array'))
        import caty
        if self.tight is not None and caty.UNDEFINED in value:
            raise JsonSchemaError(dict(msg=u'This type can not contain undefined'))
        if self.maxItems is not None and len(value) > self.maxItems:
            raise JsonSchemaError(dict(msg=u'This type can contain only $max elements or less', max=self.maxItems))
        if self.minItems is not None and len(value) < self.minItems:
            raise JsonSchemaError(dict(msg=u'This type must contain $min elements or more', min=self.minItems))
        mandatory = len(self.schema_list)
        if self.repeat:
            mandatory -= 1
        for s in self.schema_list:
            if s.optional:
                mandatory -= 1
        l = len(value)
        if l < mandatory:
            raise JsonSchemaError(dict(msg=u'This type must contain $min elements or more', min=mandatory))
        if l > len(self.schema_list) and not self.repeat:
            raise JsonSchemaError(dict(msg=u'This type can contain only $max elements or less', max=len(self.schema_list)))
        errors = []
        is_error = False
        count = 0
        s_count = 0
        while count < len(value):
            v = value[count]
            if v is caty.UNDEFINED:
                count += 1
                s_count += 1
                continue
            if s_count >= len(self.schema_list):
                if not self.repeat:
                    errors.append(JsonSchemaError(dict(msg=u'$type can not appear at tail of this type', type=type(v))))
                    is_error = True
                    break
                    #raise JsonSchemaError(dict(msg=u'This type must contain $min elements or more', min=len(self.schema_list)))
                elif self.repeat:
                    s_count = len(self.schema_list) - 1
            try:
                self.schema_list[s_count].validate(v)
                errors.append(ErrorObj(False, v, v, ''))
            except JsonSchemaError, e:
                errors.append(e)
                is_error = True
                count += 1
                s_count += 1
            else:
                count += 1
                s_count += 1
        if is_error:
            e = JsonSchemaErrorList({u'msg': u'Failed to validate array type:'}, errors)
            raise e

    def _convert(self, value):
        if not (isinstance(value, list) or isinstance(value, tuple)):
            if value is None and self.schema_list[0].optional:
                return []
            raise JsonSchemaError(dict(msg='value should be $type', type='array'))
        count = 0
        result =[]
        errors = []
        is_error = False
        for v in value:
            if count >= len(self.schema_list):
                if not self.repeat:
                    raise JsonSchemaError(dict(msg=u'This type can contain only $max elements or less', max=len(self.schema_list)))
                elif self.repeat:
                    count = len(self.schema_list) - 1
            try:
                result.append(self.schema_list[count].convert(v))
                errors.append(ErrorObj(False, v, result[-1], ''))
            except JsonSchemaError, e:
                is_error = True
                errors.append(e)
            count += 1
        if is_error:
            e = JsonSchemaErrorList({u'msg': u'Failed to validate array type:'}, errors)
            raise e
        return result

    def _deepcopy(self, ignore):
        return ArraySchema(self.schema_list, self.options)

    def _clone(self, checked, options):
        if options is not None:
            if self.repeat is not None and 'repeat' not in options:
                options['repeat'] = self.repeat
            if self.minItems is not None and 'minItems' not in options:
                options['minItems'] = self.minItems
            if self.maxItems is not None and 'maxItems' not in options:
                options['maxItems'] = self.maxItems
            if self.tight is not None and 'tight' not in options:
                options['tight'] = self.tight
            return ArraySchema([s.clone(checked, options=s.options) for s in self.schema_list], options)
        else:
            return ArraySchema([s.clone(checked, options=s.options) for s in self.schema_list], self.options)

    def dump(self, depth, node=[]):
        r = []
        for s in self.schema_list:
            r.append(s.dump(depth, node))
            if s.optional:
                r[-1] += '?'
            if s.subName:
                r[-1] += ' ' + s.subName
        if self.repeat:
            r[-1] += '*'
        return '[%s]' % ', '.join(r)

    def intersect(self, another):
        al = another.schema_list
        r = []
        for a, b in zip(self.schema_list, al):
            r.append(a & b)
        o = {}
        if self.maxItems and another.maxItems:
            o['maxItems'] = min(self.maxItems, another.maxItems)
        else:
            o['maxItems'] = self.maxItems if self.maxItems != None else another.maxItems
        if self.minItems and another.minItems:
            o['minItems'] = max(self.minItems, another.minItems)
        else:
            o['minItems'] = self.minItems if self.minItems != None else another.minItems
        if self.optional or another.optional:
            o['optional'] = True
        if self.repeat and another.repeat:
            o['repeat'] = True
        n = ArraySchema(r, o)
        return n
       
    @property
    def type(self):
        return 'array'

    def apply(self, vars):
        for s in self.schema_list:
            #if s.type == '__variable__' and s.name in vars:
            s.apply(vars)

    @property
    def type_vars(self):
        v = []
        for s in self.schema_list:
            if s.type != '__variable__': continue
            for t in s.type_vars:
                if t not in v:
                    v.append(t)
        return v


    def __iter__(self):
        return iter(self.schema_list)

    def __repr__(self):
        return repr((map(repr, self.schema_list)))

    @property
    def tag(self):
        return u'array'


