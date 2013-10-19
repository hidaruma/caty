from reification import *
from caty.jsontools import tag, untagged, tagged

class ReifyType(SafeReifier):
    def setup(self, opts, arg):
        SafeReifier.setup(self, opts, arg)

    def _execute(self):
        system = self.current_app._system
        app_name, module_name, name = split_colon_dot_path(self._cdpath)
        if not app_name or app_name == 'this':
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        if not name:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        module = app._schema_module.get_module(module_name)
        attrs = set()
        for k, v in app._schema_module.get_module(u'sweet').get_type(u'SweetAttributes').items():
            attrs.add(k)
        for k, v in app._schema_module.get_module(u'sweet').get_type(u'SweetItemAttributes').items():
            attrs.add(k)
        reifier = SweetFormReifier(attrs)
        # 型の展開を行った後の物に限る。
        try:
            r = reifier.reify_type(module.get_type(name))
        except CatyException as e:
            throw_caty_exception(u'BadArg', u'not a sweet type: $type', type=self._cdpath)
        return r


class SweetFormReifier(ShallowReifier):
    def __init__(self, sweet_attrs):
        ShallowReifier.__init__(self)
        self.SWEET_ATTRIBUTES = frozenset(sweet_attrs)

    def reify_type(self, t):
        if self._is_predefined(t):
            return tagged(u'predefined', {u'typeName': t.canonical_name})
        sr = ShallowReifier.reify_type(self, t)
        return ObjectDumper(sr[u'location'], self.SWEET_ATTRIBUTES).visit(t.body)

    def _is_predefined(self, node):
        if u'predefined' in node.annotations:
            return True
        elif isinstance(node.body, (Root, Ref)):
            return self._is_predefined(node.body)
        return False

SINGLETON_TYPES = set([u'string-val', u'binary-val', u'number-val', u'boolean-val'])
class ObjectDumper(TypeBodyReifier):
    def __init__(self, location, sweet_attrs):
        self.default_loc = location
        self._history = {}
        self.SWEET_ATTRIBUTES = sweet_attrs

    def _extract_common_data(self, node):
        r = TypeBodyReifier._extract_common_data(self, node)
        anno = r.pop(u'anno', {})
        for k, v in anno.items():
            if k in self.SWEET_ATTRIBUTES:
                r[k] = v
        return r

    def _visit_root(self, node):
        if u'predefined' in node.annotations:
            return tagged(u'predefined', {u'typeName': node.canonical_name})
        return node.body.accept(self)

    def _visit_union(self, node):
        r = untagged(TypeBodyReifier._visit_union(self, node))
        types = r[u'specified']
        items = []
        for t in types:
            if tag(t) not in SINGLETON_TYPES:
                throw_caty_exception(u'BadArg', u'not a sweet type')
            else:
                i = untagged(t)
                v = {u'value': i[u'value']}
                if u'label' in i.get(u'anno', {}):
                    v[u'label'] = i[u'anno'][u'label']
                items.append(tagged(u'item', v))
        return tagged(u'enum', items)

    def _visit_bag(self, node):
        r = untagged(TypeBodyReifier._visit_bag(self, node))
        types = r[u'items']
        items = []
        for bagitem in types:
            i = untagged(bagitem)
            t = i[u'type']
            if tag(t) not in SINGLETON_TYPES:
                throw_caty_exception(u'BadArg', u'not a sweet type')
            else:
                o = untagged(t)
                v = {u'value': o[u'value']}
                if u'label' in o[u'anno']:
                    v[u'label'] = o[u'anno'][u'label']
                v[u'minOccurs'] = i[u'minOccurs']
                v[u'maxOccurs'] = i[u'maxOccurs']
                items.append(tagged(u'multi-item', v))
        return tagged(u'multi-enum', items)

    def _visit_option(self, node):
        r = node.body.accept(self)
        b = untagged(r)
        if isinstance(b, dict):
            b[u'optional'] = True
        else:
            for i in b:
                untagged(i)[u'optional'] = True
        return r

    def _visit_symbol(self, node):
        from caty.core.schema import TypeReference, TypeVariable
        if isinstance(node, (TypeReference)):
            if node.canonical_name in self._history:
                throw_caty_exception(u'BadArg', u'not a sweet type')
            self._history[node.canonical_name] = True
            try:
                return node.body.accept(self)
            finally:
                del self._history[node.canonical_name]
        elif isinstance(node, TypeVariable):
            throw_caty_exception(u'BadArg', u'not a sweet type')
        else:
            return TypeBodyReifier._visit_symbol(self, node)


    @format_result(u'array-of')
    def _visit_array(self, node):
        r = self._extract_common_data(node)
        r[u'specified'] = []
        for v in node:
            r[u'specified'].append(v.accept(self))
        if r[u'repeat']:
            rep = r[u'specified'].pop(-1)
            untagged(rep)[u'optional'] = True
            r[u'additional'] = rep
            del r[u'repeat']
        else:
            r[u'additional'] = tagged(u'builtin', {'typeName': u'never'})
        return r


