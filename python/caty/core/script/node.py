#coding: utf-8
u"""Caty スクリプトノードモジュール。
Caty では switch, dispatch, object 生成などはすべてコマンドとして実装する。
"""

from caty.jsontools.path import build_query
from caty.jsontools import TaggedValue, tag, tagged, untagged, TagOnly, prettyprint
from caty.jsontools import jstypes
from caty.core.exception import *
from caty.core.command import ScriptError, PipelineInterruption, PipelineErrorExit, Command, Syntax, VarStorage
import caty
import types

schema = u''

class ScalarBuilder(Syntax):
    command_decl = u"""
    /**
     * 
     */
    command __scalar-builder<T default any> :: void -> T
                        reads schema
                        refers python:caty.core.script.node.ScalarBuilder;
    """

    def set_value(self, value):
        v = value
        self.value = v

    def accept(self, visitor):
        return visitor.visit_scalar(self)

class ListBuilder(Syntax):
    command_decl = u"""
    /**
     * 
     */
    command __list-builder<T default any> :: T -> array
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

    def set_facility(self, facilities, ignore=None):
        for v in self.values:
            v.set_facility(facilities)
   
    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        for v in self.values:
            v.set_var_storage(storage)

    def __iter__(self):
        return iter(self.values)

    def accept(self, visitor):
        return visitor.visit_list(self)

class ParallelListBuilder(ListBuilder):
    command_decl = u"""
    /**
     * 
     */
    command __parellel-list-builder :: array -> array
                        refers python:caty.core.script.node.ListBuilder;
    """

    def set_wildcard(self, wildcard):
        self.wildcard = wildcard

    def accept(self, visitor):
        return visitor.visit_parlist(self)

class ObjectBuilder(Syntax):
    command_decl = u"""
    /**
     * 
     */
    command __object-builder<T default any> :: T -> object
                        refers python:caty.core.script.node.ObjectBuilder;
    """
    def __init__(self, *args, **kwds):
        Syntax.__init__(self, *args, **kwds)
        self.__nodes = {}

    def add_node(self, node):
        if node.name in self.__nodes:
            raise KeyError(node.name)
        self.__nodes[node.name] = node

    def set_facility(self, facilities, app=None):
        for n in self.__nodes.values():
            n.set_facility(facilities, app)

   
    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        for v in self.__nodes.values():
            v.set_var_storage(storage)


    def accept(self, visitor):
        return visitor.visit_object(self)

    def iteritems(self):
        return self.__nodes.iteritems()

    def items(self):
        return self.__nodes.items()

class ParallelObjectBuilder(Syntax):
    command_decl = u"""
    /**
     * 
     */
    command __parallel-object-builder :: object -> object
                        refers python:caty.core.script.node.ParallelObjectBuilder;
    """
    def __init__(self, *args, **kwds):
        Syntax.__init__(self, *args, **kwds)
        self.__nodes = {}
        self.wildcard = None

    def add_node(self, node):
        if node.name == u'*':
            if self.wildcard:
                raise KeyError(node.name)
            else:
                self.wildcard = node
            return
        if node.name in self.__nodes:
            raise KeyError(node.name)
        self.__nodes[node.name] = node
    
    def set_facility(self, facilities, app=None):
        for n in self.__nodes.values():
            n.set_facility(facilities, app)
        if self.wildcard:
            self.wildcard.set_facility(facilities, app)
   
    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        for v in self.__nodes.values():
            v.set_var_storage(storage)
        if self.wildcard:
            self.wildcard.set_var_storage(storage)

    def accept(self, visitor):
        return visitor.visit_parobject(self)

    def iteritems(self):
        return self.__nodes.iteritems()

    def items(self):
        return self.__nodes.items()

class VarStore(Syntax):
    command_decl = u"""
    /**
     * 変数定義: '>' VarName
     */
    command __var-store<T default any> :: T -> T
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
    command_decl = u"""
    /**
     * 変数参照: '%' VarName ['?' ['=' ScalarLiteral]]
     */
    command __var-ref<T default any> :: void -> T
                        refers python:caty.core.script.node.VarRef;
    """
    def __init__(self, name, optional, default):
        Syntax.__init__(self)
        self.__var_name = name
        self.__optional = optional
        self.__default = default

    def accept(self, visitor):
        return visitor.visit_varref(self)

    @property
    def var_name(self):
        return self.__var_name

    @property
    def optional(self):
        return self.__optional

    @property
    def default(self):
        return self.__default

from caty.core.spectypes import UNDEFINED
class ArgRef(Syntax):
    command_decl = u"""
    /**
     * 引数参照: '%' ("0"|"1"|...|"9")+
     */
    command __arg-ref<T default any> :: void -> T
                        refers python:caty.core.script.node.ArgRef;
    """
    def __init__(self, num, optional, default):
        Syntax.__init__(self)
        self.__arg_num = int(num)
        self.__optional = optional
        self.__default = default

    def accept(self, visitor):
        return visitor.visit_argref(self)

    @property
    def arg_num(self):
        return self.__arg_num

    @property
    def optional(self):
        return self.__optional

    @property
    def default(self):
        return self.__default

class ConstNode(object):
    def __init__(self, name, value):
        self.name = name
        self.cmd = ScalarBuilder()
        self.cmd.set_value(value)

    def set_facility(self, facilities, ignore=None):
        self.name = self.name if isinstance(self.name, unicode) else unicode(self.name, facilities['env'].create(u'reads').get('SYS_ENCODING'))
   
    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)

    def accept(self, visitor):
        return self.cmd.accept(visitor)

class CommandNode(object):
    def __init__(self, name, cmd):
        self.name = name
        self.cmd = cmd

    def set_facility(self, facilities, app=None):
        self.cmd.set_facility(facilities, app)
        self.name = self.name if isinstance(self.name, unicode) else unicode(self.name, facilities['env'].create(u'reads').get('SYS_ENCODING'))

    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)

    def accept(self, visitor):
        return self.cmd.accept(visitor)

import decimal
_scalar_tag_map = {
    types.IntType: ['integer', 'number'],
    decimal.Decimal: ['number'],
    types.UnicodeType: ['string'], 
    types.BooleanType: ['boolean'], 
    types.NoneType: ['null'], 
    types.ListType: ['array'],
    types.DictType: ['object'],
    types.StringType: ['binary'],
    caty._Undefined: ['undefined'],
    caty.ForeignObject: ['foreign'],
}
class Dispatch(Syntax):
    command_decl = u"""
    /**
     * タイプタグ分岐: 'when" ['--seq'] | ['--multi'] '{' Script '}'
     */
    command __dispatch {"seq": boolean?, "multi": boolean?} :: any -> any
                        refers python:caty.core.script.node.Dispatch;
    """

    def __init__(self, selector=None):
        self.__cases = {}
        self.__query = selector
        self.__scalar_tag_map = _scalar_tag_map
        Syntax.__init__(self)
    
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

    def set_facility(self, facilities, app=None):
        for k ,v in self.__cases.items():
            v.set_facility(facilities, app)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
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
    command_decl = u"""command __tag :: any -> any
                        refers python:caty.core.script.node.TagBuilder;
    """
    def __init__(self, tag, cmd):
        Syntax.__init__(self)
        self.command = cmd
        self.tag = tag

    def set_facility(self, facilities, app=None):
        self.command.set_facility(facilities, app)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
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
    
    def set_facility(self, facilities, ignore=None):
        pass

    def accept(self, visitor):
        return visitor.visit_unarytag(self)

class ExtendedTag(object):
    def _do_tag_pipeline(self, visitor):
        prev = visitor.input
        visitor.input = None
        self.tag = self.tagcmd.accept(visitor)
        if not isinstance(self.tag, unicode):
            throw_caty_exception(u'OutputTypeError', u'Not a string: %s' % prettyprint(self.tag))
        visitor.input = prev

class ExtendedTagBuilder(Syntax, ExtendedTag):
    command_decl = u"""command __ex_tag :: any -> any
                        refers python:caty.core.script.node.ExtendedTagBuilder;
    """
    def __init__(self, tag, cmd):
        Syntax.__init__(self)
        self.command = cmd
        self.tagcmd = tag
        self.tag = None

    def set_facility(self, facilities, app=None):
        self.tagcmd.set_facility(facilities, app)
        self.command.set_facility(facilities, app)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        self.command.set_var_storage(storage)
        self.tagcmd.set_var_storage(storage)

    def accept(self, visitor):
        self._do_tag_pipeline(visitor)
        return visitor.visit_binarytag(self)

class ExtendedUnaryTagBuilder(Syntax, ExtendedTag):
    command_decl = u"""command __ex-unary-tag :: any -> any
                        refers python:caty.core.script.node.ExtendedUnaryTagBuilder;
    """
    def __init__(self, tag):
        Syntax.__init__(self)
        self.tagcmd = tag
        self.tag = None

    def set_facility(self, facilities, app=None):
        self.tagcmd.set_facility(facilities, app)

    def set_var_storage(self, storage):
        self.tagcmd.set_var_storage(storage)

    def accept(self, visitor):
        self._do_tag_pipeline(visitor)
        return visitor.visit_unarytag(self)

class ParTagBuilder(Syntax):
    command_decl = u"""command __par_tag :: univ -> univ
                        refers python:caty.core.script.node.ParTagBuilder;
    """
    def __init__(self, tag, cmd):
        Syntax.__init__(self)
        self.command = cmd
        self.tagcmd = tag
        self.tag = None

    def set_facility(self, facilities, app=None):
        self.tagcmd.set_facility(facilities, app)
        self.command.set_facility(facilities, app)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        self.command.set_var_storage(storage)
        self.tagcmd.set_var_storage(storage)

    def accept(self, visitor):
        return visitor.visit_partag(self)

class Case(object):
    def __init__(self, tag, cmd):
        self.tag= tag
        self.cmd = cmd

    def set_facility(self, facilities, app=None):
        self.cmd.set_facility(facilities, app)

    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)
    
    def accept(self, visitor):
        return self.cmd.accept(visitor)

class UntagCase(Case):pass


class TypeCase(Syntax):
    command_decl = u"""command __type_case :: any -> any
                        refers python:caty.core.script.node.TypeCase;
    """

    def __init__(self, path, via):
        self.__cases = []
        self.__scalar_tag_map = _scalar_tag_map
        Syntax.__init__(self)
        self.path= path
        self.via = via
    
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
        self.__cases.append(case)

    def set_facility(self, facilities, app=None):
        if self.via:
            self.via.set_facility(facilities, app)
        for v in self.__cases:
            v.set_facility(facilities, app)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        if self.via:
            self.via.set_var_storage(storage)
        for v in self.__cases:
            v.set_var_storage(storage)


    def accept(self, visitor):
        return visitor.visit_case(self)

class Branch(object):
    def __init__(self, type, cmd):
        self.type = type
        self.cmd = cmd

    def set_facility(self, facilities, app=None):
        self.cmd.set_facility(facilities, app)

    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)
    
    def accept(self, visitor):
        return self.cmd.accept(visitor)


class Each(Syntax):
    command_decl = u"""command __each-functor-applied<S default univ, T default univ> 
           {"seq":boolean?} :: seq<S> | object  -> [T*]|object
           {"iter":boolean} :: seq<S> -> seq<T>
           {"seq":boolean?, "obj": boolean} :: object -> object
                        refers python:caty.core.script.node.Each;"""
    def __init__(self, cmd, opts_ref):
        Syntax.__init__(self, opts_ref)
        self.cmd = cmd

    def _finish_opts(self):
        Syntax._finish_opts(self)
        o = self.var_storage.opts
        a = o['_ARGV']
        v = a[1:] if a else [u'']
        self._args = v

    def _prepare(self):
        Command._prepare(self)

    def setup(self, opts, *ignore):
        self.__prop = opts['obj'] if 'obj' in opts else None
        self.__iter = opts['iter'] if 'iter' in opts else None

    @property
    def prop(self):
        return self.__prop

    @property
    def iter(self):
        return self.__iter

    def set_facility(self, facilities, app=None):
        self.cmd.set_facility(facilities, app)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        self.cmd.set_var_storage(storage)

    def accept(self, visitor):
        return visitor.visit_each(self)

class Begin(Syntax):
    command_decl = u"""command __begin<S default univ, T default univ> :: S -> T
                        refers python:caty.core.script.node.Begin;"""
    def __init__(self, cmd, opts_ref):
        Syntax.__init__(self, opts_ref)
        self.cmd = cmd

    def _finish_opts(self):
        Syntax._finish_opts(self)
        o = self.var_storage.opts
        a = o['_ARGV']
        v = a[1:] if a else [u'']
        self._args = v

    def _prepare(self):
        Command._prepare(self)

    def set_facility(self, facilities, app=None):
        self.cmd.set_facility(facilities, app)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        self.cmd.set_var_storage(storage)

    def accept(self, visitor):
        return visitor.visit_begin(self)

class Repeat(Syntax):
    command_decl = u"""command __repeat :: void -> never
                        refers python:caty.core.script.node.Repeat;"""

    def set_facility(self, facilities, ignore=None):
        pass

    def accept(self, visitor):
        return visitor.visit_repeat(self)

class Try(Syntax):
    SOFT = 0
    HARD = 1
    SUPERHARD = 2

    command_decl = u"""command __try<S default univ, T default univ> {"wall": ("soft"|"hard"|"superhard")?} :: S -> T
                        refers python:caty.core.script.node.Try;"""

    def __init__(self, pipeline, opts):
        Syntax.__init__(self, opts)
        self.pipeline = pipeline


    def setup(self, opts):
        wall = opts.get(u'wall')
        if wall == u'hard':
            self.wall = self.HARD
        elif wall == u'superhard':
            self.wall = self.SUPERHARD
        else:
            self.wall = self.SOFT

    def set_facility(self, facilities, app=None):
        self.pipeline.set_facility(facilities, app)

    def _prepare(self):
        Command._prepare(self)
    
    def accept(self, visitor):
        return visitor.visit_try(self)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        self.pipeline.set_var_storage(storage)

class Unclose(Syntax):
    command_decl = u"""command __unclose<T default univ> {@[default(false)]"clear": boolean?} :: UncloseInput -> T
                        refers python:caty.core.script.node.Unclose;"""

    def __init__(self, pipeline, opts_ref):
        Syntax.__init__(self, opts_ref)
        self.pipeline = pipeline

    def set_facility(self, facilities, ignore=None):
        pass

    def _prepare(self):
        Command._prepare(self)
    
    def setup(self, opts):
        self.clear = opts['clear']

    def accept(self, visitor):
        return visitor.visit_unclose(self)

    @property
    def out_schema(self):
        return self.pipeline.out_schema

class Catch(Syntax):
    command_decl = u"""command __catche<S default univ, T default univ> :: S -> T
                        refers python:caty.core.script.node.Catch;"""

    def __init__(self, handler):
        Syntax.__init__(self)
        self.handler = handler

    def set_facility(self, facilities, app=None):
        if self.handler:
            for v in self.handler.values():
                v.set_facility(facilities, app)

    def _prepare(self):
        Command._prepare(self)
    
    def accept(self, visitor):
        return visitor.visit_catch(self)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        if self.handler:
            for v in self.handler.values():
                v.set_var_storage(storage)


class Time(Syntax):
    command_decl = u"""
    command __time-functor<T default any> {"verbose": boolean?} :: T -> T
        refers python:caty.core.script.node.Time;
    """
    def __init__(self, cmd, opts):
        Syntax.__init__(self, opts)
        self.cmd = cmd

    def _prepare(self):
        Command._prepare(self)

    def setup(self, opts, *ignore):
        self.verbose = opts.get('verbose', False)

    def set_facility(self, facilities, app=None):
        Syntax.set_facility(self, facilities)
        self.cmd.set_facility(facilities, app)

    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)
        Syntax.set_var_storage(self, storage)

    def accept(self, visitor):
        return visitor.visit_time(self)

class Take(Syntax):
    command_decl = u"""
    command __take-functor<T default any> {"indef": boolean?} :: seq<T> | object -> [T*]
                                        {"indef": boolean?, "iter": boolean} :: seq<T> | object -> seq<T>
                                        {"indef": boolean?, "obj": true} :: object -> object
        refers python:caty.core.script.node.Take;
    """
    def __init__(self, cmd, opts_ref):
        Syntax.__init__(self, opts_ref)
        self.cmd = cmd

    def setup(self, opts, *ignore):
        self.__obj = opts['obj'] if 'obj' in opts else None
        self.__indef = opts['indef'] if 'indef' in opts else None
        self.__iter = opts['iter'] if 'iter' in opts else None

    def _prepare(self):
        Command._prepare(self)

    @property
    def obj(self):
        return self.__obj

    @property
    def indef(self):
        return self.__indef

    @property
    def iter(self):
        return self.__iter

    def set_facility(self, facilities, app=None):
        self.cmd.set_facility(facilities, app)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        self.cmd.set_var_storage(storage)

    def accept(self, visitor):
        return visitor.visit_take(self)

class Start(Syntax):
    command_decl = u"""
    command __start-functor<T default any> :: T -> never
        refers python:caty.core.script.node.Start;
    """
    def __init__(self, cmd, ignore):
        Syntax.__init__(self)
        self.cmd = cmd

    def set_facility(self, facilities, app=None):
        Syntax.set_facility(self, facilities)
        self.cmd.set_facility(facilities, app)

    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)
        Syntax.set_var_storage(self, storage)

    def accept(self, visitor):
        return visitor.visit_start(self)

class PipelineFragment(Syntax):
    command_decl = u"""
    command __pipeline-gragment-functor<S default any, T default any> :: S -> T
        refers python:caty.core.script.node.PipelineFragment;
    """
    def __init__(self, cmd, fragment_name):
        Syntax.__init__(self)
        self.cmd = cmd
        self._name = fragment_name

    def set_facility(self, facilities, app=None):
        self.cmd.set_facility(facilities, app)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        self.cmd.set_var_storage(storage)

    def accept(self, visitor):
        return self.cmd.accept(visitor)

    @property
    def out_schema(self):
        return self.cmd.out_schema

class ActionEnvelope(Syntax):
    command_decl = u"""
    command __action-envelope {*:any} [string*] :: WebInput -> Response | Redirect
        refers python:caty.core.script.node.ActionEnvelope;
    """
    def __init__(self, script, name):
        Syntax.__init__(self)
        self.cmd = script
        self.action_name = name

    def set_facility(self, facilities, app=None):
        self.cmd.set_facility(facilities, app)
        env = facilities['env']
        env._dict['ACTION'] = self.action_name

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        self.cmd.set_var_storage(storage)

    def accept(self, visitor):
        new_storage = VarStorageForAction(self.var_storage)
        self.cmd.set_var_storage(new_storage)
        return self.cmd.accept(visitor)

class JsonPath(Syntax):
    command_decl = u"""
    command __jsonpath<S, T> :: S -> T 
        refers python:caty.core.script.node.JsonPath;
    """
    def __init__(self, stm, pos):
        Syntax.__init__(self, pos=pos)
        self.pos = pos
        self.stm = stm
        self.path = stm.to_str()

    def set_facility(self, facilities, ignore=None):
        pass

    def set_var_storage(self, storage):
        pass

    def accept(self, visitor):
        return visitor.visit_json_path(self)

class VarStorageForAction(VarStorage):
    def __init__(self, storage):
        self.opts = storage.opts
        if len(storage.args) > 1:
            self.args = [storage.args[1]] + storage.args[1:]
            self.opts[u'PATH_INFO'] = self.args[0]
        else:
            self.args = storage.args
        self.opts[u'_ARGV'] = self.args
        self.args_stack = []
        self.opts_stack = []

    def new_masked_scope(self, opts, args):
        from caty.util.collection import OverlayedDict
        self.opts_stack.append(self.opts)
        self.args_stack.append(self.args)
        self.opts = OverlayedDict(opts if opts else {})
        if len(args) >= 1:
            self.args = [args[0]] + args
        else:
            self.args = args
        self.opts[u'_ARGV'] = self.args

class ChoiceBranch(Syntax):
    command_decl = u"""command __choice_branch :: univ -> univ
                        refers python:caty.core.script.node.ChoiceBranch;
    """

    def __init__(self):
        self.__cases = []
        Syntax.__init__(self)
    
    @property
    def cases(self):
        return self.__cases

    def add_case(self, case):
        self.__cases.append(case)

    def set_facility(self, facilities, app=None):
        for v in self.__cases:
            v.set_facility(facilities, app)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        for v in self.__cases:
            v.set_var_storage(storage)


    def accept(self, visitor):
        return visitor.visit_choice_branch(self)

class Empty(Syntax):
    command_decl = u"""command __empty<T default univ> :: T -> T
                        refers python:caty.core.script.node.Empty;
    """
    def __init__(self, *args, **kwds):
        Syntax.__init__(self)

    def accept(self, visitor):
        return visitor.visit_empty(self)

class Break(Syntax):
    command_decl = u"""command __break :: univ -> never
                        refers python:caty.core.script.node.Break;
    """
    def __init__(self, *args, **kwds):
        Syntax.__init__(self)

    def accept(self, visitor):
        return visitor.visit_break(self)

class MethodChain(Syntax):
    command_decl = u"""command __method_chain<T default univ> :: Classed -> T
                        refers python:caty.core.script.node.MethodChain;"""

    def __init__(self, proxy, builder):
        Syntax.__init__(self)
        self.proxy = proxy
        self.builder = builder

    def set_facility(self, facilities, ignore=None):
        self.facilities = facilities

    def set_pipeline(self, pipeline):
        self.pipeline = pipeline
        self.pipeline.set_facility(self.facilities)

    def _prepare(self):
        Command._prepare(self)

    def accept(self, visitor):
        return visitor.visit_method_chain(self)

    @property
    def out_schema(self):
        return self.pipeline.out_schema

class Fetch(Syntax):
    command_decl = u"""command __fetch<T default univ> 
        {
            @[default(false)]
            "auto": boolean?, 
            @[default(false)]
            "no-self": boolean?, 
            @[default(2)]
            "deref-depth": integer(minimum=0)?
        } :: Reference | {"_self": Reference, *:any?} -> T
                        refers python:caty.core.script.node.Fetch;"""

    def __init__(self, queries, opts):
        Syntax.__init__(self, opts)
        self.queries = queries

    def _prepare(self):
        Command._prepare(self)

    def setup(self, opts):
        self.noself = opts['no-self']
        self.deref_depth = opts['deref-depth']
        self.auto = opts['auto']

    def accept(self, visitor):
        return visitor.visit_fetch(self)

class Mutating(Syntax):
    command_decl = u"""command __mutating<S default univ, T default univ> {@[default(false)]"commit": boolean?} :: Mut<S> -> Mut<T>
                        refers python:caty.core.script.node.Mutating;"""

    def __init__(self, pipeline, envname):
        Syntax.__init__(self)
        self.pipeline = pipeline
        self.envname = envname

    def set_facility(self, facilities, ignore=None):
        self.pipeline.set_facility(facilities)

    def set_var_storage(self, storage):
        self.pipeline.set_var_storage(storage)

    def _prepare(self):
        Command._prepare(self)

    def accept(self, visitor):
        return visitor.visit_mutating(self)

class CommitM(Syntax):
    command_decl = u"""command __commitm<S default univ> [string?] :: Mut<S> -> Mut<S>
                        refers python:caty.core.script.node.CommitM;"""

    def __init__(self, args_ref):
        Syntax.__init__(self, [], args_ref)

    def setup(self, name=None):
        self.envname = name

    def _prepare(self):
        Command._prepare(self)

    def accept(self, visitor):
        return visitor.visit_commitm(self)

class Fold(Syntax):
    command_decl = u"""command __fold<S default univ, T default univ, U default univ> :: [[S*], T]-> T
                        refers python:caty.core.script.node.Fold;"""
    def __init__(self, cmd, opts_ref):
        Syntax.__init__(self, opts_ref)
        self.cmd = cmd

    def _prepare(self):
        Command._prepare(self)

    def set_facility(self, facilities, app=None):
        self.cmd.set_facility(facilities, app)

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        self.cmd.set_var_storage(storage)

    def accept(self, visitor):
        return visitor.visit_fold(self)
