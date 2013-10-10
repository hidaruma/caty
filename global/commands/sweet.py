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
        reifier = SweetFormReifier()
        # 型の展開を行った後の物に限る。
        try:
            r = reifier.reify_type(module.get_type(name))
        except CatyException:
            throw_caty_exception(u'BadArg', u'not a sweet type: $type', type=self._cdpath)
        return r



class SweetFormReifier(ShallowReifier):

    def reify_type(self, t):
        sr = ShallowReifier.reify_type(self, t)
        return ObjectDumper(sr[u'location']).visit(t.body)

SINGLETON_TYPES = set([u'string-val', u'binary-val', u'number-val', u'boolean-val'])

class ObjectDumper(TypeBodyReifier):
    def __init__(self, location):
        self.default_loc = location
        self._history = {}

    def _visit_root(self, node):
        if u'predefined' in node.annotations:
            return tagged(u'predefined', {u'typeName': node.canonical_name})
        return node.body.accept(self)

    def _visit_union(self, node):
        r = untagged(TypeBodyReifier._visit_union(self, node))
        types = r['specified']
        items = []
        for t in types:
            if tag(t) not in SINGLETON_TYPES:
                throw_caty_exception(u'BadArg', u'not a sweet type')
            else:
                i = untagged(t)
                items.append(tagged(u'item', 
                                   {
                                    u'value': i[u'value'],
                                    u'label': i[u'anno'].get(u'label', UNDEFINED),
                                   }))
        return tagged(u'enum', items)

    def _visit_option(self, node):
        r = node.body.accept(self)
        untagged(r)['optional'] = True
        return r
