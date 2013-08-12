#coding:utf-8
from caty.core.command import Builtin
from caty.core.typeinterface import *
from caty.core.schema import TagSchema, StringSchema, NamedSchema, NumberSchema, BoolSchema, BinarySchema, TypeReference, ForeignSchema, UnionSchema, NeverSchema, UndefinedSchema, ArraySchema, ObjectSchema, TypeVariable
from caty.core.schema import types as reserved
import caty.jsontools as json
import random
from string import printable
from caty import ForeignObject, UNDEFINED
from decimal import Decimal
from caty.core.language import split_colon_dot_path
from caty.core.exception import throw_caty_exception
from caty.core.casm.cursor.dump import TreeDumper
from caty.core.typeinterface import flatten_union

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
            mod = self.current_module.schema_finder
        ast = ASTRoot(u'', [], as_parser(typedef).run(self.__type_repr, auto_remove_ws=True), Annotations([]), u'')
        sb = mod.make_schema_builder()
        rr = mod.make_reference_resolver()
        cd = mod.make_cycle_detecter()
        ta = mod.make_typevar_applier()
        tn = mod.make_type_normalizer()
        sb._root_name = u'gen:sample'
        t = ast.accept(sb)
        t = t.accept(rr)
        t = t.accept(cd)
        t = t.accept(ta)
        t = t.accept(tn).body
        re = ReferenceExpander(self._gen_options)
        t = re.expand(t)
        data = t.accept(DataGenerator(self._gen_options))
        return self._empty_to_undefined(data)

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

from caty.core.casm.cursor.base import SchemaBuilder, apply_annotation
class ReferenceExpander(SchemaBuilder):
    def __init__(self, gen_options):
        self.__max_depth = gen_options['max-depth']
        self.__max_node_num = gen_options['max-nodes']
        self.__max_branches = gen_options['max-branches']
        self._history = {}

    def expand(self, type):
        count = 0
        while count < self.__max_depth:
            type = type.accept(self)
            self._history = {}
            count += 1
            nc = NodeCounter()
            type.accept(nc)
            if nc.node_num > self.__max_node_num:
                break
        return type.accept(ReferenceDeleter(None))

    def _visit_root(self, node):
        return node.body.accept(self)

    @apply_annotation
    def _visit_scalar(self, node):
        if isinstance(node, TypeReference):
            if node.canonical_name in self._history:
                return node
            else:
                self._history[node.canonical_name] = True
                return node.body.accept(self)
        if isinstance(node, TypeVariable):
            if node._schema:
                return node._schema.accept(self)
            if node._default_schema:
                return node._default_schema.accept(self)
        return node

    @apply_annotation
    def _visit_object(self, node):
        o = {}
        for k, v in node.items():
            h = {}
            h.update(self._history)
            old = self._history
            self._history = h
            o[k] = v.accept(self)
            self._history = old
        w = node.wildcard.accept(self)
        return ObjectSchema(o, w, node.options)

    @apply_annotation
    def _visit_array(self, node):
        r = []
        for c in node:
            h = {}
            h.update(self._history)
            old = self._history
            self._history = h
            r.append(c.accept(self))
            self._history = old
        return ArraySchema(r, node.options)

    @apply_annotation
    def _visit_bag(self, node):
        r = []
        for c in node:
            h = {}
            h.update(self._history)
            old = self._history
            self._history = h
            r.append(c.accept(self))
            self._history = old
        return BagSchema(r, node.options)

    def _visit_union(self, node):
        nodes = list(self.__flatten_union(node))
        new_nodes = random.sample(nodes, min(self.__max_branches, len(nodes)))
        return reduce(lambda x, y: UnionSchema(x, y), [n.accept(self) for n in new_nodes])

    def __flatten_union(self, node):
        if isinstance(node, UnionSchema):
            for l in self.__flatten_union(node.left):
                yield l
            for r in self.__flatten_union(node.right):
                yield r
        else:
            yield node

class ReferenceDeleter(SchemaBuilder):
    def _visit_scalar(self, node):
        if isinstance(node, TypeReference):
            return NeverSchema()
        return node

    def _visit_root(self, node):
        assert False, u'This is a bug'

    def _visit_union(self, node):
        l = node.left.accept(self)
        r = node.left.accept(self)
        if l.type == 'never':
            return r
        elif r.type == 'never':
            return l
        else:
            node._left = l
            node._right = r
            return node

class _EMPTY(object): pass # undefinedではない、存在しない事を表すアトム

class _MaximumRecursionError(Exception):pass

class NodeCounter(TreeCursor):
    def __init__(self):
        self.node_num = 0

    def _visit_scalar(self, node):
        if node.type != 'never':
            self.node_num += 1

    def _visit_tag(self, node):
        node.body.accept(self)

    _visit_option = _visit_tag

    def _visit_union(self, node):
        old = self.node_num
        node.left.accept(self)
        l = self.node_num
        self.node_num = old
        node.right.accept(self)
        r = self.node_num
        self.node_num = max(l, r)

    def _visit_object(self, node):
        num = 0
        for k, v in node.items():
            v.accept(self)
            num += 1
        if node.wildcard.type not in ('never', 'undefined'):
            node.wildcard.accept(self)


    def _visit_array(self, node):
        for v in node:
            v.accept(self)

    def _visit_bag(self, node):
        for v in node:
            v.accept(self)

    def _visit_enum(self, node):
        self.node_num += 1

class DataGenerator(TreeCursor):
    def __init__(self, gen_options):
        self.__gen_str = gen_options['string']
        self.__occur = gen_options['occur']
        self.cache = {}
        self.depth = 0
        
    def __has_loop_ref(self, node, cache):
        if isinstance(node, (Root, Ref)):
            print node
            assert False, u'This is a bug'
        elif isinstance(node, Union):
            for n in flatten_union(node, debug=True):
                if self.__has_loop_ref(n, cache):
                    return True
        elif isinstance(node, Array):
            for i in node:
                if self.__has_loop_ref(i, cache):
                    return True
        elif isinstance(node, Object):
            for k, v in node.items():
                if self.__has_loop_ref(v, cache):
                    return True
        elif isinstance(node, (Tag, Optional)):
            return self.__has_loop_ref(node.body, cache)
        return False

    def __reduce_loop(self, node, cache):
        types = (Root, Ref)
        if isinstance(node, types):
            if node.canonical_name in cache:
                raise _MaximumRecursionError()
            else:
                cache.add(node.canonical_name)
                return self.__reduce_loop(node.body, cache)

        elif isinstance(node, Tag):
            n = node.body.canonical_name
            if n in cache:
                raise _MaximumRecursionError()
            cache.add(n)
            return node.__class__(node.tag, self.__reduce_loop(node.body, cache))
        elif isinstance(node, Union):
            for n in flatten_union(node, cache):
                try:
                    return self.__reduce_loop(n, cache)
                except:
                    return self.__reduce_loop(node.right, cache)
        elif isinstance(node, Optional):
            return self.__reduce_loop(node.body, cache)
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
        elif isinstance(node, TypeVariable):
            if node._schema:
                return node._schema.accept(self)
            if node._default_schema:
                return node._default_schema.accept(self)
            throw_caty_exception(u'TypeParamNotApplied', node.name)
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
            return random.choice(node.annotations['typical'].value)
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
        def generate(k, v):
            d = v.accept(self)
            if ((d is not _EMPTY) and d == u'string' 
                and v.type == 'string' 
                and self.__gen_str == 'implied'
                and 'default' not in v.annotations 
                and 'typical' not in v.annotations):
                return k
            else:
                return d
        r = {}
        for k, v in node.items():
            r[k] = generate(k, v)
        for k, v in r.items():
            if v is _EMPTY:
                del r[k]
        # withの項目を埋める
        for k, v in r.items():
            mandatory = set()
            a = node[k].annotations
            self.__check_with_without(a, u'with', mandatory)
            for m in mandatory:
                while r.get(m) in (None, _EMPTY):
                    r[m] = generate(m, node[m])
        # withoutの項目を削除
        for k, v in r.items():
            reject = set()
            a = node[k].annotations
            self.__check_with_without(a, u'without', reject)
            for j in reject:
                if j in r:
                    if random.choice([True, False]):
                        del r[j]
                    else:
                        if k in r:
                            del r[k]
        # withの対象のない項目を削除
        deleted = [None]
        while deleted:
            deleted = []
            for k, v in r.items():
                mandatory = set()
                a = node[k].annotations
                self.__check_with_without(a, u'with', mandatory)
                for m in mandatory:
                    if m not in r:
                        if k in r:
                            del r[k]
                            deleted.append(k)
            if not deleted:
                break

        if node.wildcard.type not in ('never', 'undefined') and self.__occur != u'min':
            num = 0
            mi = node.minProperties if node.minProperties != -1 else len(r)
            ma = node.maxProperties if node.maxProperties != -1 else mi + 2
            upper = random.randint(mi, ma)
            while len(r) < upper:
                r[u'$random_gen_%d' % num] = node.wildcard.body.accept(self)
                num += 1
        return r

    def __check_with_without(self, a, t, ls):
        w = a.get(t)
        if w:
            if isinstance(w.value, basestring):
               ls.add(w.value)
            else:
                mode, val = json.split_tag(w.value)
                if mode == '_AND':
                  for v in val:
                      ls.add(v)
                else:
                    ls.add(random.choice(val))

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
        l = [i for i in self.__flatten_union(node) if i.type != 'never']
        if not l:
            return _EMPTY
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
            if node.tag in ('*', '*!'):
                return json.tagged(u'auto-gen-tag', r)
            else:
                if not isinstance(node.tag, basestring):
                    return json.tagged(node.tag.accept(self).replace('\n', '').replace('\r', '').replace(' ', ''), r)
                return json.tagged(node.tag, r)
        else:
            if not isinstance(node.tag, basestring):
                return json.TagOnly(node.tag.accept(self).replace('\n', '').replace('\r', '').replace(' ', ''))
            if isinstance(node.body, Optional):
                return _EMPTY
            return json.TagOnly(node.tag)

class Url(Builtin):
    def setup(self, pattern):
        self._pattern = pattern

    def execute(self):
        from caty.core.action.parser import url_pattern
        from caty.core.action.resource import split_url_pattern
        from topdown import as_parser
        import random
        try:
            p = as_parser(url_pattern).run(random.choice(split_url_pattern(self._pattern)))
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

class ObjectDumper(TreeCursor):

    def _visit_root(self, node):
        return node.body.accept(self)

    def _visit_scalar(self, node):
        if isinstance(node, (TypeReference)):
            if node.canonical_name in self._history:
                raise
            self._history[node.canonical_name] = True
            return node.accept(self)
        else:
            r = {u'attributes': {}}
            r['attributes'].update(node.options)
            r['typeName'] = node.name
            return r

    def _visit_option(self, node):
        r = node.body.accept(self)
        r['optional'] = True
        return r

    def _visit_enum(self, node):
        e = map(self._to_str, node.enum)
        return {'attributes': {}, 'typeName': u'enum', 'values': e}

    def _to_str(self, e):
        if isinstance(e, unicode):
            return '"%s"' % e
        elif isinstance(e, bool):
            return str(e).lower()
        else:
            return str(e)

    def _visit_object(self, node):
        r = {u'attributes': {}, u'typeName': u'object', u'items': {}}
        for k, v in node.items():
            r['items'][k] = v.accept(self)
        r['items']['*'] = node.wildcard.accept(self)
        r['attributes'].update(node.options)
        return r

    def _visit_array(self, node):
        r = {u'attributes': {}, u'typeName': u'array', u'items': []}
        for v in node:
            r
        r['attributes'].update(node.options)
        return 

    def __vist_iter(self, node, r):

        return r

    def _visit_bag(self, node):
        buff = ['{[']
        self.__vist_iter(node, buff)
        buff.append(']}')
        self._process_option(node, buff)
        return ''.join(buff)

    def _visit_intersection(self, node):
        l = node.left.accept(self)
        r = node.right.accept(self)
        buff = [l + ' & ' + r]
        buff.insert(0, u'(')
        buff.insert(2, u')')
        self._process_option(node, buff)
        return u''.join(buff)

    def _visit_union(self, node):
        ls = self.__flatten_union(node)
        buff = [u'(']
        for n in ls:
            buff.append(n.accept(self))
            buff.append(u' | ')
        buff.pop(-1)
        buff.append(u')')
        self._process_option(node, buff)
        return u''.join(buff)

    def __flatten_union(self, node):
        res = []
        if not isinstance(node, Union):
            return [node]
        l = dereference(node.left)
        if isinstance(l, Union):
            res.extend(self.__flatten_union(l))
        else:
            res.append(node.left)
        r = dereference(node.right)
        if isinstance(r, Union):
            res.extend(self.__flatten_union(r))
        else:
            res.append(node.right)
        return res


    def _visit_updator(self, node):
        l = node.left.accept(self)
        r = node.right.accept(self)
        buff = [l + ' ++ ' + r]
        buff.insert(0, u'(')
        buff.insert(2, u')')
        self._process_option(node, buff)
        return u''.join(buff)

    def _visit_tag(self, node):
        t = node.tag
        s = node.body.accept(self)
        buff = ['@' + t + ' ' + s]
        self._process_option(node, buff)
        return u''.join(buff)

    def _visit_pseudo_tag(self, node):
        s = node.body.accept(self)
        buff = [ '@?("%s": %s) %s' % (node._name, 
                                    json.pp(node._value),
                                    s)]
        self._process_option(node, buff)
        return u''.join(buff)

    def _visit_kind(self, node):
        return u'$kind$'



