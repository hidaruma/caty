#coding: utf-8
import traceback
import types
import time

from caty.core.command.exception import *
from caty.command import MafsMixin
from copy import deepcopy
from caty.core.facility import PEND
import caty.util as util
from caty.util.collection import filled_zip
from caty.jsontools.path import build_query
from caty.jsontools import TaggedValue, tag, tagged, untagged, TagOnly, prettyprint, split_tag, normalize_number
from caty.jsontools import jstypes
from caty.core.command import ScriptError, PipelineInterruption, PipelineErrorExit, Command, Internal, scriptwrapper
from caty.core.script.node import *
from caty.core.script.query import *
from caty.core.exception import *
import caty
from caty.core.spectypes import UNDEFINED, INDEF
import caty.core.schema as schema
from caty.core.spectypes import reduce_undefined
from caty.core.schema.errors import JsonSchemaError

from caty.core.script.interpreter.base import BaseInterpreter
from caty.core.script.interpreter.typevar import TypeVarApplier
from caty.util.dev import debug

class CommandExecutor(BaseInterpreter):
    def __init__(self, cmd, app, facility_set):
        self.cmd = cmd
        self.app = app
        self.facility_set = facility_set
        self.schema = facility_set['schema']
        self._mutating_context = MutatingContext()

    def __call__(self, input):
        self.input = input
        self.arg0_stack = []
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
        if 'deprecated' in node.annotations or 'deprecated' in node.defined_module.annotations:
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
                traceback.print_exc()
                msg = u'%s (other infomation is lacking)' % node.name
                self.app._system.deprecate_logger.debug(msg)
        if node._mode: # @console など、特定のモードでしか動かしてはいけないコマンドのチェック処理
            mode = node.env.get('RUN_MODE', [])
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
            if self.arg0_stack:
                node._prepare(self.arg0_stack[-1])
            else:
                node._prepare()
            if node.profile.in_schema.type == 'void':
                self.input = None
                r = exec_func(node)
            else:
                try:
                    node.in_schema.validate(input)
                except JsonSchemaError, e:
                    info = e.error_report(self.app.i18n)
                    print u'[DEBUG]', node.canonical_name
                    print prettyprint(input)
                    throw_caty_exception(u'InputTypeError', prettyprint(info), errorInfo=info)
                if u'no-auto-fill' in node.annotations:
                    r = exec_func(node, input)
                else:
                    r = exec_func(node, node.in_schema.fill_default(input))
            if node.out_schema.type == 'void':
                r = None
            else:
                try:
                    node.out_schema.validate(r)
                except JsonSchemaError, e:
                    info = e.error_report(self.app.i18n)
                    print prettyprint(r)
                    throw_caty_exception(u'OutputTypeError', prettyprint(info), errorInfo=info)
            if 'commit-point' in node.profile_container.get_annotations():
                for n in node.facility_names:
                    getattr(node, n).commit()
            return r
        except SystemResourceNotFound as e:
            #traceback.print_exc()
            raise
        except ContinuationSignal as e:
            #node.signal_schema.validate(e.data)
            raise
        except CatySignal as e:
            #node.signal_schema.validate(e.raw_data)
            raise e
        except CatyException as e:
            if self.facility_set['env'].get('DEBUG'):
                msg = u'[DEBUG] {0}: Col {1}, Line {2}'.format(node.canonical_name, node.col, node.line)
                util.cout.writeln(msg)
            import sys
            info = sys.exc_info()[2]
            if e.tag in ('UnexpectedArg', 'UnexpectedOption', 'MissingArg', 'MissingOption', 'InputTypeError'):
                raise # このエラーの時はプロファイルが決定できないのでonly句のチェックなどは無理
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

    def visit_parlist(self, node):
        node._prepare()
        r = []
        node.in_schema.validate(self.input)
        for val, cmd in filled_zip(self.input, node.values, UNDEFINED):
            self.input = val
            if cmd is UNDEFINED:
                if node.wildcard:
                    r.append(node.values[-1].accept(self))
                else:
                    r.append(UNDEFINED)
            else:
                r.append(cmd.accept(self))
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

    def visit_parobject(self, node):
        node._prepare()
        node.in_schema.validate(self.input)
        obj = {}
        prev_input = {}
        prev_input.update(self.input)
        for name, cmd in node.iteritems():
            self.input = prev_input.pop(cmd.name, UNDEFINED)
            obj[name] = cmd.accept(self)
        for k , v in prev_input.items():
            if node.wildcard:
                self.input = v
                obj[k] = node.wildcard.accept(self)
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
            raise Exception(u'Variable %%%s is not defined' % node.var_name)
        if r is UNDEFINED and node.default is not UNDEFINED:
            r = node.default
        return r

    def visit_argref(self, node):
        node._prepare()
        argv = node.var_storage.opts['_ARGV']
        try:
            if node.arg_num == 0 and self.arg0_stack: #メソッドチェイン内部0への参照
                return self.arg0_stack[-1]
            return argv[node.arg_num]
        except:
            if node.optional:
                return node.default
            else:
                raise Exception(u'Variable %%%d is not defined' % node.arg_num)

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
        elif node.iter:
            if not hasattr(self.input, '__iter__'):
                throw_caty_exception(u'InputTypeError', u'Input data must be an iterator')
            node.context = self.input
            return self.__iter_stream(node)
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
                node.var_storage.opts['_value'] = i[n] if isinstance(i, dict) else v
                if not v is UNDEFINED:
                    r.append(node.cmd.accept(self))
            except BreakSignal:
                break
            finally:
                node.var_storage.del_scope()
            n+=1
        return r


    def __iter_stream(self, node):
        n = 0
        for v in node.context:
            self.input = v
            try:
                node.var_storage.new_scope()
                node.var_storage.opts['_key'] = n
                node.var_storage.opts['_value'] = v
                if not v is UNDEFINED:
                    r = node.cmd.accept(self)
            except BreakSignal:
                break
            finally:
                node.var_storage.del_scope()
            yield r
            n+=1

    def __iter_obj_as_array(self, node):
        r = []
        for k, v in self.input.iteritems():
            self.input = v
            try:
                node.var_storage.new_scope()
                node.var_storage.opts['_key'] = k
                node.var_storage.opts['_value'] = v
                if not v is UNDEFINED:
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
                if not v is UNDEFINED:
                    r.append(node.cmd.accept(self))
            except BreakSignal:
                break
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
                i = i.items()
            else:
                i = enumerate(i)
            for k, v in i:
                node.var_storage.new_scope()
                node.var_storage.opts['_key'] = k
                node.var_storage.opts['_value'] = v
                try:
                    self.input = v
                    if not v is UNDEFINED:
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
                    if not v is UNDEFINED:
                        x = node.cmd.accept(self)
                        if self.__truth(x, node):
                            r[k] = v
                finally:
                    node.var_storage.del_scope()
        return r

    def __truth(self, v, node):
        if node.indef:
            return (v == True and isinstance(v, bool)) or tag(v) == 'True' or tag(v) == 'OK' or tag(v) == 'Indef' or v is INDEF
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
        t = json.tag(self.input)
        if t == u'__normal':
            self.input = json.untagged(self.input)
        elif t in (u'__signal', u'__except'):
            return self.input
        try:
            self.input = tagged(u'__normal', node.pipeline.accept(self))
        except CatySignal as e:
            if self.schema.is_runaway_signal(e) and node.wall < node.HARD:
                raise
            self.input = tagged(u'__signal', e.raw_data)
        except CatyException as e:
            if self.schema.is_runaway_exception(e) and node.wall < node.HARD:
                raise
            self.input = tagged(u'__except', e.to_json())
        except Exception as e:
            if node.wall == node.SUPERHARD:
                import traceback
                from caty.util import error_to_ustr, brutal_encode
                tb = brutal_encode(traceback.format_exc(), u'unicode-escape')
                self.input = tagged(u'__except', CatyException(u'RuntimeError', error_to_ustr(e), stack_trace=tb).to_json())
            else:
                raise
        return self.input

    def visit_catch(self, node):
        node._prepare()
        if node.handler is not None:
            t, self.input = split_tag(self.input)
            t = t.lstrip('_')
            if t in node.handler:
                self.input = node.handler[t].accept(self)
            elif node.handler.get('*'):
                self.input = node.handler['*'].accept(self)
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
            throw_caty_exception(u'SetUnsetConflict', u'$names', names=u', '.join(conflict))
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

    def visit_choice_branch(self, node):
        import random
        node._prepare()
        c = random.choice(node.cases)
        return c.cmd.accept(self)

    def visit_empty(self, node):
        node._prepare()
        return self.input

    def visit_method_chain(self, node):
        node._prepare()
        pipeline = node.proxy.instantiate(
            MethodChainCommandBuilder(node.builder.facilities, 
                                      node.builder.namespace.get_class(self.input['className'])))
        node.set_pipeline(pipeline)
        self.arg0_stack.append(self.input['state'])
        self.input = None
        self.input = pipeline.accept(self)
        self.arg0_stack.pop(0)
        return self.input

    def visit_fold(self, node):
        node._prepare()
        try:
            node.in_schema.validate(self.input)
        except JsonSchemaError, e:
            info = e.error_report(self.app.i18n)
            throw_caty_exception(u'InputTypeError', prettyprint(info), errorInfo=info)
        input = self.input[0]
        init = self.input[1]
        n = 0
        acc = init
        for v in input:
            self.input = v
            try:
                node.var_storage.new_scope()
                node.var_storage.opts['_key'] = n
                node.var_storage.opts['_acc'] = acc
                if not v is UNDEFINED:
                    acc = node.cmd.accept(self)
            except BreakSignal:
                break
            finally:
                node.var_storage.del_scope()
            n+=1
        self.input = acc
        return self.input

    @property
    def in_schema(self):
        return self.cmd.in_schema

    @property
    def out_schema(self):
        return self.cmd.out_schema

    def set_facility(self, f, target_app=None):
        self.facility_set = f
        self.cmd.set_facility(f, target_app)

    @property
    def var_storage(self):
        return self.cmd.var_storage

    def set_var_storage(self, v):
        self.cmd.set_var_storage(v)

    def visit_break(self, node):
        raise BreakSignal()

    def visit_partag(self, node):
        node._prepare()
        t, o = split_tag(self.input)
        self.input = t
        t = node.tagcmd.accept(self)
        self.input = o
        return tagged(t, node.command.accept(self))

    def visit_fetch(self, node):
        node._prepare()
        node.in_schema.validate(self.input)
        fetcher = Fetcher()
        labels = {}
        context = []
        def filter(data, qo, orig, depth=0):
            if data is UNDEFINED:
                if qo.optional:
                    return UNDEFINED
                else:
                    throw_caty_exception(u'Undefined', '.'.join(context) or u'undefined')
            through = False
            resolved = False
            if qo.type == u'any' and qo.value in labels:
                qo = labels[qo.value]
            try:
                node.in_schema.validate(data)
            except:
                return data
            else:
                orig = data
                if qo.type == u'address':
                    return data
                if (node.deref_depth > depth):
                    if json.tag(data) != u'__r':
                        #参照型ではなく_selfに参照がある場合、あらかじめderefが済んでいるものとする。
                        data = data
                    else:
                        data = fetcher.fetch_addr(data, self.app, self.facility_set, True)
                        depth += 1
                    resolved = True
                else:
                    return data
            if qo.type == u'type':
                if qo.value in (u'any', u'_'):
                    if isinstance(data, dict):
                        qo = ObjectQuery({}, TypeQuery(None, u'any'))
                    elif isinstance(data, list):
                        qo = ArrayQuery([], TypeQuery(None, u'any'))
                    elif isinstance(data, TaggedValue):
                        qo = TagQuery(data.tag, TypeQuery(None, u'any'))
                    else:
                        through = True
            if qo.label:
                labels[qo.label] = qo
            if through:
                return data
            if qo.type == u'tag':
                if json.tag(data) == qo.tag:
                    return filter_internal(data, qo.value, orig, depth)
                else:
                    throw_caty_exception(u'BadInput', json.pp(data))
            elif qo.type == u'object':
                r = {}
                if not isinstance(data, dict):
                    throw_caty_exception(u'BadInput', json.pp(data))
                obj = {}
                obj.update(data)
                for k, q in qo.queries.items():
                    context.append(k)
                    r[k] = filter_internal(obj.pop(k, UNDEFINED), q, orig, depth=depth)
                    context.pop(-1)
                if qo.wildcard:
                    for k, v in obj.items():
                        if k == '_self':
                            r[k] = v
                        else:
                            context.append(k)
                            r[k] = filter_internal(v, qo.wildcard, orig, depth=depth)
                            context.pop(-1)
                
                if not node.noself:
                    if resolved and '_self' not in r:
                        r['_self'] = orig
                return r
            elif qo.type == u'array':
                if not isinstance(data, list):
                    throw_caty_exception(u'BadInput', json.pp(data))
                r = []
                ls = data[0:len(qo.queries)]
                num = 0
                for q, v in zip(qo.queries, ls):
                    context.append(str(num))
                    r.append(filter_internal(v, q, orig, depth=depth))
                    context.pop(-1)
                    num += 1
                if qo.repeat:
                    for v in data[len(qo.queries):]:
                        context.append(str(num))
                        r.append(filter_internal(v, qo.repeat, orig, depth=depth))
                        num += 1
                        context.pop(-1)
                return r
            elif qo.type == u'address':
                if json.tag(orig) == '__r':
                    p = json.untagged(orig)
                else:
                    p = json.untagged(orig['_self'])
                return json.tagged(u'__r', {u't': p['type'], u'a': [p['arg'], u'.'.join(['$'] +context)]})
            assert False, qo.type
        def filter_internal(val, q, o, depth):
            if q.type == 'type' and q.value in (u'any', u'_'):
                if isinstance(val, dict):
                    r = {}
                    for k, v in val.items():
                        r[k] = filter(v, q, o, depth)
                    return r
                elif isinstance(val, list):
                    return map(lambda v: filter(v, q, o, depth), val)
            return filter(val, q, o, depth)
        return filter(self.input, node.queries, self.input)

    def visit_mutating(self, node):
        node._prepare()
        node.in_schema.validate(self.input)
        if json.tag(self.input) == u'__mutate':
            req = json.untagged(self.input)
        else:
            req = {"update": {"set":{}, "unset":[], "clear":False}}
        env = self.facility_set._facilities['env']
        if node.envname in env:
            oldval = env[node.envname]
            assert isinstance(oldval, dict)
            val = deepcopy(oldval)
        else:
            oldval = UNDEFINED
            val = {}
        try:
            if u'value' in req:
                self.input = req[u'value']
            env._dict[node.envname] = json.modify(val, req.get(u'update', {}))
            self._mutating_context.enter(node.envname, env._dict[node.envname], {})
            oldmut = env.get(u'_MUTATING')
            env._dict[u'_MUTATING'] = node.envname
            r = node.pipeline.accept(self)
            node.out_schema.validate(r)
            if json.tag(r) == u'__mutate':
                res = json.untagged(r)
                outval = res.pop(u'value')
            else:
                res = {"update": {"set":{}, "unset":[], "clear":False}}
                outval = r
            updater = json.compose_update(req.get(u'update', {}), res.get(u'update', {}))
            return json.tagged(u'__mutate', {u'value': outval, u'update': updater})
        finally:
            self._mutating_context.exit()
            if oldval != UNDEFINED:
                env._dict[node.envname] = oldval
            if oldmut:
                env._dict[u'_MUTATING'] = oldmut

    def visit_commitm(self, node):
        node._prepare()
        if json.tag(self.input) == u'__mutate':
            req = json.untagged(self.input)
        else:
            req = {"update": {"set":{}, "unset":[], "clear":False}, 'value': self.input}
        if self._mutating_context.level == 0:
            if not node.envname:
                throw_caty_exception(u'SyntaxError', u'commitm <NAME>')
            env = self.facility_set._facilities['env']
            val = env._dict.get(node.envname, {})
            env._dict[node.envname] = json.modify(val, req.get(u'update', {}))
            mode = env.get('RUN_MODE', [])
            if 'console' in mode:
                self.facility_set['__console__'].env[node.envname] = env._dict[node.envname]
            req['update'] = {}
            self.input = req['value']
        else:
            self.input = self._mutating_context.apply(req)
        return self.input

class MutatingContext(object):
    def __init__(self):
        self._context = []
        self.level = 0

    def enter(self, name, value, operator):
        self.level += 1
        self._context.append([name, value, operator])

    def exit(self):
        self.level -= 1
        self._context.pop(-1)

    def apply(self, req):
        self._context[-1][1] = json.modify(self._context[-1][1], req.get('update', {}))
        self._context[-1][2] = json.compose_update(self._context[-1][1], req.get('update', {}))
        req['update'] = {}
        return json.tagged(u'__mutate', req)

class BreakSignal(Exception):
    pass

from caty.core.command import Builtin, Command, scriptwrapper
from caty.core.exception import CatyException
from caty.core.script.builder import CommandBuilder, NullCommand
class MethodChainCommandBuilder(CommandBuilder):

    def build(self, proxy, type_args, opts_ref, args_ref, pos, module):
        u"""コマンド文字のチャンクをコマンド名と引数のリストに分割し、呼び出し可能なコマンドオブジェクトを返す。
        """
        try:
            try:
                profile = self.namespace.get_command(proxy.name)
            except Exception as e:
                if proxy.module:
                    profile = proxy.module.schema_finder.get_command(proxy.name)
                else:
                    raise e
            return self.make_cmd(profile, type_args, opts_ref, args_ref, pos, module)
        except CatyException as e:
            if e.tag == 'CommandNotFound':
                return NullCommand(e)
            raise

from caty.command import MafsMixin
from caty.core.script.builder import CommandBuilder

class _CallCommand(MafsMixin, CommandBuilder, Internal):
    def __init__(self, call_opts, callee_args, type_args=[], pos=(None, None), module=None):
        args_ref = []
        opts_ref = []
        cmd = None
        for arg in callee_args:
            if 'arg' not in arg.type:
                opts_ref.append(arg)
            elif cmd == None:
                cmd = arg
            else:
                args_ref.append(arg)
        Internal.__init__(self, call_opts, [cmd], type_args, pos, module)
        self.__opts_ref = opts_ref
        self.__args_ref = args_ref
        self.__is_file = False

    def setup(self, opts, cmd_name):
        from caty.util.path import is_mafs_path
        self._cmd_name = cmd_name
        self._app_name = opts['app']
        self.__is_file = is_mafs_path(cmd_name)
        if self.__is_file:
            if '@' not in cmd_name:
                self._cmd_name = 'scripts@this:' + self._cmd_name

    def _make_cmd(self):
        if self.__is_file:
            return self.__script()
        else:
            return self.__make_cmd()

    def __make_cmd(self):
        from caty.core.script.proxy import Proxy
        from caty.core.script.builder import CommandBuilder
        from caty.core.command import VarStorage
        if not self._app_name:
            n = self._facilities['env'].get('APPLICATION')['name']
        else:
            n = self._app_name
        app = self._system.get_app(n)
        CommandBuilder.__init__(self, self._facilities, app.schema_finder)
        profile = app.schema_finder.get_command(self._cmd_name)
        c = CommandBuilder.make_cmd(self, profile, [], self.__opts_ref, self.__args_ref, (self.col, self.line), None)
        c.set_facility(self._facilities, app)
        c.set_var_storage(self.var_storage)
        return CommandExecutor(c, app, self._facilities)

    def __script(self):
        self.var_loader.opts = self.__opts_ref
        self.var_loader.args = self.__args_ref
        opts = self.var_loader._load_opts(self.var_storage.opts, self.var_storage.args)
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


