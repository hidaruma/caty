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

class ListApplications(Command):

    def execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        r = []
        for a in system._apps:
            r.append(reifier.reify_app(a))
        return r

class ListStates(Command):
    def setup(self, cdpath):
        self.__cdpath = cdpath

    def execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, _ = split_colon_dot_path(self.__cdpath)
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

class ListResources(Command):
    def setup(self, opts, cdpath):
        self.__cdpath = cdpath

    def execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, _ = split_colon_dot_path(self.__cdpath)
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

class ListActions(Command):
    def setup(self, opts, cdpath):
        self.__cdpath = cdpath

    def execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, res_name = split_colon_dot_path(self.__cdpath)
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

class ShowApplication(Command):
    def setup(self, cdpath):
        self.__cdpath = cdpath

    def execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, name = split_colon_dot_path(self.__cdpath)
        if app_name:
            app = system.get_app(app_name)
        elif not app_name and not module_name:
            app = system.get_app(name)
        else:
            throw_caty_exception('BadArg', u'$arg', arg=self.__cdpath)
        return reifier.reify_app(app)

class ShowState(Command):
    def setup(self, cdpath):
        self.__cdpath = cdpath

    def execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, name = split_colon_dot_path(self.__cdpath)
        if not app_name:
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            throw_caty_exception('BadArg', u'$arg', arg=self.__cdpath)
        if not name:
            throw_caty_exception('BadArg', u'$arg', arg=self.__cdpath)
        module = app._schema_module.get_module(module_name)
        if not module.type == u'cara':
            throw_caty_exception('BadArg', u'$arg', arg=self.__cdpath)
        return reifier.reify_state(module.get_state(name))

class ShowResource(Command):
    def setup(self, cdpath):
        self.__cdpath = cdpath

    def execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, name = split_colon_dot_path(self.__cdpath)
        if not app_name:
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            throw_caty_exception('BadArg', u'$arg', arg=self.__cdpath)
        if not name:
            throw_caty_exception('BadArg', u'$arg', arg=self.__cdpath)
        module = app._schema_module.get_module(module_name)
        if not module.type == u'cara':
            throw_caty_exception('BadArg', u'$arg', arg=self.__cdpath)
        return reifier.reify_resource(module.get_resource(name))

class ShowAction(Command):
    def setup(self, cdpath):
        self.__cdpath = cdpath

    def execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, name = split_colon_dot_path(self.__cdpath)
        if not app_name:
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            throw_caty_exception('BadArg', u'$arg', arg=self.__cdpath)
        if not name:
            throw_caty_exception('BadArg', u'$arg', arg=self.__cdpath)
        module = app._schema_module.get_module(module_name)
        if not module.type == u'cara':
            throw_caty_exception('BadArg', u'$arg', arg=self.__cdpath)
        if '.' not in name:
            throw_caty_exception('BadArg', u'$arg', arg=self.__cdpath)
        rname, aname = name.split('.', 1)
        return reifier.reify_action(module.get_resource(rname).get_action(aname))

