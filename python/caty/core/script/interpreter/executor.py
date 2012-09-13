#coding: utf-8
from caty.core.command.exception import *
from caty.command import MafsMixin
from copy import deepcopy
from caty.core.facility import PEND
import caty.util as util
from caty import UNDEFINED
from caty.jsontools.path import build_query
from caty.jsontools import TaggedValue, tag, tagged, untagged, TagOnly, prettyprint, split_tag
from caty.jsontools import jstypes
from caty.core.command import ScriptError, PipelineInterruption, PipelineErrorExit, Command, Internal, scriptwrapper
from caty.core.script.node import *
from caty.core.exception import *
import caty
import caty.core.schema as schema
import types
import time
from caty.core.spectypes import reduce_undefined

from caty.core.script.interpreter.base import BaseInterpreter
from caty.core.script.interpreter.typevar import TypeVarApplier

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
                if e.cont is None:
                    return e.data
                self.cmd = e.cont
                self.input = e.data
            except CatySignal as e:
                throw_caty_exception(u'UnhandledSignal', u'$signal', signal=e.raw_data)
            except KeyboardInterrupt as e:
                print e
                return None

    def accept(self, visitor):
        return self.cmd.accept(visitor)

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
            node.var_storage.opts['_ARGV'] = [node.arg0] + args
            node.var_storage.args = [node.arg0] + args
        else:
            node.var_storage.opts['_ARGV'] = [node.arg0]
            node.var_storage.args = [node.arg0]
        if opts:
            node.var_storage.opts['_OPTS'] = o
        else:
            node.var_storage.opts['_OPTS'] = {}
        try:
            tva = TypeVarApplier(node.type_params)
            if tva.type_params:
                tva.visit(node)
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
                if isinstance(self.cmd, ActionEnvelope) or hasattr(self.cmd, 'script'): #アクションかスクリプトから呼ばれた。
                    msg = '{0} at {1}:{2} Line {3}, Col {4}'.format(name, self.app.name, self.__get_name(self.cmd), self.cmd.col, self.cmd.line)
                elif isinstance(self.cmd, _CallCommand):
                    msg = '{0} at {1}:{2} Line {3}, Col {4}'.format(name, self.app.name, self.cmd._cmd_name, self.cmd.col, self.cmd.line)
                else: # コンソール
                    msg = '{0}'.format(name)
                self.app._system.deprecate_logger.debug(msg)
            except Exception, e:
                import traceback
                traceback.print_exc()
                msg = u'%s (other infomation is lacking)' % node.name
                self.app._system.deprecate_logger.debug(msg)
        if node._mode: # @console など、特定のモードでしか動かしてはいけないコマンドのチェック処理
            mode = node.env.get('CATY_EXEC_MODE', [])
            if not node._mode.intersection(set(mode)):
                if mode:
                    raise InternalException(u"Command $name can not use while running mode $mode", 
                                            name=node.profile_container.name,
                                            mode=str(' '.join(mode))
                    )
                else:
                    raise InternalException(u"Command $name can not use while running mode is not specified", 
                                            name=node.profile_container.name
                    )
        try:
            node.var_storage.new_scope()
            node._prepare()
            if node.profile.in_schema.type == 'void':
                self.input = None
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
            return r
        except SystemResourceNotFound as e:
            raise
        except ContinuationSignal as e:
            #node.signal_schema.validate(e.data)
            raise
        except CatySignal as e:
            #node.signal_schema.validate(e.raw_data)
            raise e
        except CatyException as e:
            import sys
            info = sys.exc_info()[2]
            try:
                node.throw_schema.validate(e.to_json())
            except Exception:
                if u'__only' in node.throw_schema.annotations:
                    raise CatyException(u'TypeError', u'Unexpected exception: $name', name=e.tag), None, sys.exc_info()[2]
                else:
                    raise e, None, info
            raise
        except Exception as e:
            if isinstance(e, PipelineInterruption) or isinstance(e, PipelineErrorExit):
                raise
            if self.facility_set['env'].get('DEBUG'):
                msg = u'[DEBUG] {0}: Col {1}, Line {2}'.format(node.name, node.col, node.line)
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
        node._prepare()
        return node.value

    def visit_list(self, node):
        node._prepare()
        r = []
        for v in node:
            prev_input = self.input
            r.append(v.accept(self))
            self.input = prev_input
        return r

    def visit_object(self, node):
        node._prepare()
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
        node._prepare()
        if node.var_name not in node.var_storage.opts:
            node.var_storage.opts[node.var_name] = self.input
            return self.input
        else:
            raise Exception(u'%s is already defined' % node.var_name)

    def visit_varref(self, node):
        node._prepare()
        r = caty.UNDEFINED
        if node.var_name in node.var_storage.opts:
            r = node.var_storage.opts[node.var_name]
        else:
            if self.facility_set['env'].exists(node.var_name):
                r = self.facility_set['env'].get(node.var_name)
        if r is UNDEFINED and not node.optional:
            raise Exception(u'%s is not defined' % node.var_name)
        if r is UNDEFINED and node.default is not UNDEFINED:
            r = node.default
        return r

    def visit_argref(self, node):
        node._prepare()
        argv = node.var_storage.opts['_ARGV']
        try:
            return argv[node.arg_num]
        except:
            if node.optional:
                return caty.UNDEFINED
            raise

    def visit_when(self, node):
        node._prepare()
        jsobj = self.input
        target = node.query.find(jsobj).next()
        if not isinstance(target, (TagOnly, TaggedValue)) and not (isinstance(target, dict) and '$$tag' in target):
            return self.__not_tagged_value_case(node, target)
        else:
            return self.__tagged_value_case(node, target)

    def __tagged_value_case(self, node, target):
        tag = target.tag if isinstance(target, (TagOnly, TaggedValue)) else target['$$tag']
        if tag not in node.cases:
            if '*' in node.cases:
                tag = '*'
            elif '*!' in node.cases:
                if tag not in schema.types:
                    tag = '*!'
                else:
                    throw_caty_exception('TagNotMatched', '$type', type=tag)
            else:
                throw_caty_exception('TagNotMatched', '$type', type=tag)
        return self.__exec_cmd(node, tag, target)

    def __not_tagged_value_case(self, node, target):
        t = tag(target)
        if t in node.cases:
            return self.__exec_cmd(node, t, target)
        if '*' in node.cases:
            t = '*'
        elif '*!' in node.cases:
            if t not in schema.types:
                t = '*!'
            else:
                throw_caty_exception('TagNotMatched', '$type', type=t)
        else:
            throw_caty_exception('TagNotMatched', '$type', type=t)
        return self.__exec_cmd(node, t, target)
    
    def __exec_cmd(self, node, tag, jsobj):
        childcmd = node.cases[tag].cmd
        if isinstance(node.cases[tag], UntagCase):
            self.input = untagged(jsobj)
        else:
            self.input = jsobj
        return childcmd.accept(self)

    def visit_binarytag(self, node):
        node._prepare()
        return tagged(node.tag, node.command.accept(self))

    def visit_unarytag(self, node):
        node._prepare()
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
        node._prepare()
        if node.verbose:
            import hotshot, hotshot.stats
            prof = hotshot.Profile("caty.prof")
            m = lambda : node.cmd.accept(self)
            result = prof.runcall(m)
            prof.close()
            stats = hotshot.stats.load("caty.prof")
            stats.sort_stats('cumulative', 'time', 'calls')
            stats.print_stats('python/caty', 20)
            return result
        else:
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
                node.var_storage.new_scope()
                try:
                    self.input = v
                    x = node.cmd.accept(self)
                    if self.__truth(x, node):
                        r[k] = v
                finally:
                    node.var_storage.del_scope()
        return r

    def __truth(self, v, node):
        if node.indef:
            return (v == True and isinstance(v, bool)) or tag(v) == 'True' or tag(v) == 'OK' or tag(v) == 'Indef'
        else:
            return (v == True and isinstance(v, bool)) or tag(v) == 'True' or tag(v) == 'OK'

    def visit_start(self, node):
        node._prepare()
        from caty.core.facility import TransactionAdaptor
        async_queue = self.app.async_queue
        subproc = TransactionAdaptor(CommandExecutor(node.cmd, self.app, self.facility_set), self.facility_set)
        worker = async_queue.push(subproc, subproc.__call__, self.input)
        t = time.time()
        while not worker.isStarted and time.time() - t < 2:
            pass
        return self.input


    def visit_case(self, node):
        node._prepare()
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
                u'CaseUnmatched',
                node.scalar_tag_map.get(type(case_in), [str(type(case_in))])[0]
            )
        else:
            return default.accept(self)

    def visit_json_path(self, node):
        node._prepare()
        from caty.jsontools.selector.stm import Nothing
        stm = node.stm
        try:
            r = stm.select(self.input).next()
            return r
        except (KeyError, Nothing) as e:
            msg = '{0} at {1}, Col {2}'.format(node.path, node.line, node.col)
            throw_caty_exception(u'Undefined', msg)
        except:
            raise

    def visit_begin(self, node):
        node._prepare()
        while True:
            try:
                node.var_storage.new_scope()
                self.input = node.cmd.accept(self)
            except RepeatSignal as e:
                self.input = e.data
            else:
                break
            finally:
                node.var_storage.del_scope()
        return self.input

    def visit_repeat(self, node):
        raise RepeatSignal(self.input)

    def visit_try(self, node):
        node._prepare()
        try:
            self.input = tagged(u'normal', node.pipeline.accept(self))
        except CatySignal as e:
            if self.__is_runaway_signal(e) and node.wall < node.HARD:
                raise
            self.input = tagged(u'signal', e.raw_data)
        except CatyException as e:
            if self.__is_runaway_exception(e) and node.wall < node.HARD:
                raise
            self.input = tagged(u'except', e.to_json())
        except Exception as e:
            if node.wall == node.SUPERHARD:
                import traceback
                from caty.util import error_to_ustr, brutal_encode
                tb = brutal_encode(traceback.format_exc(), u'unicode-escape')
                self.input = tagged(u'except', CatyException(u'RuntimeError', error_to_ustr(e), stack_trace=tb).to_json())
            else:
                raise
        return self.input

    def __is_runaway_exception(self, e):
        try:
            return u'runaway' in self.facility_set['schema'].get_type(e.tag).annotations
        except:
            return False

    def __is_runaway_signal(self, e):
        return isinstance(e.raw_data, TaggedValue) and e.raw_data.tag == u'runaway'

    def visit_catch(self, node):
        node._prepare()
        if node.handler is not None:
            t, self.input = split_tag(self.input)
            if t in node.handler:
                self.input = node.handler[t].accept(self)
        return self.input

    def visit_unclose(self, node):
        node._prepare()
        node.in_schema.validate(self.input)
        self.input, newenv, storage = self.__make_new_env_and_input(node)
        newset = self.__make_new_facility_set(newenv)
        node.pipeline.set_facility(newset)
        node.pipeline.set_var_storage(storage)
        oldset = self.facility_set
        self.facility_set = newset
        try:
            return node.pipeline.accept(self)
        finally:
            self.facility_set = oldset

    def __make_new_facility_set(self, newenv):
        from caty.core.facility import FacilitySet
        facilities = {}
        facilities.update(self.facility_set._facilities)
        facilities['env'] = newenv
        new_set = FacilitySet(facilities, self.facility_set.app)
        facilities['interpreter'] = self.app._interpreter.file_mode(new_set)
        return new_set

    def __make_new_env_and_input(self, node):
        from caty.env import Env
        newenv = Env()
        new_dict = newenv._dict
        env = self.facility_set['env']._dict if not node.clear else {}
        if isinstance(self.input, dict):
            additional = self.input.get('set', {})
            input = self.input.get('input', None)
            unset = self.input.get('unset', [])
        else:
            additional = self.input[0] or {} if self.input else {}
            input = self.input[1] or None if len(self.input) >= 2 else None
            unset = self.input[2] or [] if len(self.input) == 3 else []
        additional_names = set(additional.keys())
        conflict = additional_names.intersection(set(unset))
        if conflict:
            throw_caty_exception(u'UncloseConflict', u'$names', names=u', '.join(conflict))
        new_dict.update(env)
        new_dict.update(additional)
        for n in unset:
            if n in new_dict:
                del new_dict[n]
        storage = self.var_storage.clone()
        for k, v in self.facility_set['env'].items():
            if k in storage.opts:
                storage.opts.pop(k)
            if k in storage.opts['_OPTS']:
                storage.opts['_OPTS'].pop(k)
        for k, v in newenv.items():
            storage.opts[k] = v
        return input, newenv, storage

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
    def __init__(self, opts_ref, args_ref, type_args=[], pos=(None, None), module=None):
        Internal.__init__(self, [], [args_ref[0]], type_args, pos, module)
        self.__opts_ref = opts_ref
        self.__args_ref = args_ref[1:]
        self.__is_file = False

    def setup(self, cmd_name):
        self._cmd_name = cmd_name
        if self._cmd_name[0] == u'/' or '@' in self._cmd_name:
            if '@' not in self._cmd_name:
                self._cmd_name = 'scripts@this:' + self._cmd_name
            self.__is_file = True

    def _make_cmd(self):
        n = self._facilities['env'].get('CATY_APP')['name']
        app = self._system.get_app(n)
        if self.__is_file:
            return self.__script()
        else:
            return self.__make_cmd()

    def __make_cmd(self):
        from caty.core.script.proxy import Proxy
        from caty.core.script.builder import CommandBuilder
        from caty.core.command import VarStorage
        n = self._facilities['env'].get('CATY_APP')['name']
        app = self._system.get_app(n)
        m = self.current_module
        if m:
            profile = m.schema_finder.get_command(self._cmd_name)
        else:
            profile = app.schema_finder.get_command(self._cmd_name)
        cls = profile.get_command_class()
        if isinstance(cls, Proxy):
            c = scriptwrapper(profile, lambda :cls.instantiate(CommandBuilder(self._facilities, app.schema_finder)))(self.__opts_ref, self.__args_ref)
        else:
            c = cls(self.__opts_ref, self.__args_ref)
        c.set_facility(self._facilities)
        c.set_var_storage(self.var_storage)
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


