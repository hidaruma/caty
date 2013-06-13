#coding: utf-8
from caty.core.schema.base import *
import operator
import caty.core.runtimeobject as ro
import caty.jsontools as json
from caty.core.typeinterface import Bag

class BagItem(object):
    def __init__(self, p):
        self.schema = p[1]
        self.minCount = p[1].minCount
        self.maxCount = p[1].maxCount
        self.index = p[0]
        self.count = 0

    def validate(self, v, path=None):
        try:
            self.schema.validate(v, path)
            self.count += 1
            return True
        except:
            return False

    def convert(self, v):
        try:
            x = self.schema.convert(v)
            self.count += 1
            return True, x
        except:
            return False, None

    def check_condition(self):
        if not self.minCount <= self.count:
            raise JsonSchemaError(dict(msg=u'The occurrence count of the element is too few: type=$type, minCount=$min, count=$count', type=self.schema.type, min=self.minCount, count=self.count))
        if self.maxCount and not self.count <= self.maxCount:
            raise JsonSchemaError(dict(msg=u'The occurrence count of the element is too mutch: type=$type, maxCount=$max, count=$count', type=self.schema.type, max=self.maxCount, count=self.count))

class BagSchema(SchemaBase, Bag):
    
    def __init__(self, schema_list, *args, **kwds):
        SchemaBase.__init__(self, *args, **kwds)
        self.schema_list = schema_list
        if schema_list:
            try:
                reduce(UnionSchema, schema_list)
            except Exception, e:
                raise JsonSchemaError(dict(msg=u'Elements of Bag type is not exclusive: $types', types=', '.join(map(lambda x:x.type, schema_list))))
    
    def _validate(self, value):
        if not self.optional and value == None:
            raise JsonSchemaError(dict(msg='null is not allowed'))
        elif self.optional and value is None:
            return
        if not (isinstance(value, list) or isinstance(value, tuple)):
            raise JsonSchemaError(dict(msg=u'value should be $type', type='array'))
        items = map(BagItem, enumerate(self.schema_list))
        for v in value:
            if not any(map(lambda x: x.validate(v), items)):
                raise JsonSchemaError(dict(msg=
                    u'$value does not suit either of $types', 
                    value=json.pp(v), 
                    types=', '.join(map(lambda x: x.name, self.schema_list))))
        for i in items:
            i.check_condition()

    def _convert(self, value):
        if not (isinstance(value, list) or isinstance(value, tuple)):
            if value is None and self.schema_list[0].optional:
                return []
            raise JsonSchemaError(dict(msg=u'value should be $type', type='array'))
        result = []
        for v in value:
            for i in items:
                b, r = i.convert(v)
                if b:
                    result.append(r)
        for i in items:
            i.check_condition()
        return result

    def _deepcopy(self, ignore):
        return BagSchema(self.schema_list, self.options)

    def _clone(self, checked, options):
        if options is not None:
            return BagSchema(self.schema_list, options)
        else:
            return BagSchema(self.schema_list, self.options)

    def dump(self, depth, node=[]):
        r = []
        for s in self.schema_list:
            n = s.dump(depth, node)
            n += s._dump_option()
            r.append(n)
        return '{[%s]}' % ', '.join(r)

    @property
    def type(self):
        return u'bag'

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

    def _check_type_variable(self, declared_type_vars, checked):
        for s in self.schema_list:
            s._check_type_variable(declared_type_vars, checked)

    def set_reference(self, referent):
        found = False
        for n, s in enumerate(self.schema_list):
            v = s.set_reference(referent)
            if v:
                found = True
                self.schema_list[n] = v

        if found:
            return self

    def resolve_reference(self):
        for s in self.schema_list:
            s.resolve_reference()
    
    def __iter__(self):
        return iter(self.schema_list)

    @property
    def tag(self):
        return u'bag'

