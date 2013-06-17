from caty.core.handler import RequestHandler, PipelineAdaptor, ErrorLogHandler, ExceptionAdaptor
from caty.util.collection import int_dict_to_list
from caty.core.exception import InternalException, throw_caty_exception
from caty.core.facility import (FakeFacility, 
                                TransactionAdaptor, 
                                TransactionDiscardAdaptor, 
                                TransactionPendingAdaptor,
                                COMMIT,
                                ROLLBACK,
                                PEND)
from caty.core.command import scriptwrapper
from caty.core.command.param import Option, Argument
from caty.core.script.builder import CommandBuilder
from caty.core.script.interpreter.executor import CommandExecutor
import traceback
from caty.core.script.proxy import Proxy, EnvelopeProxy

class PerformerRequestHandler(RequestHandler):
    def _build(self, path, opts, verb, method, transaction):
        error_logger = ErrorLogHandler(self._app, path, verb, method)
        args = {}
        for k, v in opts.items():
            if k.startswith(u'_') and k.strip('_1234567890') == u'' and len(k) >= 2 and k != '_0':
                args[int(k)-1] = v
                opts.pop(k)
        args = int_dict_to_list(args)
        opts['0'] = path
        if verb:
            cmdname = verb
        else:
            cmdname = method.lower()
        try:
            containerobj = self._path_to_container(path)
            if containerobj is None:
                raise IOError(path)
            else:
                if not containerobj.has_command_type(cmdname):
                    raise IOError(path)
                cmd = containerobj.get_command(cmdname)
                self._env.put(u'ACTION', cmd.canonical_name)
                if 'deprecated' in cmd.annotations:
                    self._app._system.deprecate_logger.debug(u'path: %s verb: %s' % (path, verb))
                # executable = self._make_executable(cmd, containerobj, opts, args, transaction)
                source = [cmd.canonical_name]
                for k, v in opts.items():
                    source.append('--%s=%s' % (k, v if ' ' not in v else '"%s"' % v))
                for a in args:
                    source.append(a if ' ' not in a else '"%s"' % a)
                executable = self._interpreter.build(u' '.join(source), None, [path], transaction=transaction)
        except Exception, e:
            return ExceptionAdaptor(e, self._interpreter, traceback.format_exc(), self, error_logger)
        return PipelineAdaptor(executable, self._interpreter, self, error_logger, None, transaction)

    def _path_to_container(self, path):
        pkg_mod_name = path.lstrip('/').replace('+/', '.')
        cls = u''
        if '/' in pkg_mod_name:
            pkg_mod_name, cls = pkg_mod_name.split('/', 1)
        if cls and not cls.endswith('/'):
            throw_caty_exception(u'HTTP_400', u'Not implemented: $path', path=path)
        cls = cls.strip('/')
        mod = self._app._schema_module.get_module(pkg_mod_name)
        if mod.type != 'cara' and self._app._system.public_commands != u'all':
            throw_caty_exception(u'HTTP_403', u'Forbidden')
        if cls:
            return mod.get_class(cls)
        else:
            return mod

    def _make_executable(self, profile, module, opts, args, transaction):
        opts_ref = []
        for k, v in opts.items():
            opts_ref.append(Option(k, v))
        builder = CommandBuilder(self._interpreter._facilities, module)
        args_ref = [Argument(a) for a in args]
        cls = profile.get_command_class()
        if isinstance(cls, Proxy):
            obj = scriptwrapper(profile, lambda :cls.instantiate(builder))
            cmd = obj(opts_ref, args_ref, module=module)
        else:
            cmd = cls(opts_ref, args_ref, module=module)
        executable =  CommandExecutor(cmd, self._app, self._interpreter._facilities)
        if transaction == COMMIT:
            return TransactionAdaptor(executable, self._interpreter._facilities)
        elif transaction == ROLLBACK:
            return TransactionDiscardAdaptor(executable, self._interpreter._facilities)
        elif transaction == PEND:
            return TransactionPendingAdaptor(executable, self._interpreter._facilities)
        elif transaction == None:
            return executable
        else:
            raise Exception(self.module._app.i18n.get(u'Invalid transaction mode: $mode', mode=str(transaction)))
