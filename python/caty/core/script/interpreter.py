#coding: utf-8
from caty.core.command.exception import *
from caty.command import MafsMixin
from copy import deepcopy
from caty.core.facility import PEND
import caty.util as util
from caty import UNDEFINED
from caty.jsontools.path import build_query
from caty.jsontools import TaggedValue, tag, tagged, untagged, TagOnly, prettyprint
from caty.jsontools import jstypes
from caty.core.command import ScriptError, PipelineInterruption, PipelineErrorExit, Command, ContinuationSignal, Internal, scriptwrapper
from caty.core.exception import throw_caty_exception
from caty.core.script.node import *
from caty.core.exception import *
import caty
import caty.core.schema as schema
import types
import time

class BaseInterpreter(object):
    def visit(self, node):
        return node.accept(self)

    def visit_command(self, node):
        raise NotImplementedError(u'{0}#visit_command'.format(self.__class__.__name__))

    def visit_pipe(self, node):
        raise NotImplementedError(u'{0}#visit_pipe'.format(self.__class__.__name__))

    def visit_discard_pipe(self, node):
        raise NotImplementedError(u'{0}#visit_discard_pipe'.format(self.__class__.__name__))

    def visit_scalar(self, node):
        raise NotImplementedError(u'{0}#visit_scalar'.format(self.__class__.__name__))

    def visit_list(self, node):
        raise NotImplementedError(u'{0}#visit_list'.format(self.__class__.__name__))

    def visit_object(self, node):
        raise NotImplementedError(u'{0}#visit_object'.format(self.__class__.__name__))

    def visit_varstore(self, node):
        raise NotImplementedError(u'{0}#visit_varstore'.format(self.__class__.__name__))

    def visit_varref(self, node):
        raise NotImplementedError(u'{0}#visit_varref'.format(self.__class__.__name__))

    def visit_argref(self, node):
        raise NotImplementedError(u'{0}#visit_argref'.format(self.__class__.__name__))

    def visit_when(self, node):
        raise NotImplementedError(u'{0}#visit_when'.format(self.__class__.__name__))

    def visit_binarytag(self, node):
        raise NotImplementedError(u'{0}#visit_binarytag'.format(self.__class__.__name__))

    def visit_unarytag(self, node):
        raise NotImplementedError(u'{0}#visit_unarytag'.format(self.__class__.__name__))

    def visit_each(self, node):
        raise NotImplementedError(u'{0}#visit_each'.format(self.__class__.__name__))

    def visit_time(self, node):
        raise NotImplementedError(u'{0}#visit_time'.format(self.__class__.__name__))

    def visit_take(self, node):
        raise NotImplementedError(u'{0}#visit_take'.format(self.__class__.__name__))

    def visit_script(self, node):
        raise NotImplementedError(u'{0}#visit_script'.format(self.__class__.__name__))

    def visit_start(self, node):
        raise NotImplementedError(u'{0}#visit_start'.format(self.__class__.__name__))

    def visit_case(self, node):
        raise NotImplementedError(u'{0}#visit_case'.format(self.__class__.__name__))

    def visit_json_path(self, node):
        raise NotImplementedError(u'{0}#visit_json_path'.format(self.__class__.__name__))

class CommandExecutor(BaseInterpreter):
    def __init__(self, cmd, app, facility_set):
        self.cmd = cmd
        self.app = app
        self.facility_set = facility_set

    def __call__(self, input):
        self.input = input
        while True:
            try:
                return self.cmd.accept(self)
            except ContinuationSignal as e:
                self.cmd = e.cont
                if self.cmd is None:
                    return e.data
                self.data = e.data
            except KeyboardInterrupt as e:
                print e
                return None

    def visit_command(self, node):
        return self._exec_command(node, self._do_command)

    def visit_script(self, node):
        return self._exec_command(node, self._do_script)

    def _do_command(self, *args):
        if len(args) == 1:
            return args[0].execute()
        else:
            return args[0].execute(args[1])

    def _do_script(self, *argv):
        node = argv[0]
        opts = node._opts
        args = node._args
        o = {}
        if opts:
            for k, v in opts.items():
                o[k] = v
        node.var_storage.new_masked_scope(opts or {}, args or [])
        if opts:
            for k, v in opts.items():
                node.var_storage.opts[k] = v
        if args:
            node.var_storage.opts['_ARGV'] = [u""] + args
            node.var_storage.args = [u""] + args
        else:
            node.var_storage.opts['_ARGV'] = [u""]
            node.var_storage.args = [u""]
        if opts:
            node.var_storage.opts['_OPTS'] = o
        else:
            node.var_storage.opts['_OPTS'] = {}
        try:
            if len(argv) == 1:
                return node.script.accept(self)
            else:
                self.input = argv[1]
                return node.script.accept(self)
        finally:
            node.var_storage.del_masked_scope()

    def _exec_command(self, node, exec_func):
        input = self.input
        if 'deprecated' in node.annotations:
            util.cout.writeln(u'[DEBUG] Deprecated: %s' % node.name)
            try:
                name = self.__get_name(node)
                msg = '{0} at {1}:{2} Line {3}, Col {4}'.format(name, self.app.name, self.__get_name(self.cmd), self.cmd.col, self.cmd.line)
                self.app._system.depreacte_logger.debug(msg)
            except Exception, e:
                import traceback
                traceback.print_exc()
                msg = u'[DEBUG] %s (other infomation is lacking)' % node.name
                self.app._system.depreacte_logger.debug(msg)
        if node._mode: # @console など、特定のモードでしか動かしてはいけないコマンドのチェック処理
            mode = node.env.get('CATY_EXEC_MODE')
            if not node._mode.intersection(set(mode)):
                raise InternalException(u"Command $name can not use while running mode $mode", 
                                        name=node.profile_container.name,
                                        mode=str(' '.join(mode))
                )
        try:
            node.var_storage.new_scope()
            node._prepare()
            if node.profile.in_schema.type == 'void':
                r = exec_func(node)
            else:
                node.in_schema.validate(input)
                r = exec_func(node, input)
            if node.out_schema.type == 'void':
                r = None
            else:
                node.out_schema.validate(r)
            if 'commit-point' in node.profile_container.get_annotations():
                for n in node.facility_names:
                    getattr(node, n).commit()
            if isinstance(r, list):
                while r and r[-1] is UNDEFINED:
                    r.pop(-1)
            return r
        except ContinuationSignal as e:
            raise
        except Exception as e:
            if isinstance(e, PipelineInterruption) or isinstance(e, PipelineErrorExit):
                raise
            msg = u'Error {0}: Col {1}, Line {2}'.format(node.name, node.col, node.line)
            util.cout.writeln(msg)
            raise
        finally:
            node.var_storage.del_scope()

    def __get_name(self, node):
        if node.profile_container.module:
            name = '{0}:{1}'.format(node.profile_container.module.name, node.name)
        else:
            name = ':'+node.name
        return name

    def visit_pipe(self, node):
        self.input = node.bf.accept(self)
        return node.af.accept(self)

    def visit_discard_pipe(self, node):
        node.bf.accept(self)
        self.input = None
        return node.af.accept(self)


    def visit_scalar(self, node):
        return node.value

    def visit_list(self, node):
        r = []
        for v in node:
            prev_input = self.input
            r.append(v.accept(self))
            self.input = prev_input
        while r and r[-1] is UNDEFINED:
            r.pop(-1)
        return r

    def visit_object(self, node):
        obj = {}
        for name, node in node.iteritems():
            prev_input = self.input
            obj[name] = node.accept(self)
            self.input = prev_input
        if '$$tag' in obj:
            if '$$val' in obj:
                o = tagged(obj['$$tag'], obj['$$val'])
            else:
                t = obj['$$tag']
                del obj['$$tag']
                o = tagged(t, obj)
            return o
        else:
            return obj

    def visit_varstore(self, node):
        if node.var_name not in node.var_storage.opts:
            node.var_storage.opts[node.var_name] = self.input
            return self.input
        else:
            raise Exception(u'%s is already defined' % node.var_name)

    def visit_varref(self, node):
        r = caty.UNDEFINED
        if node.var_name in node.var_storage.opts:
            r = node.var_storage.opts[node.var_name]
        else:
            if self.facility_set['env'].exists(node.var_name):
                r = self.facility_set['env'].get(node.var_name)
        if r is UNDEFINED and not node.optional:
            raise Exception(u'%s is not defined' % node.var_name)
        return r

    def visit_argref(self, node):
        argv = node.var_storage.opts['_ARGV']
        try:
            return argv[node.arg_num]
        except:
            if node.optional:
                return caty.UNDEFINED
            raise

    def visit_when(self, node):
        jsobj = self.input
        target = node.query.find(jsobj).next()
        if not isinstance(target, TaggedValue) and not (isinstance(target, dict) and '$$tag' in target):
            return self.__not_tagged_value_case(node, target)
        else:
            return self.__tagged_value_case(node, target)

    def __tagged_value_case(self, node, target):
        tag = target.tag if isinstance(target, TaggedValue) else target['$$tag']
        if tag not in node.cases:
            if '*' in node.cases:
                tag = '*'
            elif '*!' in node.cases:
                if tag not in schema.types:
                    tag = '*!'
                else:
                    raise ScriptError(tag)
            else:
                raise ScriptError(tag)
        return self.__exec_cmd(node, tag, target)

    def __not_tagged_value_case(self, node, target):
        tags = node.scalar_tag_map.get(type(target), None)
        if tags == None:
            raise ScriptError()
        for tag in tags:
            if tag in node.cases:
                return self.__exec_cmd(node, tag, target)
        if '*' in node.cases:
            tag = '*'
        elif '*!' in node.cases:
            for tag in tags:
                if tag not in schema.types:
                    tag = '*!'
                    break
            else:
                raise ScriptError(tag)
        else:
            raise ScriptError(tag)
        return self.__exec_cmd(node, tag, target)
    
    def __exec_cmd(self, node, tag, jsobj):
        childcmd = node.cases[tag].cmd
        if childcmd.in_schema != jstypes.never:
            if isinstance(node.cases[tag], UntagCase):
                self.input = untagged(jsobj)
            else:
                self.input = jsobj
        return childcmd.accept(self)

    def visit_binarytag(self, node):
        return tagged(node.tag, node.command.accept(self))

    def visit_unarytag(self, node):
        return TagOnly(node.tag)

    def visit_each(self, node):
        node._prepare()
        if node.prop:
            return self.__iter_obj_as_array(node)
        else:
            if isinstance(self.input, dict):
                return self.__iter_obj(node)
            else:
                return self.__iter_array(node)

    def __iter_array(self, node):
        r = []
        i = self.input
        n = 0
        for v in i:
            self.input = v
            try:
                node.var_storage.new_scope()
                node.var_storage.opts['_key'] = n
                node.var_storage.opts['_value'] = i[n]
                r.append(node.cmd.accept(self))
            finally:
                node.var_storage.del_scope()
            n+=1
        return r

    def __iter_obj_as_array(self, node):
        r = []
        for k, v in self.input.iteritems():
            self.input = v
            try:
                node.var_storage.new_scope()
                node.var_storage.opts['_key'] = k
                node.var_storage.opts['_value'] = v
                r.append([k, node.cmd.accept(self)])
            finally:
                node.var_storage.del_scope()
        return dict(r)

    def __iter_obj(self, node):
        r = []
        for k, v in self.input.iteritems():
            self.input = v
            try:
                node.var_storage.new_scope()
                node.var_storage.opts['_key'] = k
                node.var_storage.opts['_value'] = v
                r.append(node.cmd.accept(self))
            finally:
                node.var_storage.del_scope()
        return r

    def visit_time(self, node):
        s = time.time()
        r = node.cmd.accept(self)
        e = time.time()
        print e - s, '[sec]'
        return r

    def visit_take(self, node):
        node._prepare()
        if not node.obj:
            r = []
            i = self.input
            if isinstance(i, dict):
                i = i.values()
            for v in i:
                node.var_storage.new_scope()
                try:
                    self.input = v
                    x = node.cmd.accept(self)
                    if self.__truth(x, node):
                        r.append(v)
                finally:
                    node.var_storage.del_scope()
        else:
            r = {}
            i = self.input
            for k, v in i.items():
                try:
                    self.input = v
                    node.var_storage.new_scope()
                    x = node.cmd.accept(self)
                    if self.__truth(x, node):
                        r[k] = v
                finally:
                    node.var_storage.del_scope()
        return r

    def __truth(self, v, node):
        if node.indef:
            return v == True or tag(v) == 'True' or tag(v) == 'OK' or tag(v) == 'Indef'
        else:
            return v == True or tag(v) == 'True' or tag(v) == 'OK'

    def visit_start(self, node):
        from caty.core.facility import TransactionAdaptor
        async_queue = self.app.async_queue
        subproc = TransactionAdaptor(CommandExecutor(node.cmd, self.app, self.facility_set), self.facility_set)
        worker = async_queue.push(subproc, subproc.__call__, self.input)
        t = time.time()
        while not worker.isStarted and time.time() - t < 2:
            pass
        return self.input


    def visit_case(self, node):
        default = None
        if node.path:
            case_in = node.path.select(self.input).next()
        else:
            case_in = self.input
        for c in node.cases:
            if c.type is None:
                default = c
            else:
                try:
                    c.type.validate(case_in)
                except:
                    pass
                else:
                    if node.via:
                        self.input = node.via.accept(self)
                    return c.accept(self)
        if default is None:
            throw_caty_exception(
                u'TypeError',
                node.scalar_tag_map.get(type(case_in), [str(type(case_in))])[0]
            )
        else:
            return default.accept(self)

    def visit_json_path(self, node):
        stm = node.stm
        try:
            r = stm.select(self.input).next()
            if r == caty.UNDEFINED:
                msg = '{0} at {1}:{2} Line {3}, Col {4}'.format(node.path, self.app.name, self.__get_name(self.cmd), self.cmd.col, self.cmd.line)
                throw_caty_exception(u'Undefined', msg)
            return r
        except:
            raise

    @property
    def in_schema(self):
        return self.cmd.in_schema

    @property
    def out_schema(self):
        return self.cmd.out_schema

    def set_facility(self, f):
        self.facility_set = f
        self.cmd.set_facility(f)

    @property
    def var_storage(self):
        return self.cmd.var_storage

    def set_var_storage(self, v):
        self.cmd.set_var_storage(v)

from caty.command import MafsMixin
class _CallCommand(MafsMixin, Internal):
    def __init__(self, opts_ref, args_ref, type_args=[], pos=(None, None)):
        Internal.__init__(self, [], [args_ref[0]], type_args, pos)
        self.__opts_ref = opts_ref
        self.__args_ref = args_ref[1:]

    def setup(self, cmd_name):
        self._cmd_name = cmd_name
        if self._cmd_name.endswith('.caty') and self._cmd_name[0] != u'/':
            self._cmd_name = 'scripts@this:/' + self._cmd_name

    def _make_cmd(self):
        n = self._facilities['env'].get('CATY_APP')['name']
        app = self._system.get_app(n)
        if self._cmd_name.endswith('.caty') or any(map(lambda x: self._cmd_name.endswith(x), app.web_config.get('script_ext'))):
            return self.__script()
        else:
            return self.__make_cmd()

    def __make_cmd(self):
        from caty.core.script.proxy import Proxy
        from caty.core.script.builder import CommandBuilder
        from caty.core.command import VarStorage
        n = self._facilities['env'].get('CATY_APP')['name']
        app = self._system.get_app(n)
        profile = app.command_finder[self._cmd_name]
        cls = profile.get_command_class()
        if isinstance(cls, Proxy):
            c = scriptwrapper(profile, cls.instantiate(CommandBuilder(self._facilities, app.command_finder)))(self.__opts_ref, self.__args_ref)
        else:
            c = cls(self.__opts_ref, self.__args_ref)
        var_storage = VarStorage(None, [])
        c.set_facility(self._facilities)
        c.set_var_storage(var_storage)
        return CommandExecutor(c, app, self._facilities)

    def __script(self):
        from copy import deepcopy
        self.var_loader.opts = self.__opts_ref
        self.var_loader.args = self.__args_ref
        opts = self.var_loader._load_opts(self.var_storage.opts)
        args = [self._cmd_name] + self.var_loader._load_args(self.var_storage.opts, self.var_storage.args)
        cmd = self.interpreter.build(self.open(self._cmd_name).read(),
                                     deepcopy(opts), 
                                     args, 
                                     transaction=PEND)
        vs = cmd.var_storage
        vs.opts['_ARGV'] = args
        vs.opts['_OPTS'] = opts
        return cmd

class CallCommand(_CallCommand):
    def execute(self, input):
        c = self._make_cmd()
        return c(input)

class Forward(_CallCommand):
    def execute(self, input):
        c = self._make_cmd()
        raise ContinuationSignal(input, c.cmd)

