#coding: utf-8
from caty.core.command import Internal, Builtin
from caty.core.exception import *
from caty.core.language import split_colon_dot_path as _split_colon_dot_path
import caty.jsontools as json

split_colon_dot_path = lambda s: _split_colon_dot_path(s, u'ignore')

class ListCommands(Internal):
    def setup(self, opts, module_name):
        self._short = opts['short']
        self._module_name = module_name

    def execute(self):
        app_name, mod_name, name = split_colon_dot_path(self._module_name)
        if app_name == 'this':
            app_name = self.current_app.name
        elif not app_name:
            app_name = self.current_app.name
        if not mod_name:
            mod_name = name
        app = self._system.get_app(app_name)
        mod = app._schema_module.get_module(mod_name)
        r = []
        for k, v in mod.command_ns.items():
            if v.module.name == mod.name:
                r.extend(self._get_command_info(v))
        return r

    def _get_command_info(self, profile):
        from caty.core.casm.cursor.dump import TreeDumper
        td = TreeDumper(withoutdoc=True)
        td.started = True
        profiles = []
        for p in profile.profiles:
            o = {
                'name': profile.name,
                'implemented': profile.implemented,
            }
            o['opts'] = td.visit(p.opts_schema) if p.opts_schema.type != 'never' else u'{}'
            o['args'] = td.visit(p.args_schema) if p.args_schema.type != 'never'  else u'[]'
            o['input'] = td.visit(p.declobj.profile[0])
            o['output'] = td.visit(p.declobj.profile[1])
            o['deprecated'] = 'deprecated' in profile.annotations
            o['throws'] = []
            o['signals'] = []
            o['typeVars'] = [v.var_name for v in profile.type_params]
            if p.declobj.throws.type != u'never':
                for node in self.__divide_union(p.declobj.throws):
                    o['throws'].append(td.visit(node))
            if p.declobj.signals.type != u'never':
                for node in self.__divide_union(p.declobj.signals):
                    o['signals'].append(td.visit(node))
            if not self._short:
                o['facilityUsages'] = []
                for mode, declobj in p.declobj.get_all_resources():
                    o['facilityUsages'].append({'usageType': unicode(mode), 'facilityName': declobj.name})
            profiles.append(o)
        return profiles
        
    def __divide_union(self, o):
        from caty.core.schema import UnionSchema
        if isinstance(o, UnionSchema):
            for x in self.__divide_union(o.left):
                yield x
            for x in self.__divide_union(o.right):
                yield x
        else:
            yield o

class ListModules(Internal):
    def setup(self, app_name):
        self.app_name = app_name

    def execute(self):
        app = self._system.get_app(self.app_name)
        r = []
        for mod in app._schema_module.get_modules():
            if mod._app.name != self.app_name:
                continue
            o = {
                'name': mod.name,
                'document': mod.doc_object,
                'syntax': unicode(mod._type.split('.', 1)[0]),
                'place': u'schemata' if mod._type.startswith('casm') else u'actions'
            }
            r.append(o)
        return r
        
class ModuleInfo(Internal):
    def setup(self, mod_name):
        self._module_name = mod_name

    def execute(self):
        app_name, mod_name, _ = split_colon_dot_path(self._module_name)
        if app_name == 'this':
            app_name = self.current_app.name
        elif not app_name:
            app_name = self.current_app.name
        app = self._system.get_app(app_name)
        mod = app._schema_module.get_module(mod_name)
        o = {
            'name': mod.name,
            'document': mod.doc_object,
            'syntax': unicode(mod._type.split('.', 1)[0]),
            'place': u'schemata' if mod._type.startswith('casm') else u'actions'
        }
        return o

class ReifyType(Builtin):
    def setup(self, type_name):
        self._type_name = type_name

    def execute(self):
        from caty.core.casm.language.ast import ScalarNode, BagNode, ObjectNode, ArrayNode
        mod = self.schema
        if self._type_name in ('integer', 'number', 'boolean', 'string', 'binary', 'null', 'undefined', 'any', 'never', 'univ'):
            return ScalarNode(self._type_name).reify()
        elif self._type_name == 'object':
            return ObjectNode(wildcard=ScalarNode(u'any')).reify()
        elif self._type_name == 'array':
            return ArrayNode(wildcard=ArrayNode(u'any'), options={'repeat': True}).reify()
        elif self._type_name == 'bag':
            return BagNode().reify()
        ast = mod.get_ast(self._type_name)
        return ast.reify()

class ReifyCmd(Builtin):
    def setup(self, cmd_name):
        self._cmd_name = cmd_name

    def execute(self):
        mod = self.schema
        ast = mod.get_proto_type(self._cmd_name)
        return ast.reify()

class ReifyModule(Internal):
    def setup(self, mod_name):
        self._module_name = mod_name

    def execute(self):
        app_name, mod_name, name = split_colon_dot_path(self._module_name)
        if app_name == 'this':
            app_name = self.current_app.name
        elif not app_name:
            app_name = self.current_app.name
        if not mod_name:
            mod_name = name
        app = self._system.get_app(app_name)
        mod = app._schema_module.get_module(mod_name)
        return mod.reify()

class Whereis(Internal):
    def setup(self, opts, cmd_name):
        self._cmd_name = cmd_name
        self.type = opts['type']

    def execute(self):
        from caty.core.language import split_colon_dot_path
        app, mod, cn = split_colon_dot_path(self._cmd_name, u'cmd')
        m = self.current_app.get_app(app)._schema_module
        if self.type == 'command':
            c = m.get_command(mod + ':' +cn)
        elif self.type == 'type':
            c = m.get_type(mod + ':' +cn)
        elif self.type == 'class':
            c = m.get_class(mod + ':' +cn)
        return c.module.app.name + u'::' + c.module.canonical_name + u':' + c.name

