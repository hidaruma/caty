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
                'minOccurrs': 0 if l.appearance in (u'?', u'*') else 1,
                'maxOccurrs': u'unbounded' if l.appearance in (u'+', u'*') else 1,
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

    def reify_package(self, m):
        if m.type == 'cara':
            p = u'actions'
        else:
            p = u'schemata'
        return {
            'name': m.canonical_name,
            'place': p,
            'document': {'description': m.docstring, 'moreDescription': m.more_docstring},
        }

    def reify_type(self, t):
        return {
            'name': t.name,
            'document': make_structured_doc(t.docstring),
            'deprecated': 'deprecated' in t.annotations,
            'annotations': self.reify_annotations(t.annotations)
        }

    def reify_command(self, c):
        return {
            'name': c.name,
            'document': make_structured_doc(c.docstring),
            'annotations': self.reify_annotations(c.annotations),
            'implemented': c.implemented,
            'profiles': self._make_profile(c),
            'typeParams': [self.reify_type_param(p) for p in c.type_params],
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
                'arg0': self._dump_schema(p.arg0_schema),
                'input': self._dump_schema(p.in_schema),
                'output': self._dump_schema(p.in_schema),
                'exception': [],
                'signal': [],
            }
            if p.throw_schema and p.throw_schema.type != 'never':
                for e in p.throw_schema:
                    o['exception'].append(self._dump_schema(e))
            if p.signal_schema and p.signal_schema.type != 'never':
                for e in p.signal_schema:
                    o['signal'].append(self._dump_schema(e))
            if p.opts_schema.type != 'null':
                o['opts'] = self._dump_schema(p.opts_schema)
            if p.args_schema.type != 'null':
                o['args'] = self._dump_schema(p.args_schema)
            r.append(o)
        return r

    def _dump_schema(self, o):
        from caty.core.casm.cursor.dump import TreeDumper
        if not o:
            return None
        td = TreeDumper(True)
        return td.visit(o)

    def reify_annotations(self, a):
        r = {}
        for an in a.values():
            r[an.name] = self.reify_annotation(an)
        return r

    def reify_annotation(self, a):
        return {
            'name': a.name,
            'value': a.value
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

class SafeReifierWithDefaultApp(SafeReifier):
    def setup(self, opts, cdpath=u'this'):
        self._cdpath = cdpath
        self._safe = opts.get('safe', False)

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
        app_name, pkg_name, _ = split_colon_dot_path(self._cdpath)
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
            for m in pkg.get_modules():
                r.append(reifier.reify_module(m))
        else:
            for m in app._schema_module.get_modules():
                r.append(reifier.reify_module(m))
        return r

class ListPackages(SafeReifierWithDefaultApp):
    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, pkg_name, _ = split_colon_dot_path(self._cdpath)
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
            for m in pkg.get_packages():
                if pkg == m: continue
                r.append(reifier.reify_module(m))
        else:
            for m in app._schema_module.get_packages():
                r.append(reifier.reify_module(m))
        return r

class ListTypes(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, _ = split_colon_dot_path(self._cdpath)
        if not app_name or app_name == 'this':
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            module_name = _
        module = app._schema_module.get_module(module_name)
        r = []
        for t in module.schema_ns.values():
            r.append(reifier.reify_type(t))
        return r

class ListCommands(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, _ = split_colon_dot_path(self._cdpath)
        if not app_name or app_name == 'this':
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            module_name = _
        module = app._schema_module.get_module(module_name)
        r = []
        for c in module.command_ns.values():
            r.append(reifier.reify_command(c))
        return r

class ListStates(SafeReifier):

    def _execute(self):
        reifier = ShallowReifier()
        system = self.current_app._system
        app_name, module_name, _ = split_colon_dot_path(self._cdpath)
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
        app_name, module_name, _ = split_colon_dot_path(self._cdpath)
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
        app_name, module_name, res_name = split_colon_dot_path(self._cdpath)
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
        app_name, module_name, name = split_colon_dot_path(self._cdpath)
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
        if not app_name:
            app = self.current_app
        else:
            app = system.get_app(app_name)
        if not module_name:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        if not name:
            throw_caty_exception('BadArg', u'$arg', arg=self._cdpath)
        module = app._schema_module.get_module(module_name)
        return reifier.reify_type(module.get_type(name))

class ShowCommand(SafeReifier):

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
        return reifier.reify_command(module.get_command(name))

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

