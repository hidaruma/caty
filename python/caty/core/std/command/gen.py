#coding:utf-8
from caty.core.command import Builtin
from caty.core.typeinterface import *
from caty.core.schema import TagSchema, StringSchema, NamedSchema, NumberSchema, BoolSchema, BinarySchema, TypeReference, ForeignSchema, UnionSchema, NeverSchema, UndefinedSchema
from caty.core.schema import types as reserved
import caty.jsontools as json
import random
from string import printable
from caty import ForeignObject, UNDEFINED
from decimal import Decimal
from caty.core.language import split_colon_dot_path
from caty.core.exception import throw_caty_exception

class Sample(Builtin):
   
    def setup(self, opts, type_repr):
        self.__type_repr = type_repr
        self.__mod = opts.pop(u'mod')
        self._gen_options = opts

    def execute(self):
        from caty.core.casm.language.schemaparser import typedef
        from caty.core.casm.language.ast import ASTRoot
        from caty.core.schema.base import Annotations
        from topdown import as_parser
        if self.__mod:
            app_name, mod_name, _ = split_colon_dot_path(self.__mod, u'mod')
            if _:
                throw_caty_exception('BadArg', u'$arg', arg=self.__mod)
            if app_name == 'this':
                app = self.current_app
            else:
                app = self.current_app._system.get_app(app_name)
            mod = app._schema_module.get_module(mod_name)
        else:
            mod = self.current_module
        ast = ASTRoot(u'', [], as_parser(typedef).run(self.__type_repr, auto_remove_ws=True), Annotations([]), u'')
        sb = mod.make_schema_builder()
        rr = mod.make_reference_resolver()
        cd = mod.make_cycle_detecter()
        tn = mod.make_type_normalizer()
        ta = mod.make_typevar_applier()
        t = ast.accept(sb).accept(rr).accept(cd).accept(ta).accept(tn).body
        return self._empty_to_undefined(t.accept(DataGenerator(self._gen_options)))

    def _empty_to_undefined(self, o):
        if o is _EMPTY:
            return UNDEFINED
        elif isinstance(o, dict):
            r = {}
            for k, v in o.items():
                r[k] = self._empty_to_undefined(v)
            return r
        elif isinstance(o, list):
            r = []
            for a in o:
                r.append(self._empty_to_undefined(a))
            return r
        elif isinstance(o, json.TaggedValue):
            return json.tagged(o.tag, self._empty_to_undefined(json.untagged(o)))
        else:
            return o

class _EMPTY(object): pass # undefinedではない、存在しない事を表すアトム

class _MaximumRecursionError(Exception):pass

class DataGenerator(TreeCursor):
    def __init__(self, gen_options):
        self.__gen_str = gen_options['string']
        self.__occur = gen_options['occur']
        self.__max_depth = gen_options['max-depth']
        self.cache = {}
        
    def __has_loop_ref(self, node, cache):
        types = (Root, Tag, Ref)
        if isinstance(node, types):
            if node in cache:
                return True
            else:
                cache.add(node)
            return self.__has_loop_ref(node.body, cache)
        elif isinstance(node, Union):
            return self.__has_loop_ref(node.left, cache) or self.__has_loop_ref(node.right, cache)
        elif isinstance(node, Array):
            for i in node:
                if self.__has_loop_ref(i, cache):
                    return True
        elif isinstance(node, Object):
            for k, v in node.items():
                if self.__has_loop_ref(v, cache):
                    return True
        return False

    def __reduce_loop(self, node, cache):
        types = (Root, Ref)
        if isinstance(node, types):
            if node in cache:
                raise _MaximumRecursionError()
            else:
                cache.add(node)
                return self.__reduce_loop(node.body, cache)

        elif isinstance(node, Tag):
            pair = (node.tag, node.body)
            if pair in cache:
                raise _MaximumRecursionError()
            cache.add(pair)
            return node.__class__(node.tag, self.__reduce_loop(node.body, cache))
        elif isinstance(node, Union):
            try:
                return self.__reduce_loop(node.left, cache)
            except:
                return self.__reduce_loop(node.right, cache)
        return node

    def _visit_root(self, node):
        if node not in self.cache:
            self.cache[node] = 0
        loop = self.__has_loop_ref(node, set())
        if loop:
            self.cache[node] += 1
        try:
            if self.cache[node] > self.__max_depth:
                return self.__reduce_loop(node, set()).accept(self)
            return node.body.accept(self)
        except:
            raise
        finally:
            if loop:
                self.cache[node] -= 1

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
        elif isinstance(node, (NeverSchema)) :
            return _EMPTY
        elif isinstance(node, UndefinedSchema):
            return UNDEFINED
        return None


    def __rand_int(self, node):
        import sys
        max_i = node.maximum if node.maximum is not None else 100
        min_i = node.minimum if node.minimum is not None else max_i - 100
        if node.maximum is None:
            max_i = min_i + 100
        return random.randint(min_i, max_i)

    def __rand_number(self, node):
        max_i = node.maximum if node.maximum is not None else 100.0
        min_i = node.minimum if node.minimum is not None else max_i - 100.0
        if node.maximum is None:
            max_i = min_i + 100
        return Decimal(str(random.uniform(min_i, max_i)))
    
    def __gen_string(self, node):
        import sys
        if 'typical' in node.annotations:
            return node.annotations['typical'].value
        elif 'default' in node.annotations:
            return node.annotations['default'].value
        elif self.__gen_str == 'rand':
            min_l = node.minLength or 0
            max_l = node.maxLength or 100
            r = []
            l = random.randint(min_l, max_l)
            for i in range(l):
                r.append(unicode(random.choice(printable)))
            return u''.join(r)
        elif self.__gen_str == 'empty':
            return u''
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
            r[k] = v.accept(self)
            if ((r[k] is not _EMPTY) and r[k] == u'string' 
                and v.type == 'string' 
                and self.__gen_str == 'implied'
                and 'default' not in v.annotations 
                and 'typical' not in v.annotations):
                r[k] = k
        for k, v in r.items():
            if v is _EMPTY:
                del r[k]
        if node.wildcard.type != 'never':
            num = 0
            upper = random.randint(node.minProperties if node.minProperties != -1 else 0, 
                                   node.maxProperties if node.maxProperties != -1 else node.minProperties + 2)
            while len(r) < upper:
                r[u'$random_gen_%d' % num] = node.wildcard.body.accept(self)
                num += 1
        return r

    def _visit_array(self, node):
        r = []
        mandatory = len(node.schema_list)
        if node.repeat:
            mandatory -= 1
        min_i = node.minItems or mandatory
        max_i = node.maxItems or mandatory
        if node.repeat:
            max_i += 5
        l = random.randint(min_i, max_i)
        num = 0
        for s in node.schema_list:
            if num >= l: break
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
        if r:
            while r and r[-1] is _EMPTY:
                r.pop(-1)
        return r

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
        o = random.choice(l)
        while True:
            try:
                return o.accept(self)
            except _MaximumRecursionError:
                if l == [o]:
                    raise _MaximumRecursionError()
                l.remove(o)
                o = random.choice(l)

    def __flatten_union(self, s):
        if isinstance(s, UnionSchema):
            o = [s.left, s.right]
        else:
            o = [s]
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
            return json.TagOnly(node.tag)

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
        r = u''.join(url)
        if r.startswith(u'/'):
            return r
        else:
            return u'/' + r

    def __random_str(self, includes_colon=False):
        p = [u'']
        seed = u'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_'
        if includes_colon:
            seed += u'.....'
        for i in range(random.choice(range(3,10))):
            c = unicode(random.choice(seed))
            if not (c == u'/' and p[-1] == u'/'):
                p.append(c)
        r = u''.join(p).strip(u'/')
        if not r:
            return self.__random_str(includes_colon)
        else:
            return r

