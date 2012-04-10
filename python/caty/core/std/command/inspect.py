#coding: utf-8
from caty.core.command import Internal, Builtin
from caty.core.exception import *
import caty.jsontools as json

class ListCommands(Internal):
    def setup(self, opts, module_name):
        self._short = opts['short']
        self._module_name = module_name

    def execute(self):
        if ':' in self._module_name:
            app_name, mod_name = self._module_name.split(':', 1)
            if app_name == 'this':
                app_name = self.current_app.name
        else:
            app_name = self.current_app.name
            mod_name = self._module_name
        app = self._system.get_app(app_name)
        mod = app._schema_module.get_module(mod_name)
        r = []
        for k, v in mod.proto_ns.items():
            if v.module.name == mod.name:
                r.extend(self._get_command_info(v))
        return r

    def _get_command_info(self, proto_type):
        from caty.core.casm.cursor.dump import TreeDumper
        td = TreeDumper(withoutdoc=True)
        td.started = True
        profiles = []
        for p in proto_type.patterns:
            o = {
                'name': proto_type.name,
                'implemented': u'catyscript' if proto_type.script_proxy is not None else u'python' if proto_type.uri != 'caty.core.command.Dummy' else u'none',
            }
            o['opts'] = td.visit(p.opts) if p.opts else u'{}'
            o['args'] = td.visit(p.args) if p.args else u'[]'
            o['input'] = td.visit(p.decl.profile[0])
            o['output'] = td.visit(p.decl.profile[1])
            o['deprecated'] = 'deprecated' in proto_type.annotation
            o['throws'] = []
            o['typeVars'] = [v.var_name for v in proto_type.type_params]
            for ls in p.decl.jump:
                for node in ls:
                    o['throws'].append(td.visit(node))
            if not self._short:
                o['facilityUsages'] = []
                for mode, decl in p.decl.get_all_resources():
                    o['facilityUsages'].append({'usageType': unicode(mode), 'facilityName': decl.name})
            profiles.append(o)
        return profiles
        
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
        if ':' in self._module_name:
            app_name, mod_name = self._module_name.split(':', 1)
            if app_name == 'this':
                app_name = self.current_app.name
        else:
            app_name = self.current_app.name
            mod_name = self._module_name
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
        mod = self.schema._module.command_finder
        ast = mod.get_proto_type(self._cmd_name)
        return ast.reify()

class ReifyModule(Internal):
    def setup(self, mod_name):
        self._module_name = mod_name

    def execute(self):
        if ':' in self._module_name:
            app_name, mod_name = self._module_name.split(':', 1)
            if app_name == 'this':
                app_name = self.current_app.name
        else:
            app_name = self.current_app.name
            mod_name = self._module_name
        app = self._system.get_app(app_name)
        mod = app._schema_module.get_module(mod_name)
        if not mod.type.startswith('casm'):
            throw_caty_exception(u'BadArg', self._module_name)
        return mod.reify()

