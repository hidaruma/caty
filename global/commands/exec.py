from caty.core.command import Internal
class Exec(Internal):
    def execute(self, executable):
        from caty.util.path import is_mafs_path
        from caty.core.command import VarStorage
        from caty.core.command.param import Option, Argument
        from caty.core.script.interpreter.executor import CommandExecutor
        from caty.core.script.builder import CommandBuilder
        from caty.core.facility import TransactionPendingAdaptor
        app = self.current_app.get_app(executable['app'])
        callable = executable['callable']
        if is_mafs_path(callable):
            raise NotImplemented()
        cmd_class = app._schema_module.get_command(callable)
        input = executable['input']
        type_args_expr = executable.get('typeArgs', [])
        type_args = []
        for tap in type_args_expr:
            type_args.append(self._compile_type(tap, app))
        opts_base = executable['opts']
        args_base = executable['args']
        opts = [Option('0', executable['arg0'])]
        args = []
        for k, v in opts_base:
            opts.append(k, v)
        for v in args_base:
            args.append(Argument(v))
        oldenv = self._facilities['env']
        new_facilities = self._replace_env_and_facilities(executable, app)
        for k, v in new_facilities.items():
            v.merge_transaction(self._facilities[k])
        builder = CommandBuilder(new_facilities, {})
        cmd_instance = builder.make_cmd(cmd_class, type_args, opts, args, (0, 0), app._schema_module)
        cmd_instance.set_facility(new_facilities)
        var_storage = VarStorage(None, None)
        cmd_instance.set_var_storage(var_storage)
        try:
            executor = TransactionPendingAdaptor(CommandExecutor(cmd_instance, app, new_facilities), new_facilities)
            r = executor(input)
            for k, v in self._facilities.items():
                v.merge_transaction(new_facilities[k])
            return r
        finally:
            self._facilities._facilities['env'] = oldenv

    def _replace_env_and_facilities(self, executable, app):
        from caty.env import Env
        oldenv = self._facilities['env']
        f = app.create_facilities(lambda: self._facilities['session'])
        newenv = {}
        if not executable['clearEnv']:
            if executable['defaultEnv'] == 'frame':
                newenv.update(oldenv._dict)
                f['env'] = Env(newenv)
            else:
                f['env'] = Env(newenv)
                app.init_env(f)
        additional_names = set()
        for k, v in executable['setEnv'].items():
            newenv[k] = v
            additional_names.add(k)
        unset = executable['unsetEnv']
        for n in unset:
            if n in new_dict:
                del new_dict[n]

        conflict = additional_names.intersection(set(unset))
        if conflict:
            throw_caty_exception(u'SetEnvConflict', u'$names', names=u', '.join(conflict))
        return f

    def _compile_type(self, expr, app):
        from caty.core.casm.language.schemaparser import typedef
        from caty.core.casm.language.ast import ASTRoot
        from caty.core.schema.base import Annotations
        from topdown import as_parser
        mod = app._schema_module
        ast = ASTRoot(u'', [], as_parser(typedef).run(expr, auto_remove_ws=True), Annotations([]), u'')
        sb = mod.make_schema_builder()
        rr = mod.make_reference_resolver()
        cd = mod.make_cycle_detecter()
        ta = mod.make_typevar_applier()
        tn = mod.make_type_normalizer()
        t = ast.accept(sb)
        t = t.accept(rr)
        t = t.accept(cd)
        t = t.accept(ta)
        t = t.accept(tn)
        return t
