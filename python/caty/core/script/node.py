#coding: utf-8
u"""Caty スクリプトノードモジュール。
Caty では switch, dispatch, object 生成などはすべてコマンドとして実装する。
"""

from caty.jsontools.path import build_query
from caty.jsontools import TaggedValue, tag, tagged, untagged, TagOnly
from caty.jsontools import jstypes
from caty.core.command import ScriptError, PipelineInterruption, PipelineErrorExit, Command, Syntax
import caty
import caty.core.schema as schema
import types

schema = ''

class ScalarBuilder(Syntax):
    command_decl = u"""command scalar-builder<T> :: void -> T
                        reads schema
                        refers python:caty.core.script.node.ScalarBuilder;
    """

    def __init__(self):
        Syntax.__init__(self)

    def set_value(self, value):
        if isinstance(value, str):
            v = unicode(value)
        else:
            v = value
        #self.profile.out_schema = jstypes.enum.create({}, [v])
        self.value = v

    def execute(self):
        return self.value

class ListBuilder(Syntax):
    command_decl = u"""command list-builder<T> :: T -> array
                        refers python:caty.core.script.node.ListBuilder;
    """

    def __init__(self):
        Syntax.__init__(self)
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
        #scms = []
        #    scms.append(v.out_schema)
        #self.out_schema.schema_list = scms
   
    def set_var_storage(self, storage):
        for v in self.values:
            v.set_var_storage(storage)

    def execute(self, input):
        r = []
        for v in self.values:
            r.append(v(input))
        return r


class ObjectBuilder(Syntax):
    command_decl = u"""command __object-builder<T> :: T -> object
                        refers python:caty.core.script.node.ObjectBuilder;
    """

    def __init__(self):
        Syntax.__init__(self)
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

    def execute(self, input):
        obj = {}
        for name, node in self.__nodes.iteritems():
            obj[name] = node(input)
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

class VarStore(Syntax):
    command_decl = u"""command __var-store<T> :: T -> T
                        refers python:caty.core.script.node.VarStore;
    """
    def __init__(self, name):
        Syntax.__init__(self)
        self.__var_name = name

    def set_var_storage(self, storage):
        self.__var_storage = storage

    def execute(self, input):
        if self.__var_name not in self.__var_storage.opts:
            self.__var_storage.opts[self.__var_name] = input
            return input
        else:
            raise Exception(u'%s is already defined' % self.__var_name)

class VarRef(Syntax):
    command_decl = u"""command __var-ref<T> :: void -> T
                        refers python:caty.core.script.node.VarRef;
    """
    def __init__(self, name, optional):
        Syntax.__init__(self)
        self.__var_name = name
        self.__optional = optional

    def set_var_storage(self, storage):
        self.__var_storage = storage

    def execute(self):
        if self.__var_name in self.__var_storage.opts:
            r = self.__var_storage.opts[self.__var_name]
            if r is caty.UNDEFINED and not self.__optional:
                raise Exception(u'%s is not defined' % self.__var_name)
            return r
        else:
            if self.__optional:
                return caty.UNDEFINED
            raise Exception(u'%s is not defined' % self.__var_name)

class ArgRef(Syntax):
    command_decl = u"""command __arg-ref<T> :: void -> T
                        refers python:caty.core.script.node.ArgRef;
    """
    def __init__(self, num, optional):
        Syntax.__init__(self)
        self.__arg_num = int(num)
        self.__optional = optional

    def execute(self):
        argv = self._var_storage.opts['_ARGV']
        try:
            return argv[self.__arg_num]
        except:
            if self.__optional:
                return caty.UNDEFINED
            raise

class ConstNode(object):
    def __init__(self, name, value):
        self.name = name
        self.cmd = ScalarBuilder()
        self.cmd.set_value(value)

    def set_facility(self, facilities):
        self.name = self.name if isinstance(self.name, unicode) else unicode(self.name, facilities['env'].read_mode.get('SYSTEM_ENCODING'))
   
    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)

    def __call__(self, input):
        return self.cmd(input)

class CommandNode(object):
    def __init__(self, name, cmd):
        self.name = name
        self.cmd = cmd

    def set_facility(self, facilities):
        self.cmd.set_facility(facilities)
        self.name = self.name if isinstance(self.name, unicode) else unicode(self.name, facilities['env'].read_mode.get('SYSTEM_ENCODING'))

    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)

    def __call__(self, input):
        return self.cmd(input)

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
            caty._Undefined: ['undefined'],
        }
    
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

    def execute(self, input):
        jsobj = input
        target = self.__query.find(jsobj).next()
        if not isinstance(target, TaggedValue) and not (isinstance(target, dict) and '$$tag' in target):
            return self.not_tagged_value_case(target)
        else:
            return self.tagged_value_case(target)

    def tagged_value_case(self, target):
        tag = target.tag if isinstance(target, TaggedValue) else target['$$tag']
        if tag not in self.__cases:
            if '*' in self.__cases:
                tag = '*'
            elif '*!' in self.__cases:
                if tag not in schema.types:
                    tag = '*!'
                else:
                    raise ScriptError(tag)
            else:
                raise ScriptError(tag)
        return self.exec_cmd(tag, target)

    def not_tagged_value_case(self, target):
        tags = self.__scalar_tag_map.get(type(target), None)
        if tags == None:
            raise ScriptError()
        for tag in tags:
            if tag in self.__cases:
                return self.exec_cmd(tag, target)
        if '*' in self.__cases:
            tag = '*'
        elif '*!' in self.__cases:
            for tag in tags:
                if tag not in schema.types:
                    tag = '*!'
                    break
            else:
                raise ScriptError(tag)
        else:
            raise ScriptError(tag)
        return self.exec_cmd(tag, target)
    
    def exec_cmd(self, tag, jsobj):
        childcmd = self.__cases[tag].cmd
        if childcmd.in_schema != jstypes.never:
            if isinstance(self.__cases[tag], UntagCase):
                input = untagged(jsobj)
            else:
                input = jsobj
        return childcmd(input)

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

    def execute(self, input):
        return tagged(self.tag, self.command(input))

class UnaryTagBuilder(Syntax):
    command_decl = u"""command __unary-tag :: any -> any
                        refers python:caty.core.script.node.UnaryTagBuilder;
    """
    def __init__(self, tag):
        Syntax.__init__(self)
        self.tag = tag
    
    def set_facility(self, facilities):
        pass

    def execute(self, input):
        return TagOnly(self.tag)


class Case(object):
    def __init__(self, tag, cmd):
        self.tag= tag
        self.cmd = cmd

    def set_facility(self, facilities):
        self.cmd.set_facility(facilities)

    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)
    

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
        self._args = self._var_storage.opts['_ARGV'][1:]

    def _prepare(self):
        Command._prepare(self)

    def setup(self, opts, *ignore):
        self.__prop = opts['prop'] if 'prop' in opts else None

    def set_facility(self, facilities):
        self.cmd.set_facility(facilities)
        #ils = facilities['schema']['array']
        #ils.schemata = [self.cmd.in_schema]
        #ils.repeat = True
        #ols = facilities['schema']['array']
        #ols.schemata = [self.cmd.out_schema]
        #ols.repeat = True
        #self.profile.declobj.profiles = [(ils, ols)]

    def set_var_storage(self, storage):
        Syntax.set_var_storage(self, storage)
        self.cmd.set_var_storage(storage)

    def execute(self, input):
        if self.__prop:
            return self._iter_obj(input)
        else:
            return self._iter_array(input)

    def _iter_array(self, input):
        r = []
        for v in input:
            try:
                self._var_storage.new_scope()
                r.append(self.cmd(v))
            finally:
                self._var_storage.del_scope()
        return r

    def _iter_obj(self, input):
        r = self._iter_array(list(input.items()))
        return dict(r)

from caty.util import error_to_ustr
class Capture(Syntax):
    command_decl = u"""@[test] command captured-pipeline<S, T, U> :: S -> @OK T | @Err U
                            reads env
                        refers python:caty.core.script.node.Capture;"""
    def __init__(self, cmd):
        Syntax.__init__(self)
        self.cmd = cmd

    def set_facility(self, facilities):
        Syntax.set_facility(self, facilities)
        self.cmd.set_facility(facilities)

    def set_var_storage(self, storage):
        self.cmd.set_var_storage(storage)

    def execute(self, input):
        try:
            return tagged(u'OK', self.cmd(input))
        except (PipelineErrorExit, PipelineInterruption), e:
            return tagged(u'Err', e.json_obj)
        except Exception, e:
            return tagged(u'Err', error_to_ustr(e))
    

class TypeInfo(Syntax):
    command_decl = u"""@[console] command type-info :: void -> string
                        reads schema
                        refers python:caty.core.script.node.TypeInfo;"""

    def __init__(self, cmd):
        Syntax.__init__(self)
        self.cmd = cmd

    def set_facility(self, facilities):
        Syntax.set_facility(self, facilities)
        self.cmd.set_facility(facilities)

    def execute(self):
        return unicode('%s -> %s' % (self.cmd.profile.in_schema.canonical_name, self.cmd.profile.out_schema.canonical_name))

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

    def execute(self, input):
        import time
        s = time.time()
        r = self.cmd(input)
        e = time.time()
        print e - s, '[sec]'
        return r

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

    def execute(self, input):
        r = []
        for v in input:
            try:
                self._var_storage.new_scope()
                x = self.cmd(v)
                if x == True or tag(x) == 'True':
                    r.append(v)
            finally:
                self._var_storage.del_scope()
        return r

