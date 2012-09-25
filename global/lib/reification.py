from caty.command import *
from caty.core.language import split_colon_dot_path
from caty.core.language.util import make_structured_doc
from caty.jsontools import tagged
from caty.util.collection import conditional_dict
from caty.core.casm.cursor.dump import TreeDumper

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
            u'annotations': a._annotations,
        }
        if a.parent:
            r[u'visibleParent'] = a.parent.name
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
                u'minOccurrs': 0 if l.appearance in (u'?', u'*') else 1,
                u'maxOccurrs': u'unbounded' if l.appearance in (u'+', u'*') else 1,
                u'document': make_structured_doc(l.docstring),
                u'targets': map(lambda x:x[0], l.link_to_list)
            })
        return {
            u'name': s.name,
            u'document': make_structured_doc(s.docstr),
            u'annotations': {},
            u'type': s.type.name,
            u'location': self._get_localtion(s),
            u'links': links,
        }

    def reify_resource(self, s):
        return {
                u'name': s.name,
                u'document': make_structured_doc(s.docstring),
                u'pathPattern': s.url_patterns,
                u'annotations': self.reify_annotations(s.annotations),
                u'instances': s.instances,
                u'location': self._get_localtion(s),
        }

    def reify_action(self, s):
        return conditional_dict(lambda k, v: v is not None, {
                u'name': s.name,
                u'document': make_structured_doc(s.docstring),
                u'implemented': s.implemented,
                u'invoker': s.invoker_obj,
                u'annotations': self.reify_annotations(s.annotations),
                u'location': self._get_localtion(s),
                u'pathPattern': s.parent.url_patterns,
                u'produces': reduce(lambda x, y: x+y, [p._next_states for p in s.profiles]),
                u'redirects': reduce(lambda x, y: x+y, [p._redirects for p in s.profiles]),
                u'forwards': reduce(lambda x, y: x+y, [p._relay_list for p in s.profiles]),
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
            u'annotations': self.reify_annotations(m.annotations),
            u'document': make_structured_doc(m.docstring),
            u'location': self._get_localtion(m),
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
            u'annotations': self.reify_annotations(m.annotations),
            u'location': self._get_localtion(m),
        }

    def reify_class(self, c):
        return {
            u'document': make_structured_doc(c.docstring),
            u'annotations': self.reify_annotations(c.annotations),
            u'name': c.name,
            u'arg0': self._dump_schema(c._clsrestriction),
            u'location': self._get_localtion(c),
        }

    def reify_type(self, t):
        return {
            u'name': t.name,
            u'document': make_structured_doc(t.docstring),
            u'deprecated': 'deprecated' in t.annotations,
            u'annotations': self.reify_annotations(t.annotations),
            u'typeParams': [self.reify_type_param(p) for p in t.type_params],
            u'location': self._get_localtion(t),
        }

    def reify_command(self, c):
        return {
            u'name': c.name,
            u'document': make_structured_doc(c.docstring),
            u'annotations': self.reify_annotations(c.annotations),
            u'implemented': c.implemented,
            u'profile': self._make_profile(c),
            u'typeParams': [self.reify_type_param(p) for p in c.type_params],
            u'location': self._get_localtion(c),
        }

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
            o['exception'] = exc
            sig = []
            if p.signal_schema.type != 'never':
                for e in self._flatten(p.signal_schema):
                    sig.append(self._dump_schema(e))
            if u'__only' in p.signal_schema.annotations:
                sig = tagged(u'only', sig)
            else:
                sig = tagged(u'likely', sig)
                o['signal'] = sig
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

class FullReifier(ShallowReifier):
    def reify_type(self, t):
        sr = ShallowReifier.reify_type(self, t)
        sr['body'] = TypeBodyReifier().reify(t.body)
        return tagged(u'type', sr)

class TypeBodyReifier(object):
    def reify(self, t):
        return TreeDumper().visit(t)

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
