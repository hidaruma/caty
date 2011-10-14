#coding: utf-8
u"""Caty スクリプトノードモジュール。
Caty では switch, dispatch, object 生成などはすべてコマンドとして実装する。
"""

from caty.jsontools.path import build_query
from caty.jsontools import TaggedValue, tag, tagged, untagged, TagOnly
from caty.jsontools import jstypes
from caty.core.command import ScriptError, PipelineInterruption, PipelineErrorExit, Command, Syntax, VarStorage
import caty
import types

schema = u''

class ScalarBuilder(Syntax):
    command_decl = u"""command scalar-builder<T> :: void -> T
                        reads schema
                        refers python:caty.core.script.node.ScalarBuilder;
    """

    def set_value(self, value):
        if isinstance(value, str):
            v = unicode(value)
        else:
            v = value
        self.value = v

    def accept(self, visitor):
        return visitor.visit_scalar(self)

class ListBuilder(Syntax):
    command_decl = u"""command list-builder<T> :: T -> array
                        refers python:caty.core.script.node.ListBuilder;
    """
    def __init__(self, *args, **kwds):
        Syntax.__init__(self, *args, **kwds)
        self.values= []

    def set_values(self, values):
        for v in values:
            if isinstance(v, Command):
                self.values.append(v)
            else:
                s = ScalarBuilder()
                s.set_value(v)
                self.values.append(s)

    def set_facility(self, facilities):
        for v in self.values:
            v.set_facility(facilities)
   
    def set_var_storage(self, storage):
        for v in self.values:
            v.set_var_storage(storage)

    def __iter__(self):
        return iter(self.values)

    def accept(self, visitor):
        return visitor.visit_list(self)

class ObjectBuilder(Syntax):
    command_decl = u"""command __object-builder<T> :: T -> object
                        refers python:caty.core.script.node.ObjectBuilder;
    """
    def __init__(self, *args, **kwds):
        Syntax.__init__(self, *args, **kwds)
        self.__nodes = {}

    def add_node(self, node):
        if node.name in self.__nodes:
            raise KeyError(node.name)
        self.__nodes[node.name] = node

    def set_facility(self, facilities):
        for n in self.__nodes.values():
            n.set_facility(facilities)

   
    def set_var_storage(self, storage):
        for v in self.__nodes.values():
            v.set_var_storage(storage)


    def accept(self, visitor):
        return visitor.visit_object(self)

    def iteritems(self):
        return self.__nodes.iteritems()

class VarStore(Syntax):
    command_decl = u"""command __var-store<T> :: T -> T
                        refers python:caty.core.script.node.VarStore;
    """
    def __init__(self, *args, **kwds):
        Syntax.__init__(self, args[1:], **kwds)
        self.__var_name = args[0]

    @property
    def var_name(self):
        return self.__var_name

    def accept(self, visitor):
        return visitor.visit_varstore(self)

class VarRef(Syntax):
    command_decl = u"""command __var-ref<T> :: void -> T
                        refers python:caty.core.script.node.VarRef;
    """
    def __init__(self, name, optional):
        Syntax.__init__(self)
        self.__var_name = name
        self.__optional = optional

    def accept(self, visitor):
        return visitor.visit_varref(self)

    @property
    def var_name(self):
        return self.__var_name

    @property
    def optional(self):
        return self.__optional

class ArgRef(Syntax):
    command_decl = u"""command __arg-ref<T> :: void -> T
                        refers python:caty.core.script.node.ArgRef;
    """
    def __init__(self, num, optional):
        Syntax.__init__(self)
        self.__arg_num = int(num)
        self.__optional = optional


    def accept(self, visitor):
        return visitor.visit_argref(self)

    @property
    def arg_num(self):
        return self.__arg_num

    @property
    def optional(self):
        return self.__optional

class ConstNode(object):
    def __init__(self, name, value):
        self.name = name
        self.cmd = ScalarBuilder()
        self.cmd.set_value(value)

    def set_facility(self, facilities):
        self.name = self.name if isinstance(self.name, unicode) else unicode(self.name, facilities['env'].read_mode.get('SYSTEM_ENCODING'))
   
    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)

    def accept(self, visitor):
        return self.cmd.accept(visitor)

class CommandNode(object):
    def __init__(self, name, cmd):
        self.name = name
        self.cmd = cmd

    def set_facility(self, facilities):
        self.cmd.set_facility(facilities)
        self.name = self.name if isinstance(self.name, unicode) else unicode(self.name, facilities['env'].read_mode.get('SYSTEM_ENCODING'))

    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)

    def accept(self, visitor):
        return self.cmd.accept(visitor)

class Dispatch(Syntax):
    command_decl = u"""command __dispatch {"seq": boolean?, "multi": boolean?} :: any -> any
                        refers python:caty.core.script.node.Dispatch;
    """

    def __init__(self):
        Syntax.__init__(self)
        self.__cases = {}
        self.__query = build_query('$')
        self.__scalar_tag_map = {
            types.IntType: ['integer', 'number'],
            types.FloatType: ['number'],
            types.UnicodeType: ['string'], 
            types.BooleanType: ['boolean'], 
            types.NoneType: ['null'], 
            types.ListType: ['array'],
            types.DictType: ['object'],
            types.StringType: ['binary'],
            caty._Undefined: ['undefined'],
        }
    
    @property
    def cases(self):
        return self.__cases

    @property
    def query(self):
        return self.__query

    @property
    def scalar_tag_map(self):
        return self.__scalar_tag_map

    def add_case(self, case):
        if case.tag in self.__cases:
            raise Exception(case.tag)
        self.__cases[case.tag] = case

    def set_facility(self, facilities):
        for k ,v in self.__cases.items():
            v.set_facility(facilities)

    def set_var_storage(self, storage):
        for v in self.__cases.values():
            v.set_var_storage(storage)


    def accept(self, visitor):
        return visitor.visit_when(self)

    def execute(self, input):
        jsobj = input
        target = self.__query.find(jsobj).next()
        if not isinstance(target, TaggedValue) and not (isinstance(target, dict) and '$$tag' in target):
            return self.not_tagged_value_case(target)
        else:
            return self.tagged_value_case(target)



class TagBuilder(Syntax):
    command_decl = u"""command __add-tag :: any -> any
                        refers python:caty.core.script.node.TagBuilder;
    """
    def __init__(self, tag, cmd):
        Syntax.__init__(self)
        self.command = cmd
        self.tag = tag

    def set_facility(self, facilities):
        self.command.set_facility(facilities)

    def set_var_storage(self, storage):
        self.command.set_var_storage(storage)

    def accept(self, visitor):
        return visitor.visit_binarytag(self)

class UnaryTagBuilder(Syntax):
    command_decl = u"""command __unary-tag :: any -> any
                        refers python:caty.core.script.node.UnaryTagBuilder;
    """
    def __init__(self, tag):
        Syntax.__init__(self)
        self.tag = tag
    
    def set_facility(self, facilities):
        pass

    def accept(self, visitor):
        return visitor.visit_unarytag(self)

class Case(object):
    def __init__(self, tag, cmd):
        self.tag= tag
        self.cmd = cmd

    def set_facility(self, facilities):
        self.cmd.set_facility(facilities)

    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)
    
    def accept(self, visitor):
        return self.cmd.accept(visitor)

class UntagCase(Case):pass

class Each(Syntax):
    command_decl = u"""command each-functor-applied<T> {"seq":boolean?} :: [T*] -> [T*]
                                                       {"seq":boolean?, "prop": boolean} :: object -> object
                        refers python:caty.core.script.node.Each;"""
    def __init__(self, cmd, opts_ref):
        Syntax.__init__(self, opts_ref)
        self.cmd = cmd

    def _init_opts(self):
        Command._init_opts(self)
        o = self.var_storage.opts
        a = o['_ARGV']
        v = a[1:] if a else [u'']
        self._args = v

    def _prepare(self):
        Command._prepare(self)

    def setup(self, opts, *ignore):
        self.__prop = opts['prop'] if 'prop' in opts else None

    @property
    def prop(self):
        return self.__prop

    def set_facility(self, facilities):
        self.cmd.set_facility(facilities)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        self.cmd.set_var_storage(storage)

    def accept(self, visitor):
        return visitor.visit_each(self)

class Time(Syntax):
    command_decl = u"""
    command time-functor<T> :: T -> T
        refers python:caty.core.script.node.Time;
    """
    def __init__(self, cmd, ignore):
        Syntax.__init__(self)
        self.cmd = cmd

    def set_facility(self, facilities):
        Syntax.set_facility(self, facilities)
        self.cmd.set_facility(facilities)

    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)
        Syntax.set_var_storage(self, storage)


    def accept(self, visitor):
        return visitor.visit_time(self)

class Take(Syntax):
    command_decl = u"""
    command take-functor<T> :: [T*] -> [T*]
        refers python:caty.core.script.node.Take;
    """
    def __init__(self, cmd, opts_ref):
        Syntax.__init__(self, opts_ref)
        self.cmd = cmd

    def set_facility(self, facilities):
        self.cmd.set_facility(facilities)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        self.cmd.set_var_storage(storage)

    def accept(self, visitor):
        return visitor.visit_take(self)

class Start(Syntax):
    command_decl = u"""
    command start-functor<T> :: T -> never
        refers python:caty.core.script.node.Start;
    """
    def __init__(self, cmd, ignore):
        Syntax.__init__(self)
        self.cmd = cmd

    def set_facility(self, facilities):
        Syntax.set_facility(self, facilities)
        self.cmd.set_facility(facilities)

    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)
        Syntax.set_var_storage(self, storage)

    def accept(self, visitor):
        return visitor.visit_start(self)

class PipelineFragment(Syntax):
    command_decl = u"""
    command __pipeline-gragment-functor<S, T> :: S -> T
        refers python:caty.core.script.node.PipelineFragment;
    """
    def __init__(self, cmd, fragment_name):
        Syntax.__init__(self)
        self.cmd = cmd
        self._name = fragment_name

    def set_facility(self, facilities):
        self.cmd.set_facility(facilities)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        self.cmd.set_var_storage(storage)

    def accept(self, visitor):
        return self.cmd.accept(visitor)

class ActionEnvelope(Syntax):
    command_decl = u"""
    command __action-envelope {*:any} [string*] :: WebInput | void -> Response | Redirect
        refers python:caty.core.script.node.ActionEnvelope;
    """
    def __init__(self, script):
        Syntax.__init__(self)
        self.cmd = script

    def set_facility(self, facilities):
        self.cmd.set_facility(facilities)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        self.cmd.set_var_storage(storage)

    def accept(self, visitor):
        new_storage = VarStorageForAction(self.var_storage)
        self.cmd.set_var_storage(new_storage)
        return self.cmd.accept(visitor)

class VarStorageForAction(VarStorage):
    def __init__(self, storage):
        self.opts = storage.opts
        if len(storage.args) > 1:
            self.args = [storage.args[1]] + storage.args[1:]
        else:
            self.args = storage.args
        self.opts['_ARGV'] = self.args
        self.args_stack = []
        self.opts_stack = []

    def new_masked_scope(self, opts, args):
        self.opts_stack.append(self.opts)
        self.args_stack.append(self.args)
        self.opts = OverlayedDict(opts if opts else {})
        if len(args) >= 1:
            self.args = [args[0]] + args
        else:
            self.args = args
        self.opts['_ARGV'] = self.args

