##coding:utf-8
from __future__ import with_statement
from decimal import Decimal
from topdown import *
from caty.core.command import *
from caty.core.script.proxy import CommandProxy
from caty.core.script.proxy import ScalarProxy as ScalarBuilder
from caty.core.script.proxy import ListProxy as ListBuilder
from caty.core.script.proxy import ObjectProxy as ObjectBuilder
from caty.core.script.proxy import ConstNodeProxy as ConstNode
from caty.core.script.proxy import CommandNodeProxy as CommandNode
from caty.core.script.proxy import DispatchProxy as Dispatch
from caty.core.script.proxy import TagProxy as TagBuilder
from caty.core.script.proxy import UnaryTagProxy as UnaryTagBuilder
from caty.core.script.proxy import CaseProxy as Case
from caty.core.script.proxy import UntagCaseProxy as UntagCase
from caty.core.script.proxy import EachProxy as Each
from caty.core.script.proxy import TimeProxy as Time
from caty.core.script.proxy import CaptureProxy as Capture
from caty.core.script.proxy import TypeInfoProxy as TypeInfo
from caty.core.script.proxy import DiscardProxy as Discard
from caty.core.script.proxy import VarStoreProxy as VarStore
from caty.core.script.proxy import VarRefProxy as VarRef
from caty.core.script.proxy import ArgRefProxy as ArgRef
from caty.core.script.proxy import combine_proxy
from caty.util import bind2nd
import caty.jsontools.xjson as xjson
from caty.core.exception import SubCatyException
from caty.core.command.param import *

class NothingTodo(Exception):
    u"""コメントのみの入力など、何もしないときのシグナル
    """
    def __init__(self):
        pass

class HashNotationFound(Exception):
    pass

class ScriptParser(Parser):
    def __init__(self, facilities=None):
        pass
        #self.mafs = facilities['pub'].read_mode
        #scripts = facilities.get('scripts', None)
        #if scripts:
        #    self.scripts = scripts
        #self.facilities = facilities

    def parse(self, text):
        if not text:
            return None
        seq = CharSeq(text, hook=xjson.remove_comment, auto_remove_ws=True)
        try:
            self._script = self.make_pipeline(seq)
            if not seq.eof:
                raise ParseFailed(seq, self.make_pipeline)
        except EndOfBuffer, e:
            return None
        return self._script

    def __call__(self, seq):
        return self.make_pipeline(seq)

    def value(self, cs):
        v = cs.parse([xjson.string, 
                      xjson.multiline_string,
                      bind2nd(xjson.null, True), 
                      bind2nd(xjson.number, True), 
                      bind2nd(xjson.integer, True), 
                      bind2nd(xjson.boolean, True),
                      ])
        s = ScalarBuilder()
        s.set_value(v)
        return s

    def name(self, seq):
        return seq.parse(Regex(r'[a-zA-Z]+[-a-zA-Z0-9:._]*'))

    def functor(self, seq):
        func = seq.parse(['each', 'capture', 'type-info', 'time'])
        opts = self.options(seq)
        seq.parse('{')
        cmd  = self.make_pipeline(seq)
        seq.parse('}')
        if func == 'each':
            return Each(cmd, opts)  
        elif func == 'type-info':
            return TypeInfo(cmd, opts)
        elif func == 'time':
            return Time(cmd, opts)
        else:
            return Capture(cmd, opts)

    def command(self, seq):
        name = self.name(seq)
        type_args = option(self.type_args, [])(seq)
        opts = self.options(seq)
        args = self.arguments(seq)
        return CommandProxy(name, type_args, opts, args)

    def type_args(self, seq):
        seq.parse('<')
        types = split(self.name, ',', allow_last_delim=False)(seq)
        seq.parse('>')
        return types

    def arguments(self, seq):
        args = filter(lambda a: a is not None, seq.parse(many(self.arg)))
        return args

    def options(self, seq):
        opts = filter(lambda o: o != (None, None), seq.parse(many(self.opt)))
        return opts

    def pipe(self, seq):
        _ = seq.parse(['|','>@', '>:', '>', ';'])
        if _ == '>:':
            raise ParseFailed(seq, self.pipe)
        return _

    def pipeline(self, seq):
        r = []
        seq.parse(self.do_nothing)
        if seq.eof:
            raise NothingTodo()
        r.append(seq.parse([self.term, self.group]))
        while True:
            a = option(try_(self.pipe), None)(seq)
            if not a:
                break
            if a == '|':
                r.append(seq.parse([self.term, self.group]))
            elif a == '>@':
                t = self.tag_name(seq)
                exp = r.pop(-1)
                r.append(TagBuilder(t, exp))
            elif a == ';':
                nex = seq.parse([self.term, self.group])
                r.append(Discard(nex))
            elif a == '>':
                n = seq.parse(self.name)
                r.append(VarStore(n))
        return combine_proxy(r)

    def group(self, seq):
        _ = seq.parse('(')
        r = self.pipeline(seq)
        _ = seq.parse(')')
        return r

    def make_pipeline(self, seq):
        return seq.parse([self.pipeline])

    def term(self, seq):
        parsers = map(try_, [
                    self.functor,
                    self.tag,
                    self.cond,
                    self.object, 
                    self.diagram_order, 
                    self.value, 
                    self.script,
                    self.command,
                    self.list, 
                    self.var_ref,
                    self.arg_ref,
                    self.hash,
                    ])
        return seq.parse(parsers)

    def tag(self, seq):
        _ = seq.parse('@')
        n = self.tag_name(seq)
        delim = True if seq.eof else seq.peek(option([',', ']', '}'], False))
        if delim:
            return UnaryTagBuilder(n)
        r = seq.parse([self.term, self.group])
        return TagBuilder(n, r)
    
    def var_ref(self, seq):
        seq.parse('%')
        n = seq.parse(self.var_name)
        o = seq.parse(option('?'))
        return VarRef(n, bool(o))

    def var_name(self, seq):
        return seq.parse(Regex(r'[a-zA-Z_]+[-a-zA-Z0-9_]*'))

    def arg_ref(self, seq):
        seq.parse('%')
        n = seq.parse(Regex(r'[0-9]+'))
        o = seq.parse(option('?'))
        return ArgRef(n, bool(o))
    
    def tag_name(self, seq):
        return seq.parse(['*!', '*', xjson.string, self.name, Regex(r'[-0-9a-zA-Z_]+')])

    def unquoted(self, seq):
        return seq.parse(Regex(r'[^;\t\r\n <>|%+"(){},\[\]]+'))

    def opt(self, seq):
        seq.ignore_hook = True
        try:
            o = seq.parse([self.shortopt, self.longopt, self.parameter_opt])
            skip_ws(seq)
            return o
        finally:
            seq.ignore_hook = False

    def script(self, seq):
        path = seq.parse(Regex(r'[^\t\r\n <>|+"(){},.\[\]]+\.(caty|cgi)'))
        if not path.startswith('/'):
            path = 'scripts@this:/' + path
        s = [Argument(path)]
        opts = self.options(seq)
        args = self.arguments(seq)
        if not args:
            args = []
        p = CommandProxy(u'exec', [], {}, s + args)
        return p

    def shortopt(self, seq):
        o = seq.parse(Regex(r'-[a-zA-Z]'))
        try:
            v = seq.parse([xjson.number, xjson.integer, self.unquoted, xjson.string])
            return Option(o, v)
        except:
            return Option(o, None)

    def longopt(self, seq):
        o = seq.parse(Regex(r'--[a-zA-Z]+[-a-zA-Z0-9_]*'))
        try:
            seq.parse('=')
            v = seq.parse([xjson.number, xjson.integer, self.unquoted, xjson.string, self.named_arg, self.indexed_arg])
            if v is None: return (None, None)
            return Option(o, v)
        except:
            return Option(o, None)

    def parameter_opt(self, seq):
        name = seq.parse(Regex(r'%--[a-zA-Z]+[-a-zA-Z0-9_]*\??'))[3:]
        optional = False
        if name.endswith('?'):
            name = name[:-1]
            optional = True
        return OptionLoader(name, optional)
    
    def named_arg(self, seq):
        name = seq.parse(Regex(r'%[a-zA-Z]+[-a-zA-Z0-9_]*\??'))[1:]
        optional = False
        if name.endswith('?'):
            name = name[:-1]
            optional = True
        return NamedArg(name, optional)

    def arg(self, seq):
        r = seq.parse([xjson.number, xjson.integer, xjson.boolean, self.unquoted, xjson.string, self.named_arg, self.indexed_arg])
        return Argument(r) if not isinstance(r, Param) else r

    def indexed_arg(self, seq):
        index = seq.parse(Regex(r'%[0-9]+\??'))[1:]
        optional = False
        if index.endswith('?'):
            index = int(index[:-1])
            optional = True
        else:
            index = int(index)
        return IndexArg(index, optional)

    def comma(self, seq):
        _ = seq.parse(',')
        return _

    def list(self, seq):
        from itertools import dropwhile
        seq.parse('[')
        values = seq.parse(split(self.listitem, self.comma, True))
        actual = list(reversed(list(dropwhile(lambda x: isinstance(x, CommandProxy) and x.name == 'undefined', reversed(values)))))
        seq.parse(']')
        l = ListBuilder()
        l.set_values(anything(actual))
        return l

    def listitem(self, seq):
        if seq.current == ']': return CommandProxy('undefined', [], {}, [])
        try:
            return seq.parse([self.make_pipeline, self.loose_item])
        except NothingTodo:
            raise ParseFailed(seq, self.listitem)

    def loose_item(self, seq):
        if not seq.peek(self.comma):
            raise ParseFailed(seq, self.listitem)
        return CommandProxy('undefined', [], {}, [])

    def object(self, seq):
        seq.parse('{')
        items = seq.parse(split(self.item, self.comma, True))
        seq.parse('}')
        o = ObjectBuilder()
        for i in anything(items):
            o.add_node(i)
        return o

    def item(self, seq):
        if seq.current == '}': return
        n = xjson.string(seq)
        if not seq.parse(option(':')):
            if seq.eof:
                raise EndOfBuffer(seq, self.item)
            else:
                raise ParseError(seq, self.item)
        try:
            v = self.make_pipeline(seq)
        except NothingTodo:
            raise ParseFailed(seq, self.item)
        return CommandNode(n, v)

    def diagram_order(self, seq):
        seq.parse('do')
        seq.parse('{')
        items = seq.parse(split(self.item_do, self.comma))
        seq.parse('}')
        o = ObjectBuilder()
        for i in anything(items):
            o.add_node(i)
        return o

    def item_do(self, seq):
        if seq.current == '}': return
        try:
            v = self.make_pipeline(seq)
        except NothingTodo:
            raise ParseFailed(seq, self.item)
        seq.parse('>:')
        n = xjson.string(seq)
        return CommandNode(n, v)

    def cond(self, seq):
        seq.parse('when')
        opts = self.options(seq)
        seq.parse('{')
        name_set = set()
        cases = seq.parse(split(lambda s:self.case(s, name_set), self.comma, allow_last_delim=True))
        seq.parse('}')
        d = Dispatch(opts)
        for c in anything(cases):
            d.add_case(c)
        return d

    def case(self, seq, name_set):
        t = seq.parse(self.tag_name)
        if t in name_set:
            raise ParseFailed(seq, self.case, t)
        name_set.add(t)
        tp = seq.parse(['==>', '=>'])
        try:
            v = self.make_pipeline(seq)
        except NothingTodo:
            raise ParseFailed(seq, self.case)
        return Case(t, v) if tp == '==>' else UntagCase(t, v)

    def remove_comment(self, seq):
        seq.parse(self.singleline_comment)
        seq.parse(self.multiline_comment)
        seq.parse(skip_ws)

    def singleline_comment(self, seq):
        if seq.parse(option('//', None)) == None: return
        seq.parse([until('\n'), until('\r')])

    def multiline_comment(self, seq):
        if seq.parse(option('/*', None)) == None: return
        seq.parse(until('*/'))
        seq.parse('*/')

    def do_nothing(self, seq):
        u"""コメント行のみ入力された場合用のダミー
        """
        pass

    def hash(self, seq):
        seq.parse('#')
        delim = seq.parse(['<', "'"])
        if delim == "'":
            seq.parse('undefined')
            raise HashNotationFound('undefined')
        name = seq.parse(Regex(r'[a-zA-Z_]+[a-zA-Z0-9_-]*'))
        parsers = map(try_, [
                    self.functor,
                    self.tag,
                    self.cond,
                    self.object, 
                    self.diagram_order, 
                    self.value, 
                    self.script,
                    self.command,
                    self.list, 
                    ])
        obj = seq.parse(option(parsers))
        seq.parse('>')
        raise HashNotationFound(name)

def anything(l):
    return filter(lambda i: i!= None, l)


