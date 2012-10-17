from caty.core.command import Internal
class Exec(Internal):
    def execute(self, executable):
        from caty.util.path import is_mafs_path
        from caty.core.command import VarStorage
        from caty.core.command.param import Option, Argument
        from caty.core.script.interpreter.executor import CommandExecutor
        from caty.core.script.builder import CommandBuilder
        app = self.current_app.get_app(executable['app'])
        callable = executable['callable']
        if is_mafs_path(callable):
            raise NotImplemented()
        cmd_class = app._schema_module.get_command(callable)
        input = executable['input']
        type_args = [] #executable.get('typeArgs', [])
        opts_base = executable['opts']
        args_base = executable['args']
        opts = [Option('0', executable['arg0'])]
        args = []
        for k, v in opts_base:
            opts.append(k, v)
        for v in args_base:
            args.append(Argument(v))
        oldenv = self._facilities['env']
        self._replace_env_and_facilities(executable)
        builder = CommandBuilder(self._facilities, {})
        cmd_instance = builder.make_cmd(cmd_class, type_args, opts, args, (0, 0), app._schema_module)
        cmd_instance.set_facility(self._facilities)
        var_storage = VarStorage(None, None)
        cmd_instance.set_var_storage(var_storage)
        try:
            executor = CommandExecutor(cmd_instance, app, self._facilities)
            return executor(input)
        finally:
            self._facilities._facilities['env'] = oldenv

    def _replace_env_and_facilities(self, executable):
        from caty.env import Env
        oldenv = self._facilities['env']
        newenv = {}
        if not executable['clearEnv']:
            if executable['defaultEnv'] == 'frame':
                newenv.update(oldenv._dict)
                self._facilities['env'] = Env(newenv)
            else:
                self._facilities['env'] = Env(newenv)
                app.init_env(self._facilities)
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
            throw_caty_exception(u'UncloseConflict', u'$names', names=u', '.join(conflict))
