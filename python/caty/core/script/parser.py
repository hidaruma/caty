##coding:utf-8
from __future__ import with_statement
from decimal import Decimal
from topdown import *
from caty.core.command import *
from caty.core.script.proxy import CommandProxy
from caty.core.script.proxy import ScalarProxy as ScalarBuilder
from caty.core.script.proxy import ListProxy as ListBuilder
from caty.core.script.proxy import ParallelListProxy as ParallelListBuilder
from caty.core.script.proxy import ObjectProxy as ObjectBuilder
from caty.core.script.proxy import ParallelObjectProxy as ParallelObjectBuilder
from caty.core.script.proxy import ConstNodeProxy as ConstNode
from caty.core.script.proxy import CommandNodeProxy as CommandNode
from caty.core.script.proxy import DispatchProxy as Dispatch
from caty.core.script.proxy import TagProxy as TagBuilder
from caty.core.script.proxy import ParTagProxy as ParTagBuilder
from caty.core.script.proxy import UnaryTagProxy as UnaryTagBuilder
from caty.core.script.proxy import CaseProxy as Case
from caty.core.script.proxy import UntagCaseProxy as UntagCase
from caty.core.script.proxy import EachProxy as Each
from caty.core.script.proxy import TimeProxy as Time
from caty.core.script.proxy import TakeProxy as Take
from caty.core.script.proxy import StartProxy as Start
from caty.core.script.proxy import BeginProxy as Begin
from caty.core.script.proxy import RepeatProxy as Repeat
from caty.core.script.proxy import DiscardProxy as Discard
from caty.core.script.proxy import VarStoreProxy as VarStore
from caty.core.script.proxy import VarRefProxy as VarRef
from caty.core.script.proxy import ArgRefProxy as ArgRef
from caty.core.script.proxy import FragmentProxy as PipelineFragment
from caty.core.script.proxy import TypeCaseProxy as TypeCase
from caty.core.script.proxy import TypeCondProxy as TypeCond
from caty.core.script.proxy import BranchProxy as Branch
from caty.core.script.proxy import JsonPathProxy as JsonPath
from caty.core.script.proxy import TryProxy as Try
from caty.core.script.proxy import CatchProxy as Catch
from caty.core.script.proxy import UncloseProxy as Unclose
from caty.core.script.proxy import ChoiceBranchProxy as ChoiceBranch
from caty.core.script.proxy import ChoiceBranchItemProxy as ChoiceBranchItem
from caty.core.script.proxy import BreakProxy as Break
from caty.core.script.proxy import EmptyProxy as Empty
from caty.core.script.proxy import MethodChainProxy as MethodChain
from caty.core.script.proxy import FetchProxy as Fetch
from caty.core.script.proxy import MutatingProxy as Mutating
from caty.core.script.proxy import CommitMProxy as CommitM
from caty.core.script.proxy import FoldProxy as Fold
from caty.core.script.proxy import ClassProxy
from caty.core.script.query import *
from caty.core.script.proxy import combine_proxy
from caty.util import bind2nd, try_parse
from caty.util.dev import debug
import caty.jsontools.xjson as xjson
from caty.core.exception import SubCatyException
from caty.core.command.param import *
from caty.core.language.util import fragment_name, identifier_token_a, name_token, class_identifier_token_a
from caty.jsontools.selector.parser import JSONPathSelectorParser
import caty

def method_chain(seq):
    S('.')(seq)
    S('{')(seq)
    return '.{'

_OPERATORS = ['>@', '>:', '>', ';', '||', '|&', '|>', '|=', '|', ';;', method_chain]

class NothingTodo(Exception):
    u"""コメントのみの入力など、何もしないときのシグナル
    """
    def __init__(self):
        pass

class HashNotationFound(Exception):
    pass

class ScriptParser(Parser):
    DEFAULT = 0
    BEGIN_REPEAT = 1
    EACH = 2

    def __init__(self, facilities=None):
        self._context = [self.DEFAULT]
        self.continue_to_parse = True

    def parse(self, text):
        if not text:
            return None
        seq = CharSeq(text, hook=xjson.remove_comment, auto_remove_ws=True)
        try:
            self._script = self.make_pipeline(seq)
            if not seq.eof:
                raise ParseFailed(seq, self.make_pipeline)
        except (ContinuedComment, EndOfBuffer) as e:
            return None
        return self._script

    def __call__(self, seq):
        return self.make_pipeline(seq)

    def value(self, cs):
        v = cs.parse([xjson.string, 
                      xjson.binary,
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
        return identifier_token_a(seq)

    def exception_handle(self, seq):
        keyword(u'try')(seq)
        opts = self.options(seq)
        with strict():
            S(u'{')(seq)
            pipeline = self.make_pipeline(seq)
            S(u'}')(seq)
            return Try(pipeline, opts)

    def catch(self, seq):
        r = {}
        keyword(u'catch')(seq)
        S(u'{')(seq)
        handlers = split(self._handler, u',')(seq)
        for t, cmd in handlers:
            if not cmd:
                continue
            if t in r:
                raise ParseError(seq, u'duplicated exception handler: %s' % t)
            r[t] = cmd
        S(u'}')(seq)
        return Catch(r)

    def _handler(self, seq):
        t = option(choice(u'normal', u'except', u'signal', u'*'))(seq)
        if not t:
            return None, None
        S(u'=>')(seq)
        cmd = self.make_pipeline(seq)
        return t, cmd

    def fetch(self, seq):
        keyword(u'fetch')(seq)
        opts = self.options(seq)
        return Fetch(self.query_value(seq), opts)

    def query_item(self, seq, label_list=frozenset()):
        n = choice(S(u'*'), xjson.string)(seq)
        if not seq.parse(option(':')):
            if seq.eof:
                raise EndOfBuffer(seq, self.query)
            else:
                raise ParseError(seq, self.query)
        return (n, self.query_value(seq, label_list))

    def query_value(self, seq, label_list=frozenset()):
        if option(S(u'@='))(seq):
            label = name_token(seq)
            if label in label_list:
                raise ParseError(seq, u'Label is already defined: %s' % label)
        else:
            label = None
        if not label_list:
            label_list = set([label])
        else:
            label_list.add(label)
        v = option(choice(u'&', u'!', name_token))(seq)
        if v and v not in (u'any', u'_', u'&', u'!') and v not in label_list:
            raise ParseError(seq, u'Undefined label: %s' % v)
        if not v:
            r = choice(#xjson.string, 
                          #xjson.binary,
                          #xjson.multiline_string,
                          #bind2nd(xjson.null, True), 
                          #bind2nd(xjson.number, True), 
                          #bind2nd(xjson.integer, True), 
                          #bind2nd(xjson.boolean, True),
                          try_(bind2nd(self.obj_query, label_list)),
                          try_(bind2nd(self.array_query, label_list)),
                          try_(bind2nd(self.tag_query, label_list)),
                          )(seq)
            r.label = label
        elif v == u'&':
            r = AddressQuery()
        elif v == u'!':
            r = ReferenceQuery()
        else:
            r = TypeQuery(label, v)
        r.optional = option(S(u'?'))(seq)
        return r

    def repeat_item(self, seq, label_list):
        r = self.query_value(seq, label_list)
        r.repeat = option(S(u'*'))(seq)
        if r.optional:
            raise ParseError(seq, u'*')
        return r

    def obj_query(self, seq, label_list=frozenset()):
        S(u'{')(seq)
        queries = seq.parse(split(bind2nd(self.query_item, label_list), self.comma, True))
        S(u'}')(seq)
        q = {}
        w = None
        for k, v in queries:
            if k == '*':
                if not w:
                    w = v
                else:
                    raise ParseError(seq, u'Duplicated wildcard')
            else:
                q[k] = v
        return ObjectQuery(q, w)

    def array_query(self, seq, label_list=frozenset()):
        S(u'[')(seq)
        queries = seq.parse(split(bind2nd(self.repeat_item, label_list), self.comma, True))
        S(u']')(seq)
        q = []
        r = None
        for v in queries:
            if v.repeat:
                if not r:
                    r = v
                else:
                    raise ParseError(seq, u'*')
            else:
                if r:
                    raise ParseError(seq, u'*')
                else:
                    q.append(v)
        return ArrayQuery(q, r)

    def tag_query(self, seq, label_list=frozenset()):
        _ = seq.parse('@')
        n = self.tag_name(seq)
        return TagQuery(n, self.query_value(seq, label_list))

    def mutating(self, seq):
        keyword(u'mutating')(seq)
        name = self.name(seq)
        S(u'{')(seq)
        p = self.pipeline(seq)
        S(u'}')(seq)
        return Mutating(p, name)

    def functor(self, seq):
        import string as str_mod
        k = lambda s: keyword(s, str_mod.ascii_letters + '_.')
        func = seq.parse([k(u'each'), k(u'take'), k(u'time'), k(u'start'), k(u'begin'), k(u'unclose'), k(u'fold')])
        try:
            if func in ('unclose', 'each', 'take'):
                opts = self.options(seq)
            else:
                opts = ()
            seq.parse(u'{')
            if seq.eof:
                raise EndOfBuffer(seq, self.functor)
            if func == 'begin':
                self._context.append(self.BEGIN_REPEAT)
            elif func == 'each':
                self._context.append(self.EACH)
            else:
                self._context.append(self._context[-1])
            try:
                cmd = self.make_pipeline(seq)
            finally:
                self._context.pop(-1)
            seq.parse(u'}')
            if func == u'each':
                return Each(cmd, opts)
            elif func == u'time':
                return Time(cmd, opts)
            elif func == u'take':
                return Take(cmd, opts)
            elif func == u'start':
                return Start(cmd, opts)
            elif func == u'begin':
                return Begin(cmd, opts)
            elif func == u'unclose':
                return Unclose(cmd, opts)
            elif func == u'fold':
                return Fold(cmd, opts)
        except ParseFailed as e:
            raise ParseError(e.cs, self.functor)

    def command(self, seq, no_opt=False):
        if option(peek('$'))(seq):
            return self.xjson_path(seq)
        name = choice(class_identifier_token_a, identifier_token_a)(seq)
        if name == u'commitm':
            return CommitM(self.arguments(seq))
        elif '.' in name:
            pos = (seq.col-len(name), seq.line)
            name, mname = name.split('.', 1)
            type_args2 = option(self.type_args, [])(seq)
            if not no_opt:
                opts = self.options(seq)
                args = self.arguments(seq)
            else:
                opts = []
                args = []
            return ClassProxy(name, [], CommandProxy(mname, type_args2, opts, args, pos))
        pos = (seq.col-len(name), seq.line)
        type_args = option(nohook(self.type_args), [])(seq)
        if option(nohook(peek(u'.')))(seq) and type_args:
            nohook(S('.'))(seq)
            mname = nohook(name_token)(seq)
            type_args2 = option(self.type_args, [])(seq)
            if not no_opt:
                opts = self.options(seq)
                args = self.arguments(seq)
            else:
                opts = []
                args = []
            return ClassProxy(name, type_args, CommandProxy(mname, type_args2, opts, args, pos))
        else:
            if not no_opt:
                opts = self.options(seq)
                args = self.arguments(seq)
            else:
                opts = []
                args = []
        return CommandProxy(name, type_args, opts, args, pos)

    def call_forward(self, seq):
        name = choice(keyword(u'call'), keyword(u'forward'))(seq)
        pos = (seq.col-len(name), seq.line)
        call_opts = self.options(seq)
        type_args = option(self.type_args, [])(seq)
        cmd = choice(self.named_arg, self.unquoted_maybe_num)(seq)
        if not isinstance(cmd, (NamedArg, unicode)):
            raise ParseError(seq, self.call_forward)
        if isinstance(cmd, unicode):
            cmd = Argument(cmd)
        opts = self.options(seq)
        args = [cmd] + self.arguments(seq)
        return CommandProxy(name, type_args, call_opts, opts + args, pos)


    def xjson_path(self, seq):
        pos = (seq.col-1, seq.line)
        stm = JSONPathSelectorParser(False, True)(seq)
        return JsonPath(stm, pos)

    def type_args(self, seq):
        from caty.core.casm.language.schemaparser import type_var
        return type_var(seq)

    def arguments(self, seq):
        args = filter(lambda a: a is not None, seq.parse(many(try_(self.arg))))
        return args

    def options(self, seq):
        opts = filter(lambda o: o != (None, None), seq.parse(many(self.opt)))
        return opts

    def pipe(self, seq):
        _ = seq.parse(_OPERATORS)
        if _ == '>:':
            raise ParseFailed(seq, self.pipe)
        return _

    def pipeline(self, seq):
        r = []
        seq.parse(self.do_nothing)
        if seq.eof:
            raise NothingTodo()
        r.append(seq.parse([self.term, self.group]))
        while self.continue_to_parse:
            a = option(try_(self.pipe), None)(seq)
            if not a:
                break
            if a == '|':
                r.append(seq.parse([self.term, self.group]))
            elif a == '>@':
                if option(S(u'('))(seq):
                    t = self.pipeline(seq)
                    S(u')')(seq)
                else:
                    t = self.tag_name(seq)
                exp = r.pop(-1)
                r.append(TagBuilder(t, exp))
            elif a == ';':
                nex = seq.parse([self.term, self.group])
                r.append(Discard(nex))
            elif a == '>':
                n = seq.parse(self.name)
                r.append(VarStore(n))
            elif a == '.{':
                pipe = self.make_pipeline(seq)
                S('}')(seq)
                r.append(MethodChain(pipe))
            else:
                raise ParseFailed(seq, '`%s` is reserved token' % a)
        return combine_proxy(r)

    def group(self, seq):
        _ = seq.parse('(')
        r = self.pipeline(seq)
        _ = seq.parse(')')
        return r

    def named_block(self, seq):
        o = choice(S(u'{'), S(u'('))(seq)
        fragment = fragment_name(seq)
        p = self.make_pipeline(seq)
        if o == '{':
            S(u'}')(seq)
        else:
            S(u')')(seq)
        return PipelineFragment(p, fragment)

    def make_pipeline(self, seq):
        return self.pipeline(seq)

    def term(self, seq):
        parsers = map(try_, [
                    self.empty,
                    self.exception_handle,
                    self.catch,
                    self.fetch,
                    self.mutating,
                    self.functor,
                    self.tag,
                    self.choice_branch,
                    self.type_case,
                    self.type_cond,
                    self.cond,
                    self.object, 
                    self.diagram_order, 
                    self.value, 
                    self.call_forward,
                    self.repeat,
                    self.break_,
                    self.command,
                    self.list, 
                    self.par_list, 
                    self.par_obj, 
                    self.par_tag, 
                    self.var_ref,
                    self.arg_ref,
                    self.named_block,
                    self.hash,
                    ])
        return seq.parse(parsers)

    def tag(self, seq):
        _ = seq.parse('@')
        if option(S(u'('))(seq):
            t = self.pipeline(seq)
            S(u')')(seq)
        else:
            t = self.tag_name(seq)
        delim = True if seq.eof else seq.peek(option([',', ']', '}', ';', '|'], False))
        if delim:
            return UnaryTagBuilder(t)
        p = seq.parse([self.term, self.group])
        return TagBuilder(t, p)

    def par_tag(self, seq):
        _ = seq.parse('=@')
        S(u'(')(seq)
        t = self.pipeline(seq)
        S(u')')(seq)
        p = seq.parse([self.term, self.group])
        return ParTagBuilder(t, p)

    def var_ref(self, seq):
        seq.parse('%')
        n = name_token(seq)
        o = seq.parse(option('?'))
        if o and option('=')(seq):
            d = seq.parse([xjson.string, 
                      xjson.binary,
                      xjson.multiline_string,
                      bind2nd(xjson.null, True), 
                      bind2nd(xjson.number, True), 
                      bind2nd(xjson.integer, True), 
                      bind2nd(xjson.boolean, True),
                      ])
        else:
            d = caty.UNDEFINED
        return VarRef(n, bool(o), d)

    def var_name(self, seq):
        return seq.parse(Regex(ur'[a-zA-Z_]+[-a-zA-Z0-9_]*'))

    def arg_ref(self, seq):
        seq.parse('%')
        n = seq.parse(Regex(ur'[0-9]+'))
        o = seq.parse(option('?'))
        if o and option('=')(seq):
            d = seq.parse([xjson.string, 
                      xjson.binary,
                      xjson.multiline_string,
                      bind2nd(xjson.null, True), 
                      bind2nd(xjson.number, True), 
                      bind2nd(xjson.integer, True), 
                      bind2nd(xjson.boolean, True),
                      ])
        else:
            d = caty.UNDEFINED
        return ArgRef(n, bool(o), d)
    
    def tag_name(self, seq):
        return seq.parse([u'*!', u'*', xjson.string, self.name, Regex(ur'[-0-9a-zA-Z_]+')])

    def unquoted(self, seq):
        #v = seq.parse(Regex('([^;\\t\\r\\n <>|%+"(){},\\[\\]]|(?!\\\'\\\'\\\'))([^;\\t\\r\\n <>|%+"(){},\\[\\]]|\\(\\)|(?!\\\'\\\'\\\'))*'))
        delim = list(u';\t\r\n <>|%+"(){},[]') + [u"'''"] + ['//'] + ['/*']
        v = until(delim)(seq)
        if not v:
            raise ParseFailed(seq, self.unquoted)
        if u'/*' in v:
            v, _ = v.split('/*', 1)
            until('*/')(seq)
            if seq.eof:
                raise ContinuedComment()
            S('*/')(seq)
        elif '//' in v:
            v, _ = v.split('//', 1)
            until('\n')(seq)
        return v

    def opt(self, seq):
        seq.ignore_hook = True
        try:
            o = seq.parse(map(try_, [self.longopt, self.parameter_opt, self.arg0]))
            skip_ws(seq)
            return o
        finally:
            seq.ignore_hook = False

    def __make_exec_script(self, path, seq):
        pos = (seq.col, seq.line)
        s = [Argument(path)]
        opts = self.options(seq)
        args = self.arguments(seq)
        if not args:
            args = []
        p = CommandProxy(u'call', [], opts, s + args, pos)
        return p

    def longopt(self, seq):
        o = seq.parse(Regex(ur'--[a-zA-Z]+[-a-zA-Z0-9_]*'))
        try:
            seq.parse('=')
        except:
            return Option(o, True)
        v = choice(
                  bind2nd(xjson.null, True), 
                  bind2nd(xjson.boolean, True),
                  xjson.string, 
                  xjson.multiline_string,
                  self.unquoted_maybe_num, 
                  self._undefined_literal,
                  try_(self.var_ref),
                  self.arg_ref,
                  )(seq)
        if isinstance(v, VarRef):
            return OptionVarLoader(o, v, v.optional, v.default)
        if isinstance(v, ArgRef):
            return ArgVarLoader(o, v, v.optional)
        return Option(o, v)

    def _undefined_literal(self, seq):
        S(u'%?')(seq)
        return caty.UNDEFINED

    def arg0(self, seq):
        o = seq.parse(Regex(ur'--0'))
        try:
            seq.parse('=')
            v = choice(
                      bind2nd(xjson.null, True), 
                      bind2nd(xjson.boolean, True),
                      xjson.string, 
                      xjson.multiline_string,
                      self.unquoted_maybe_num, 
                      self.var_ref
                      )(seq)
            if isinstance(v, VarRef):
                return OptionVarLoader(o, v, v.optional, v.default)
            return Option(o, v)
        except:
            return Option(o, True)

    def unquoted_maybe_num(self, seq):
        v = self.unquoted(seq)
        v = try_parse(int, v, try_parse(Decimal, v, v))
        return v

    def parameter_opt(self, seq):
        from caty.core.language import _name_token_ptn
        if option(S(u'%--*'))(seq):
            return GlobOption()
        name = seq.parse(Regex(r'%%--%s\??' % _name_token_ptn, re.X))[3:]
        optional = False
        if name.endswith('?'):
            name = name[:-1]
            optional = True
        return OptionLoader(name, optional)
    
    def named_arg(self, seq):
        from caty.core.language import _name_token_ptn
        if option(S(u'%#'))(seq):
            return GlobArg()
        if option(S('%?'))(seq):
            return Argument(caty.UNDEFINED)

        name = seq.parse(Regex(r'%%%s\??' % _name_token_ptn, re.X))[1:]
        optional = False
        if name.endswith('?'):
            name = name[:-1]
            optional = True
        if optional and option('=')(seq):
            d = seq.parse([xjson.string, 
                      xjson.binary,
                      xjson.multiline_string,
                      bind2nd(xjson.null, True), 
                      bind2nd(xjson.number, True), 
                      bind2nd(xjson.integer, True), 
                      bind2nd(xjson.boolean, True),
                      ])
        else:
            d = caty.UNDEFINED
        return NamedArg(name, optional, d)

    def arg(self, seq):
        r = choice(
                  bind2nd(xjson.null, True), 
                  bind2nd(xjson.boolean, True),
                  xjson.string, 
                  xjson.multiline_string,
                  self.unquoted_maybe_num, 
                  self.named_arg,
                  self.indexed_arg
                  )(seq)
        return Argument(r) if not isinstance(r, Param) else r

    def indexed_arg(self, seq):
        index = seq.parse(Regex(ur'%[0-9]+\??'))[1:]
        optional = False
        if index.endswith('?'):
            index = int(index[:-1])
            optional = True
        else:
            index = int(index)
        if optional and option('=')(seq):
            d = seq.parse([xjson.string, 
                      xjson.binary,
                      xjson.multiline_string,
                      bind2nd(xjson.null, True), 
                      bind2nd(xjson.number, True), 
                      bind2nd(xjson.integer, True), 
                      bind2nd(xjson.boolean, True),
                      ])
        else:
            d = caty.UNDEFINED
        return IndexArg(index, optional, d)

    def comma(self, seq):
        _ = seq.parse(',')
        return _

    def list(self, seq):
        from itertools import dropwhile
        seq.parse('[')
        values = seq.parse(split(self.listitem, self.comma, True))
        seq.parse(']')
        l = ListBuilder()
        l.set_values(anything(values))
        return l

    def par_list(self, seq):
        from itertools import dropwhile
        seq.parse('=[')
        items = seq.parse(split(choice(lambda s: (False, self.listitem(s)), self.wildcard_item), self.comma, True))
        seq.parse(']')
        wild = len([i for i in items if i[0]])
        if wild > 1:
            raise ParseError(seq, self.par_list)
        elif wild:
            w = True
        else:
            w = False
        l = ParallelListBuilder()
        l.set_values(anything([i[1] for i in items]))
        l.set_wildcard(w)
        return l

    def wildcard_item(self, seq):
        S('*')(seq)
        try:
            return True, seq.parse(self.make_pipeline)
        except NothingTodo:
            raise ParseFailed(seq, self.listitem)

    def listitem(self, seq):
        if seq.current == ']': 
            return None
            #return CommandProxy(u'undefined', [], {}, [], (seq.col, seq.line))
        try:
            return seq.parse([self.make_pipeline, self.loose_item])
        except NothingTodo:
            raise ParseFailed(seq, self.listitem)

    def loose_item(self, seq):
        if not seq.peek(self.comma):
            raise ParseFailed(seq, self.listitem)
        return CommandProxy(u'undefined', [], {}, [], (seq.col, seq.line))

    def par_obj(self, seq):
        seq.parse('={')
        items = seq.parse(split(self.par_item, self.comma, True))
        seq.parse('}')
        o = ParallelObjectBuilder()
        for i in anything(items):
            o.add_node(i)
        return o

    def par_item(self, seq):
        if seq.current == '}': return
        n = choice(xjson.string, S(u'*'))(seq)
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

    def choice_branch(self, seq):
        seq.parse(keyword('branch'))
        seq.parse('{')
        name_set = set()
        cases = seq.parse(split(lambda s:self.choice_branch_item(s, name_set), self.comma, allow_last_delim=True))
        seq.parse('}')
        t = ChoiceBranch()
        for c in anything(cases):
            t.add_case(c)
        return t

    def choice_branch_item(self, seq, name_set):
        t = name_token(seq)
        if t in name_set:
            raise ParseFailed(seq, self.type_case_branch, t)
        name_set.add(t)
        S(u'=>')(seq)
        try:
            v = self.make_pipeline(seq)
        except NothingTodo:
            raise ParseFailed(seq, self.case)
        return ChoiceBranchItem(t, v)

    def type_case(self, seq):
        seq.parse(keyword('case'))
        path = option(JSONPathSelectorParser(False, True))(seq)
        if option(keyword('via'))(seq):
            seq.parse('{')
            via = self.make_pipeline(seq)
            seq.parse('}')
        else:
            via = None
        seq.parse('{')
        name_set = set()
        cases = seq.parse(split(lambda s:self.type_case_branch(s, name_set), self.comma, allow_last_delim=True))
        seq.parse('}')
        t = TypeCase(path, via)
        for c in anything(cases):
            t.add_case(c)
        return t

    def type_cond(self, seq):
        seq.parse(keyword('cond'))
        path = option(JSONPathSelectorParser(False, True))(seq)
        seq.parse('{')
        name_set = set()
        cases = seq.parse(split(lambda s:self.type_case_branch(s, name_set), self.comma, allow_last_delim=True))
        seq.parse('}')
        t = TypeCond(path)
        for c in anything(cases):
            t.add_case(c)
        return t

    def type_case_branch(self, seq, name_set):
        from caty.core.casm.language.schemaparser import typedef
        t = choice(u'*', typedef)(seq)
        if t in name_set:
            raise ParseFailed(seq, self.type_case_branch, t)
        name_set.add(t)
        S(u'=>')(seq)
        try:
            v = self.make_pipeline(seq)
        except NothingTodo:
            raise ParseFailed(seq, self.case)
        return Branch(t, v)

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
        name = seq.parse(Regex(ur'[a-zA-Z_]+[a-zA-Z0-9_-]*'))
        parsers = map(try_, [
                    self.exception_handle,
                    self.functor,
                    self.tag,
                    self.type_case,
                    self.type_cond,
                    self.cond,
                    self.object, 
                    self.diagram_order, 
                    self.value, 
                    self.call_forward,
                    self.command,
                    self.list, 
                    ])
        obj = seq.parse(option(parsers))
        seq.parse('>')
        raise HashNotationFound(name)

    def repeat(self, seq):
        S(u'repeat')(seq)
        if self.BEGIN_REPEAT not in self._context:
            raise ParseError(seq, u'repeat')
        return Repeat()

    def break_(self, seq):
        S(u'break')(seq)
        if self.EACH not in self._context:
            raise ParseError(seq, u'break')
        return Break()

    def empty(self, seq):
        if seq.eof:
            self.continue_to_parse = False
            return Empty()
        o = option(peek(_OPERATORS))(seq)
        if o in ('|', ';'):
            return Empty()
        if option(peek('}'))(seq):
            return Empty()
        raise ParseFailed(seq, self.pipeline)

def anything(l):
    return filter(lambda i: i!= None, l)

def list_to_opts_and_args(arg_list):
    opts = {}
    args = []
    key = None
    has_upcoming_value = False
    for a in arg_list:
        if isinstance(a, unicode):
            if a.startswith('--'):
                if '=' in a:
                    k, v = a.split('=', 1)
                    opts[k[2:]] = v.strip('"')
                    continue
                else:
                    key = k[2:]
                    continue
            if a == '=':
                has_upcoming_value = True
                continue
        if key and has_upcoming_value:
            opts[key] = a
            has_upcoming_value = False
            key = None
            continue
        if key:
            opts[key] = True
            key = None
        args.append(a)
    return opts, args



import re
_SINGLE = re.compile(u'//.*')
_MULTI = re.compile(u'/\\*.*\\*/', re.DOTALL)
def _remove_comment(v):
    return _SINGLE.sub(u' ', _MULTI.sub(u' ', v))

class ContinuedComment(Exception): pass

