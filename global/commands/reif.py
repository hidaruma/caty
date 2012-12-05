from reification import *

class ReifyType(SafeReifier):
    def setup(self, opts, arg):
        SafeReifier.setup(self, opts, arg)
        self.to_string = opts['to-string']

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
        if self.to_string:
            reifier = StringReifier()
        else:
            reifier = FullReifier()
        return reifier.reify_type(module.get_ast(name))
