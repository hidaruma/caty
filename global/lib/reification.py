# coding:utf-8
from caty.command import *
from caty.core.language import split_colon_dot_path
from caty.core.language.util import make_structured_doc
from caty.jsontools import tagged, split_tag, pp
from caty.util.collection import conditional_dict
from caty.core.typeinterface import *
from caty.core.casm.cursor.dump import TreeDumper
from caty.core.casm.language.schemaparser import RESERVED

_modemap = {
    u'reads': u'read',
    u'updates': u'update',
    u'uses': u'use'
}

class ShallowReifier(object):
    def _get_localtion(self, obj):
        if obj.app:
            a = obj.app.name
        else:
            a = u'caty'
        aname, mname, name = split_colon_dot_path(a + '::' + obj.canonical_name)
        if name and not mname:
            mname = name
            name = None
        pname = None
        cname = None
        if mname and '.' in mname:
            pname, mname = mname.rsplit('.', 1)
        if not name:
            mname = None
        if name and '.' in name:
            cname, name = name.rsplit('.', 1)
        if aname:
            aname += '::'
        if pname:
            pname += '.'
        else:
            pname = u''
        if mname:
            mname += ':'
        if cname:
            cname += u'.'
        name = None
        return conditional_dict(lambda k, v: v is not None,
            {
                u'app': aname,
                u'pkg': pname,
                u'mod': mname,
                u'cls': cname,
            })

    def reify_app(self, a):
        r = {
            u'document': conditional_dict(lambda k, v: v is not None, description=a.description, moreDescription=a.more_description),
            u'name': a.name,
            u'group': a._group.name if a._group else None,
            u'path': a.web_path,
            u'anno': a._annotations,
            u'loaded': a._loaded,
        }
        if a.parent:
            r[u'visibleParent'] = a.parent.name
        if a.deprecated:
            r[u'anno'][u'deprecated'] = a.deprecated
        return r

    def reify_state(self, s):
        tmap = {
            u'embeded-link':  u'embedded',
            u'additional-link': u'additional',
            u'indef-link': u'indef'
        }
        links = {}
        for l in s.links:
            links[l.trigger] = tagged(u'link', {
                u'name': l.trigger,
                u'becoming': tmap[l.type],
                u'minOccurs': 0 if l.appearance in (u'?', u'*') else 1,
                u'maxOccurs': u'unbounded' if l.appearance in (u'+', u'*') else 1,
                u'document': make_structured_doc(l.docstring),
                u'targets': map(lambda x:x[0], l.link_to_list)
            })
        return {
            u'name': s.name,
            u'document': make_structured_doc(s.docstring),
            u'anno': self.reify_annotations(s.annotations),
            u'type': s.type.name,
            u'location': self._get_localtion(s),
            u'links': links,
            u'forWhom': s.actor_names,
        }

    def reify_resource(self, s):
        return {
                u'name': s.name,
                u'document': make_structured_doc(s.docstring),
                u'pathPattern': s.url_patterns,
                u'anno': self.reify_annotations(s.annotations),
                u'instances': s.instances,
                u'location': self._get_localtion(s),
        }

    def reify_action(self, s):
        return conditional_dict(lambda k, v: v is not None, {
                u'name': s.name,
                u'document': make_structured_doc(s.docstring),
                u'implemented': s.implemented,
                u'invoker': s.invoker_obj,
                u'anno': self.reify_annotations(s.annotations),
                u'location': self._get_localtion(s),
                u'pathPattern': s.parent.url_patterns,
                u'produces': reduce(lambda x, y: x+y, [p._next_states for p in s.profiles], []),
                u'redirects': reduce(lambda x, y: x+y, [p._redirects for p in s.profiles], []),
                u'forwards': [], 
                u'profile': self._reify_action_profile(s),
        })

    def _reify_action_profile(self, act):
        return {
            u'opts': u'{}' if act.opts is None else self._dump_schema(act.opts),
            u'exception': tagged(u'likely', []),
            u'signal': tagged(u'likely', []),
            u'internalInput': u'any' if act.profiles._input_type is None else self._dump_schema(act.profiles._input_type)
        }

    def reify_module(self, m):
        if m.type == 'cara':
            p = u'actions'
        else:
            p = u'schemata'
        return {
            u'name': m.name,
            u'place': p,
            u'syntax': m.type,
            u'literate': m.literate,
            u'anno': self.reify_annotations(m.annotations),
            u'document': make_structured_doc(m.docstring),
            u'location': self._get_localtion(m),
            u'loadOn': m.timing,
            u'loaded': m.loaded,
        }

    def reify_package(self, m):
        if m.type == 'cara':
            p = u'actions'
        else:
            p = u'schemata'
        return {
            u'name': m.name,
            u'place': p,
            u'document': conditional_dict(lambda k,v: v is not None, {'description': m.docstring, 'moreDescription': m.more_docstring}),
            u'anno': self.reify_annotations(m.annotations),
            u'location': self._get_localtion(m),
        }

    def reify_class(self, c):
        return {
            u'document': make_structured_doc(c.docstring),
            u'anno': self.reify_annotations(c.annotations),
            u'name': c.name,
            u'arg0': self._dump_schema(c._clsrestriction),
            u'location': self._get_localtion(c),
        }

    def reify_type(self, t):
        return {
            u'name': t.name,
            u'document': make_structured_doc(t.docstring),
            u'deprecated': 'deprecated' in t.annotations,
            u'anno': self.reify_annotations(t.annotations),
            u'typeParams': [self.reify_type_param(p) for p in t.type_params],
            u'location': self._get_localtion(t),
        }

    def reify_command(self, c):
        return {
            u'name': c.name,
            u'document': make_structured_doc(c.docstring),
            u'anno': self.reify_annotations(c.annotations),
            u'implemented': c.implemented,
            u'profile': self._make_profile(c),
            u'typeParams': [self.reify_type_param(p) for p in c.type_params],
            u'location': self._get_localtion(c),
            u'facilityUsages': self.reifiy_facility_usages(c.profiles[0], c.defined_application),
        }

    def reifiy_facility_usages(self, profile, app):
        r = {}
        for mode, fcl in profile.facilities:
            entry = app._facility_classes.get(fcl.name, [None, None]) # system facility
            if len(entry) == 2:
                o = {
                    u'registeredName': fcl.name,
                    u'name': fcl.alias or fcl.name,
                    u'mode': _modemap[mode],
                    u'userParam': fcl.param,
                }
            else:
                o = {
                    u'registeredName': entry[3],
                    u'name': fcl.alias or fcl.name,
                    u'entityName': fcl.alias or fcl.name,
                    u'mode': _modemap[mode],
                    u'userParam': entry[2],
                }
            r[fcl.alias or fcl.name] = o
        return r

    def reify_type_param(self, p):
        from caty.util.collection import conditional_dict
        from caty.jsontools import tagged
        return tagged(u'param', conditional_dict(
            lambda k, v: v is not None,
            name = p.var_name,
            default = p.default,
            kind = None
        ))

    def _make_profile(self, c):
        r = []
        for p in c.profiles:
            o = {
                u'arg0': self._dump_schema(p.arg0_schema),
                u'input': self._dump_schema(p.in_schema),
                u'output': self._dump_schema(p.out_schema),
                u'opts': u'{}',
                u'args': u'[]',
            }
            exc = []
            if p.throw_schema.type != 'never':
                for e in self._flatten(p.throw_schema):
                    exc.append(self._dump_schema(e))
            if u'__only' in p.throw_schema.annotations:
                exc = tagged(u'only', exc)
            else:
                exc = tagged(u'likely', exc)
            o[u'exception'] = exc
            sig = []
            if p.signal_schema.type != 'never':
                for e in self._flatten(p.signal_schema):
                    sig.append(self._dump_schema(e))
            if u'__only' in p.signal_schema.annotations:
                sig = tagged(u'only', sig)
            else:
                sig = tagged(u'likely', sig)
                o[u'signal'] = sig
            if p.opts_schema.type != 'null':
                o[u'opts'] = self._dump_schema(p.opts_schema)
            if p.args_schema.type != 'null':
                o[u'args'] = self._dump_schema(p.args_schema)
            r.append(o)
        return r[0]

    def _flatten(self, o):
        from caty.core.typeinterface import Union
        if isinstance(o, Union):
            for r in self._flatten(o.left):
                yield r
            for r in self._flatten(o.right):
                yield r
        else:
            yield o

    def _dump_schema(self, o):
        if o is None:
            return None
        td = TreeDumper(True)
        return td.visit(o)

    def reify_annotations(self, a):
        r = {}
        for an in a.values():
            r[an.name] = an.value
        return r

class StringReifier(ShallowReifier):
    def reify_type(self, t):
        sr = ShallowReifier.reify_type(self, t)
        sr[u'body'] = TreeDumper().visit(t.body)
        return tagged(u'type', sr)

class FullReifier(ShallowReifier):
    def reify_type(self, t):
        sr = ShallowReifier.reify_type(self, t)
        sr[u'body'] = TypeBodyReifier(sr[u'location']).visit(t.body)
        return tagged(u'type', sr)

from caty.core.spectypes import UNDEFINED

def format_result(t):
    def _format_result(f):
        def __format_result(*args, **kwds):
            r = f(*args, **kwds)
            r = conditional_dict(lambda k, v: v is not UNDEFINED, r)
            return tagged(t, r)
        return __format_result
    return _format_result

class TypeBodyReifier(TreeCursor):
    def __init__(self, default_loc):
        self.default_loc = default_loc
        self.root_found = False

    def _extract_common_data(self, node):
        r = {}
        for k, v in node.options.items():
            if k != 'pseudoTag':
                r[k] = v
        if isinstance(node, Root):
            r[u'location'] = node.canonical_name
        elif isinstance(node, Ref):
            r[u'location'] = node.module.canonical_name + ':' + node.name
        r['anno'] = self.reify_annotations(node.annotations)
        return r

    def reify_annotations(self, a):
        r = {}
        for an in a.values():
            r[an.name] = an.value
        return r

    @format_result(u'params')
    def __reify_params(self, params):
        r = []
        for p in params:
            r.append({
                u'name': p.name,
                u'kind':  UNDEFINED,
                u'default': p.default.accept(self) if p.default else UNDEFINED
            })
        return r

    @format_result(u'kind')
    def __reify_kind(self, node):
        # XXX:仕様の問題: kindへの参照を表現するオブジェクトがない
        return {
            'name': node.name
        }

    def _visit_root(self, node):
        if not self.root_found:
            self.root_found = True
            r = self._extract_common_data(node)
            r[u'params'] = self.__reify_params(node._type_params)
            r[u'expr'] = node.body.accept(self)
            return tagged(u'type', r)
        else:
            return node.body.accept(self)

    def _visit_symbol(self, node):
        if node.name not in RESERVED:
            if u'predefined' in node.annotations:
                return self.__reify_predefined(node)
            return self.__reify_ref(node)
        else:
            return self.__reify_builtin(node)

    @format_result(u'builtin')
    def __reify_builtin(self, node):
        r = self._extract_common_data(node)
        r[u'typeName'] = node.name
        return r

    @format_result(u'predefined')
    def __reify_predefined(self, node):
        r = self._extract_common_data(node)
        r[u'typeName'] = node.canonical_name
        return r
    
    @format_result(u'type-ref')
    def __reify_ref(self, node):
        r = self._extract_common_data(node)
        r[u'ref'] = node.name
        #if node.body.kind:
        #    r[u'kind'] = self.__reify_kind(node.body.kind)
        return r

    @format_result(u'optional')
    def _visit_option(self, node):
        return {'operand': node.body.accept(self)}

    def _visit_scalar(self, node):
        r = self._extract_common_data(node)
        r[u'value'] = node.value
        if isinstance(node.value, unicode):
            return tagged(u'string-val', r)
        elif isinstance(node.value, bool):
            return tagged(u'boolean-val', r)
        elif isinstance(node.value, str):
            return tagged(u'binary-val', r)
        else:
            return tagged(u'number-val', r)

    @format_result(u'object-of')
    def _visit_object(self, node):
        r = self._extract_common_data(node)
        r[u'specified'] = {}
        for k, v in node.items():
            r[u'specified'][k] = v.accept(self)
        r[u'additional'] = node.wildcard.accept(self)
        return r

    @format_result(u'array-of')
    def _visit_array(self, node):
        r = self._extract_common_data(node)
        r[u'specified'] = []
        for v in node:
            r[u'specified'].append(v.accept(self))
        if r[u'repeat']:
            r[u'additional'] = json.tagged(u'optional', {u'operand': r[u'specified'].pop(-1)})
            del r[u'repeat']
        else:
            r[u'additional'] = tagged(u'builtin', {'typeName': u'never'})
        return r

    @format_result(u'bag')
    def _visit_bag(self, node):
        items = []
        r = self._extract_common_data(node)
        for i in node:
            o = i.accept(self)
            t, s = split_tag(o)
            mi = s.pop('minCount', 1)
            ma = s.pop('maxCount', u'unbounded')
            items.append(tagged('bag-item', {'minOccurs': mi, 'maxOccurs': ma, 'type': tagged(t, s)}))
        r[u'items'] = items
        return r

    @format_result(u'intersection')
    def _visit_intersection(self, node):
        return {'operands': [node.left.accept(self), node.right.accept(self)]}

    @format_result(u'union')
    def _visit_union(self, node):
        spec = list(self.__flatten_union(node))
        return {'specified': spec, 'additional': tagged(u'builtin', {'typeName': u'never'})}

    def __flatten_union(self, node):
        if isinstance(node, Union):
            for l in self.__flatten_union(node.left):
                yield l
            for r in self.__flatten_union(node.right):
                yield r
        else:
            yield node.accept(self)

    @format_result(u'merge')
    def _visit_updator(self, node):
        return {'operands': [node.left.accept(self), node.right.accept(self)]}

    @format_result(u'tagged')
    def _visit_tag(self, node):
        return {'tag': node.tag, 'content': node.body.accept(self)}

    def _visit_pseudo_tag(self, node):
        raise NotImplementedError(u'{0}._visit_pseudo_tag'.format(self.__class__.__name__))

    def _visit_function(self, node):
        raise NotImplementedError(u'{0}._visit_function'.format(self.__class__.__name__))

    def _visit_kind(self, node):
        raise NotImplementedError(u'{0}._visit_kind'.format(self.__class__.__name__))

    def _visit_unary_op(self, node):
        res = node.body.accept(self)
        if node.operator == 'extract':
            return json.tagged(u'extract', {u'operands': {u'path':node.path.to_str() , u'expr':res}})
        return json.tagged(node.operator, {u'operand': res})

class SafeReifier(Command):
    def setup(self, opts, cdpath):
        self._cdpath = cdpath
        self._safe = opts.get('safe', False)

    def execute(self):
        from caty.core.exception import SystemResourceNotFound
        from caty import UNDEFINED
        try:
            return self._execute()
        except SystemResourceNotFound:
            if self._safe:
                return UNDEFINED
            raise

class SafeReifierWithDefaultApp(SafeReifier):
    def setup(self, opts, cdpath=u'this::'):
        self._cdpath = cdpath
        self._safe = opts.get('safe', False)
        self._rec = opts.get('rec', False)




class FormReifier(ShallowReifier):

    def reify_type(self, t):
        sr = ShallowReifier.reify_type(self, t)
        if u'predefined' in t.annotations:
            sr[u'body'] = tagged(u'predefined', {u'typeName': t.canonical_name})
        else:
            sr[u'body'] = ObjectDumper(sr[u'location']).visit(t.body)
        return tagged(u'type', sr)

class ObjectDumper(TypeBodyReifier):
    def __init__(self, location):
        self.default_loc = location
        self._history = {}

    def _visit_root(self, node):
        if u'predefined' in node.annotations:
            return tagged(u'predefined', {u'typeName': node.canonical_name})
        return node.body.accept(self)

    def _visit_symbol(self, node):
        from caty.core.schema import TypeReference
        if isinstance(node, (TypeReference)):
            if node.canonical_name in self._history:
                raise Exception(u'To reify recursive type definition is not implemented')
            self._history[node.canonical_name] = True
            try:
                return node.body.accept(self)
            finally:
                del self._history[node.canonical_name]
        else:
            return TypeBodyReifier._visit_symbol(self, node)




