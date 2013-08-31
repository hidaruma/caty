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
from caty.core.script.builder import CommandBuilder, CommandCombinator, DiscardCombinator
from caty.core.script.interpreter.executor import CommandExecutor
import traceback
from caty.core.script.proxy import Proxy, EnvelopeProxy
from caty.core.script.node import Try, Catch

class PerformerRequestHandler(RequestHandler):
    def _build(self, path, opts, verb, method, transaction):
        error_logger = ErrorLogHandler(self._app, path, verb, method)
        args = {}
        for k, v in opts.items():
            if k.startswith(u'_') and k.strip('_1234567890') == u'' and len(k) >= 2 and k != '_0':
                args[int(k.strip('_'))-1] = v
                opts.pop(k)
        args = int_dict_to_list(args)
        opts['0'] = path
        if verb:
            cmdnames = [verb]
        else:
            cmdnames = [method.upper(), method.lower()]
        try:
            containerobj = self._path_to_container(path)
            if containerobj is None:
                raise IOError(path)
            else:
                cmdname = None
                for c in cmdnames:
                    if containerobj.has_command_type(c):
                        cmdname = c
                if not c:
                    raise IOError(path)
                cmd = containerobj.get_command(cmdname)
                emitter = containerobj.get_command(u'emit-normal')
                exhandler = containerobj.get_command(u'map-exception')
                sighandler = containerobj.get_command(u'map-signal')
                self._env.put(u'ACTION', cmd.canonical_name)
                if 'deprecated' in cmd.annotations:
                    self._app._system.deprecate_logger.debug(u'path: %s verb: %s' % (path, verb))
                executable = self._make_executable(cmd, emitter, exhandler, sighandler, containerobj, opts, args, transaction)
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
        #if mod.type != 'cara' and self._app._system.public_commands != u'all':
        #    throw_caty_exception(u'HTTP_403', u'Forbidden')
        if cls:
            return mod.get_class(cls)
        else:
            return mod

    def _make_executable(self, profile, emitter, exhandler, sighandler, module, opts, args, transaction):
        builder = CommandBuilder(self._interpreter._facilities, module)
        opts_ref, args_ref = self._sift_opts_and_args(profile, opts, args)
        em_opts_ref, em_args_ref = self._sift_opts_and_args(emitter, opts, args)
        cls = profile.get_command_class()
        if isinstance(cls, Proxy):
            obj = scriptwrapper(profile, lambda :cls.instantiate(builder))
            cmd = obj(opts_ref, args_ref, module=module)
        else:
            cmd = cls(opts_ref, args_ref, module=module)
        cmd = CommandCombinator(
            Try(cmd, [Option(u'wall', u'superhard')]), 
            Catch({
                u'normal': builder.build(emitter, [], em_opts_ref, em_args_ref, (0, 0), module),
                u'except': builder.build(exhandler, [], [], [], (0, 0), module),
                u'signal': builder.build(sighandler, [], [], [], (0, 0), module),
            })
        )
        cmd.set_facility(self._interpreter._facilities)
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

    def _sift_opts_and_args(self, pc, opts, args):
        o_schm = pc.profiles[0].opts_schema
        a_schm = pc.profiles[0].args_schema
        cmd_opts = {}
        cmd_args = []
        if o_schm.type == 'object':
            for k, v in o_schm.items():
                if k in opts:
                    cmd_opts[k] = opts[k]
        if a_schm.type == 'array':
            if a_schm.repeat:
                cmd_args = args
            else:
                cmd_args = args[:len(a_schm)]
        opts_ref = []
        for k, v in cmd_opts.items():
            opts_ref.append(Option(k, v))
        args_ref = [Argument(a) for a in cmd_args]
        return opts_ref, args_ref

