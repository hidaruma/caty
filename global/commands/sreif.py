from caty.command import *
from caty.core.language import split_colon_dot_path
from caty.core.language.util import make_structured_doc
from caty.jsontools import tagged
from caty.util.collection import conditional_dict
from caty.core.casm.language.ast import KindReference
from reification import *


class ListApplications(Command):

    def execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        r = []
        for a in system._apps:
            r.append(reifier.reify_app(a))
        return r

class ListModules(SafeReifierWithDefaultApp):
    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, pkg_name, _ = split_colon_dot_path(self._cdpath, u'app')
        app = None
        if _:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        if app_name == 'this' or not app_name and pkg_name:
            app = self.current_app
        else:
            app = system.get_app(app_name)
        r = []
        reifier = ShallowReifier()
        if pkg_name:
            pkg = app._schema_module.get_package(pkg_name)
            for m in pkg.list_modules(self._rec):
                r.append(reifier.reify_module(m))
        else:
            r.append(reifier.reify_module(app._schema_module))
            for m in app._schema_module.list_modules(self._rec):
                r.append(reifier.reify_module(m))
        return r

class ListPackages(SafeReifierWithDefaultApp):
    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, pkg_name, _ = split_colon_dot_path(self._cdpath, u'app')
        app = None
        if _:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        if app_name == 'this' or not app_name and pkg_name:
            app = self.current_app
        else:
            app = system.get_app(app_name)
        r = []
        reifier = ShallowReifier()
        if pkg_name:
            pkg = app._schema_module.get_package(pkg_name)
            for m in pkg.list_packages(self._rec):
                r.append(reifier.reify_package(m))
        else:
            for m in app._schema_module.list_packages(self._rec):
                r.append(reifier.reify_package(m))
        return r

class ListClasses(SafeReifierWithDefaultApp):
    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, mod_name, _ = split_colon_dot_path(self._cdpath, u'mod')
        app = None
        if _:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        if app_name == 'this' or not app_name and pkg_name:
            app = self.current_app
        else:
            app = system.get_app(app_name)
        r = []
        reifier = ShallowReifier()
        mod = app._schema_module.get_module(mod_name)
        for c in mod.class_ns.values():
            r.append(reifier.reify_class(c))
        return r

class ListTypes(SafeReifier):
    def setup(self, opts, cdpath):
        SafeReifier.setup(self, opts, cdpath)
        self._rec = opts.get('rec', False)

    def _execute(self):
        from caty.core.schema import types
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, cls_name = split_colon_dot_path(self._cdpath, u'mod')
        if not app_name or app_name == 'this':
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            module_name = cls_name
        module = app._schema_module.get_module(module_name)
        if cls_name:
            module = module.get_class(cls_name)
        r = []
        for t in module.ast_ns.values():
            if t.name not in types:
                if isinstance(t, KindReference): continue
                r.append(reifier.reify_type(t))
        if not cls_name and self._rec:
            for cls in module.class_ns.values():
                for t in cls.ast_ns.values():
                    if isinstance(t, KindReference): continue
                    o = reifier.reify_type(t)
                    o['name'] = cls.name + '.' + o['name']
                    r.append(o)
        return r

class ListCommands(SafeReifier):
    def setup(self, opts, cdpath):
        SafeReifier.setup(self, opts, cdpath)
        self._rec = opts.get('rec', False)


    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, cls_name = split_colon_dot_path(self._cdpath, 'mod')
        if not app_name or app_name == 'this':
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            module_name = cls_name
        module = app._schema_module.get_module(module_name)
        if cls_name:
            module = module.get_class(cls_name)
        r = []
        for c in module.command_ns.values():
            r.append(reifier.reify_command(c))
        if not cls_name and self._rec:
            for cls in module.class_ns.values():
                for c in cls.command_ns.values():
                    o = reifier.reify_command(c)
                    r.append(o)
        return r

class ListStates(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, _ = split_colon_dot_path(self._cdpath, u'mod')
        if not app_name or app_name == 'this':
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
        app_name, module_name, _ = split_colon_dot_path(self._cdpath, u'mod')
        if not app_name or app_name == 'this':
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            if _:
                module_name = _
            else:
                throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
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
        app_name, module_name, res_name = split_colon_dot_path(self._cdpath, u'mod')
        if not app_name or app_name == 'this':
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

class ShowApplication(SafeReifierWithDefaultApp):

    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, name = split_colon_dot_path(self._cdpath, u'app')
        if app_name:
            pass
        elif not app_name and not module_name:
            app_name = name
        else:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        if app_name == 'this':
            app = self.current_app
        else:
            app = system.get_app(app_name)
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
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        return reifier.reify_module(app._schema_module.get_module(module_name))

class ShowPackage(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, pkg_name, _ = split_colon_dot_path(self._cdpath)
        app = None
        if app_name == 'this' or not app_name and not pkg_name:
            app = self.current_app
        elif app_name:
            app = system.get_app(app_name)
        if not pkg_name and _:
            pkg_name = _
        if not pkg_name or not app:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        return reifier.reify_package(app._schema_module.get_package(pkg_name))

class ShowType(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
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
        return reifier.reify_type(module.get_ast(name))

class ShowCommand(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
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
        return reifier.reify_command(module.get_command(name))

class ShowClass(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
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
        return reifier.reify_class(module.get_class(name))

class ShowState(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
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
        if not module.type == u'cara':
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        return reifier.reify_state(module.get_state(name))

class ShowResource(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
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
        if not module.type == u'cara':
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        return reifier.reify_resource(module.get_resource(name))

class ShowAction(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
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
        if not module.type == u'cara':
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        if '.' not in name:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        rname, aname = name.split('.', 1)
        return reifier.reify_action(module.get_resource(rname).get_action(aname))

