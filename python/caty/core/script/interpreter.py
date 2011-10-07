#coding: utf-8
from caty.core.command.exception import *
import caty.util as util
from caty import UNDEFINED
from caty.jsontools.path import build_query
from caty.jsontools import TaggedValue, tag, tagged, untagged, TagOnly
from caty.jsontools import jstypes
from caty.core.command import ScriptError, PipelineInterruption, PipelineErrorExit, Command, ContinuationSignal, Internal
from caty.core.script.node import *
import caty
import caty.core.schema as schema
import types

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

class CommandExecutor(BaseInterpreter):
    def __init__(self, cmd, app, facility_set):
        self.cmd = cmd
        self.app = app
        self.facility_set = facility_set

    def __call__(self, input):
        self.input = input
        try:
            return self.cmd.accept(self)
        except ContinuationSignal as e:
            return e.json_obj

    def visit_command(self, node):
        return self._exec_command(node, self._do_command)

    def visit_script(self, node):
        return self._exec_command(node, self._do_script)

    def _do_command(self, *args):
        if len(args) == 1:
            return args[0].execute()
        else:
            return args[0].execute(args[1])

    def _do_script(self, *args):
        try:
            if len(args) == 1:
                return args[0].script.accept(self)
            else:
                self.input = args[1]
                return args[0].script.accept(self)
        finally:
            args[0].var_storage.del_masked_scope()

    def _exec_command(self, node, exec_func):
        input = self.input
        if 'deprecated' in node.annotations:
            util.cout.writeln(u'[DEBUG] Deprecated: %s' % self.name)
        if node._mode: # @console など、特定のモードでしか動かしてはいけないコマンドのチェック処理
            mode = node.env.get('CATY_EXEC_MODE')
            if not node._mode.intersection(set(mode)):
                raise InternalException(u"Command $name can not use while running mode $mode", 
                                        name=node.profile_container.name,
                                        mode=str(mode)
                )
        try:
            node.var_storage.new_scope()
            node._prepare()
            node.in_schema.validate(input)
            if node.profile.in_schema.type == 'void':
                r = exec_func(node)
            else:
                r = exec_func(node, input)
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
            util.cout.writeln(u"[DEBUG] Error: " + repr(node))
            raise
        finally:
            node.var_storage.del_scope()

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
        if node.var_name in node.var_storage.opts:
            r = node.var_storage.opts[node.var_name]
            if r is UNDEFINED and not node.optional:
                raise Exception(u'%s is not defined' % node.var_name)
            return r
        else:
            if node.optional:
                return caty.UNDEFINED
            raise Exception(u'%s is not defined' % node.var_name)

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
            return self.__iter_obj(node)
        else:
            return self.__iter_array(node)

    def __iter_array(self, node):
        r = []
        i = self.input
        for v in i:
            self.input = v
            try:
                node.var_storage.new_scope()
                r.append(node.cmd.accept(self))
            finally:
                node.var_storage.del_scope()
        return r

    def __iter_obj(self, node):
        r = []
        i = self.input.iteritems()
        for v in i:
            self.input = v
            try:
                node.var_storage.new_scope()
                r.append(node.cmd.accept(self))
            finally:
                node.var_storage.del_scope()
        return dict(r)

    def visit_time(self, node):
        import time
        s = time.time()
        r = node.cmd.accept(self)
        e = time.time()
        print e - s, '[sec]'
        return r

    def visit_take(self, node):
        r = []
        i = self.input
        for v in i:
            try:
                self.input = v
                node.var_storage.new_scope()
                x = node.cmd.accept(self)
                if x == True or tag(x) == 'True':
                    r.append(v)
            finally:
                node.var_storage.del_scope()
        return r

    def visit_start(self, node):
        from caty.core.facility import TransactionAdaptor
        async_queue = self.app.async_queue
        subproc = TransactionAdaptor(CommandExecutor(node.cmd, self.app, self.facility_set), self.facility_set)
        async_queue.push(subproc, subproc.__call__, self.input)
        return self.input

    @property
    def in_schema(self):
        return self.cmd.in_schema

    @property
    def out_schema(self):
        return self.cmd.out_schema

    def set_facility(self, f):
        self.facility_set = f
        self.cmd.set_facility(f)

class _CallCommand(object):
    def setup(self, cmd_name, *args):
        from caty.core.command.param import Argument
        self.__cmd_name = cmd_name
        self.__args = map(Argument, args)

    def _execute(self, input):
        n = self._facilities['env'].get('CATY_APP')['name']
        app = self._system.get_app(n)
        c = app.command_finder[self.__cmd_name].get_command_class()({}, self.__args)
        c.set_facility(self._facilities)
        return CommandExecutor(c)(input)

class CallCommand(_CallCommand, Internal):
    def execute(self, input):
        return self._execute(input)

class Forward(_CallCommand, Internal):
    def execute(self, input):
        raise ContinuationSignal(self._execute(input))


