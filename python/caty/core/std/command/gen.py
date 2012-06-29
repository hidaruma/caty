#coding:utf-8
from caty.core.command import Builtin
from caty.core.typeinterface import TreeCursor, Union, Tag
from caty.core.schema import TagSchema, StringSchema, NumberSchema, BoolSchema, BinarySchema, TypeReference, ForeignSchema, UnionSchema
import caty.jsontools as json
import random
from string import printable
from caty import ForeignObject
from decimal import Decimal

class Sample(Builtin):
   
    def setup(self, opts, type_name):
        self.__type_name = type_name
        self._gen_options = opts

    def execute(self):
        t = self.schema.get_type(self.__type_name)
        return t.accept(DataGenerator(self._gen_options))

class _EMPTY(object): pass # undefinedではない、存在しない事を表すアトム

class DataGenerator(TreeCursor):
    def __init__(self, gen_options):
        self.__gen_str = gen_options['string']
        self.__occur = gen_options['occur']
        
    def _visit_root(self, node):
        return node.body.accept(self)

    def _visit_scalar(self, node):
        if isinstance(node, StringSchema):
            return self.__gen_string(node)
        elif isinstance(node, BinarySchema):
            return self.__gen_binary(node)
        elif isinstance(node, BoolSchema):
            return random.choice([True, False])
        elif isinstance(node, NumberSchema):
            if node.is_integer:
                return self.__rand_int(node)
            else:
                return self.__rand_number(node)
        elif isinstance(node, TypeReference):
            return node.body.accept(self)
        elif isinstance(node, UnionSchema):
            return self.__union(node)
        elif isinstance(node, ForeignSchema):
            return ForeignObject()
        return None

    def __rand_int(self, node):
        import sys
        min_i = node.minimum or 0
        max_i = node.maximum or 100
        return random.randint(min_i, max_i)

    def __rand_number(self, node):
        min_i = node.minimum or 0
        max_i = node.maximum or 100.0
        return Decimal(str(random.uniform(min_i, max_i)))
    
    def __gen_string(self, node):
        import sys
        if self.__occur == 'rand':
            min_l = node.minLength or 0
            max_l = node.maxLength or 100
            r = []
            l = random.randint(min_l, max_l)
            for i in range(l):
                r.append(unicode(random.choice(printable)))
            return ''.join(r)
        elif self.__occur == 'empty':
            return u''
        else:
            if 'typical' in node.annotations:
                return random.choice(node.annotations['typical'].value)
            elif 'default' in node.annotations:
                return node.annotations['default'].value
            else:
                return u'string'

    def __gen_binary(self, node):
        min_l = node.minLength or 0
        max_l = node.maxLength or 100
        r = []
        l = random.randint(min_l, max_l)
        for i in range(l):
            r.append(chr(random.randint(0, 127)))
        return ''.join(r)

    def _visit_option(self, node):
        if self.__occur == 'min':
            return _EMPTY
        elif self.__occur == 'once':
            return node.body.accept(self)
        else:
            if random.choice([0, 1]) == 1:
                return _EMPTY
            else:
                return node.body.accept(self)

    def _visit_enum(self, node):
        return random.choice(node.enum)

    def _visit_object(self, node):
        r = {}
        for k, v in node.items():
            if v.optional:
                if self.__occur == 'var':
                    i = random.randint(0, 1)
                    if i == 0:
                        r[k] = v.accept(self)
                elif self.__occur == 'once':
                    r[k] = v.accept(self)
                else:
                    pass
            else:
                r[k] = v.accept(self)
            if (k in r and r[k] == u'string' 
                and v.type == 'string' 
                and self.__gen_str == 'implied'
                and 'default' not in v.annotations 
                and 'typical' not in v.annotations):
                r[k] = k
        for k, v in r.items():
            if v is _EMPTY:
                del r[k]
        return r

    def _visit_array(self, node):
        r = []
        min_i = node.minItems or 0
        max_i = node.maxItems or (len(node.schema_list)+5)
        l = random.randint(min_i, max_i)
        num = 0
        for s in node.schema_list:
            r.append(self.__imply_array_item(s, num))
            num += 1

        if node.repeat and len(r) < l:
            if self.__occur == 'var':
                if l < len(r):
                    r.pop(-1)
                else:
                    for i in range(l - len(r)):
                        r.append(self.__imply_array_item(node.schema_list[-1], num))
                        num += 1
            elif self.__occur == 'min':
                pass
        if node.repeat and (len(r) >= len(node.schema_list)) and self.__occur == 'min':
            r.pop(-1)
        return [i for i in r if i is not _EMPTY]

    def __imply_array_item(self, schema, num):
        value = schema.accept(self)
        if (value == u'string' 
            and schema.type == 'string'
            and self.__gen_str == 'implied'
            and 'default' not in schema.annotations 
            and 'typical' not in schema.annotations):
            if schema.subName:
                return schema.subName
            elif schema.name != 'string':
                return schema.name
            else:
                return u'item %d' % num
        return value

    def _visit_bag(self, node):
        r = []
        for s in self.schema_list:
            r.append(s.accept(self))
        random.shuffle(r)
        return [i for i in r if i is not _EMPTY]

    def _visit_intersection(self, node):
        assert False, u'This method must not called'

    def _visit_union(self, node):
        l = self.__flatten_union(node)
        return random.choice(l).accept(self)

    def __flatten_union(self, s):
        o = [s.left, s.right]
        r = []
        for i in o:
            if isinstance(i, Union):
                for j in self.__flatten_union(i):
                    r.append(j)
            elif isinstance(i, Tag):
                for j in self.__flatten_union(i.body):
                    r.append(TagSchema(i.tag, j))
            else:
                r.append(i)
        return r

    def _visit_updator(self, node):
        assert False, u'This method must not called'

    def _visit_tag(self, node):
        r = node.body.accept(self)
        if r is not _EMPTY:
            return json.tagged(node.tag, r)
        else:
            return _EMPTY

class Url(Builtin):
    def setup(self, pattern):
        self._pattern = pattern

    def execute(self):
        from caty.core.action.parser import url_pattern
        from topdown import as_parser
        try:
            p = as_parser(url_pattern).run(self._pattern)
        except:
            throw_caty_exception(u'BadArg', self._pattern)
        url = []
        for s in p:
            if s == u'*':
                url.append(self.__random_str())
            elif s == u'**':
                url.append(self.__random_str(True))
            else:
                url.append(s)
        return u''.join(url)

    def __random_str(self, includes_slash=False):
        p = [u'']
        seed = u'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_'
        if includes_slash:
            seed += u'///////'
        for i in range(random.choice(range(3,10))):
            c = unicode(random.choice(seed))
            if not (c == u'/' and p[-1] == u'/'):
                p.append(c)
        r = u''.join(p).strip(u'/')
        if not r:
            return self.__random_str(includes_slash)
        else:
            return r

