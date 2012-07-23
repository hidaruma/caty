from caty.command import *
from caty.core.language import split_colon_dot_path
from caty.core.language.util import make_structured_doc
from caty.jsontools import tagged

class ShallowReifier(object):
    def reify_app(self, a):
        r = {
            'document': make_structured_doc(a.description),
            'name': a.name,
            'group': a._group.name if a._group else None,
            'path': a.web_path,
            'deprecated': a.deprecated,
        }
        if a.parent:
            r['visibleParent'] = a.parent.name
        return r

    def reify_state(self, s):
        tmap = {
            'embeded-link':  u'embedded',
            'additional-link': u'additional',
            'no-care-link': u'indef'
        }
        links = {}
        for l in s.links:
            links[l.trigger] = tagged(u'link', {
                'name': l.trigger,
                'becoming': tmap[l.type],
                'occurrence': l.appearance,
                'document': make_structured_doc(l.docstring),
                'targets': map(lambda x:x[0], l.link_to_list)
            })
        return {
            'name': s.name,
            'document': make_structured_doc(s.docstr),
            'type': s.type.name,
            'links': links,
        }

    def reify_resource(self, s):
        return {
                'name': s.name,
                'document': make_structured_doc(s.docstring),
                'pathPattern': s.url_patterns,
                'deprecated': 'deprecated' in s.annotations
        }

    def reify_action(self, s):
        return {
                'name': s.name,
                'document': make_structured_doc(s.docstring),
                'implemented': s.implemented,
                'deprecated': 'deprecated' in s.annotations,
                'invoker': s.invoker_obj,
        }

    def reify_module(self, m):
        if m.type == 'cara':
            p = u'actions'
        else:
            p = u'schemata'
        return {
            'name': m.canonical_name,
            'place': p,
            'deprecated': 'deprecated' in m.annotations,
            'document': make_structured_doc(m.docstring),
        }

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

class ListApplications(Command):

    def execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        r = []
        for a in system._apps:
            r.append(reifier.reify_app(a))
        return r

class ListModules(SafeReifier):
    def _execute(self):
        app_name = self._cdpath
        system = self.current_app._system
        if app_name == 'this':
            app = self.current_app
        else:
            app = system.get_app(app_name)
        reifier = ShallowReifier()
        r = []
        for m in app._schema_module.get_modules():
            r.append(reifier.reify_module(m))
        return r

class ListStates(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, _ = split_colon_dot_path(self._cdpath)
        if not app_name:
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            module_name = _
        module = app._schema_module.get_module(module_name)
        if not module.type == u'cara':
            return []
        r = []

        for s in module.states:
            r.append(reifier.reify_state(s))
        return r

class ListResources(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, _ = split_colon_dot_path(self._cdpath)
        if not app_name:
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            module_name = _
        module = app._schema_module.get_module(module_name)
        if not module.type == u'cara':
            return []
        r = []
        for s in module.resources:
            r.append(reifier.reify_resource(s))
        return r

class ListActions(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, res_name = split_colon_dot_path(self._cdpath)
        if not app_name:
            app = self.current_app
        else:
            app = system.get_app(app_name)
        module = app._schema_module.get_module(module_name)
        if not module.type == u'cara':
            return []
        r = []
        for s in module.get_resource(res_name).actions:
            r.append(reifier.reify_action(s))
        return r

class ShowApplication(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, name = split_colon_dot_path(self._cdpath)
        if app_name:
            app = system.get_app(app_name)
        elif not app_name and not module_name:
            app = system.get_app(name)
        else:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        return reifier.reify_app(app)

class ShowModule(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, _ = split_colon_dot_path(self._cdpath)
        if app_name == 'this' or not app_name and not module_name:
            app = self.current_app
        elif app_name:
            app = system.get_app(app_name)
        if not module_name and _:
            module_name = _
        if not module_name:
            print app_name, module_name, _
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        return reifier.reify_module(app._schema_module.get_module(module_name))

class ShowState(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, name = split_colon_dot_path(self._cdpath)
        if not app_name:
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        if not name:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        module = app._schema_module.get_module(module_name)
        if not module.type == u'cara':
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        return reifier.reify_state(module.get_state(name))

class ShowResource(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, name = split_colon_dot_path(self._cdpath)
        if not app_name:
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        if not name:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        module = app._schema_module.get_module(module_name)
        if not module.type == u'cara':
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        return reifier.reify_resource(module.get_resource(name))

class ShowAction(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, name = split_colon_dot_path(self._cdpath)
        if not app_name:
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        if not name:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        module = app._schema_module.get_module(module_name)
        if not module.type == u'cara':
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        if '.' not in name:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        rname, aname = name.split('.', 1)
        return reifier.reify_action(module.get_resource(rname).get_action(aname))

