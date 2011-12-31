#coding: utf-8
u"""Smarty 構文サブセットのパーサ。
"""

from topdown import *
from caty.template.core.st import *
from caty.util import bind2nd

class SmartyParser(Parser):

    def __call__(self, seq):
        t = self.smarty_template(seq)
        if not seq.eof:
            raise ParseFailed(seq, None)
        return t

    def smarty_template(self, seq):
        ts = seq.parse(many(self.term))
        return Template(ts)

    def term(self, seq):
        s = seq.parse([self.literal, self.delim, self.statement, try_(self.comment)])
        return s

    def literal(self, seq):
        s = seq.parse(until('{'))
        if not s:
            if seq.eof or not option(peek(S('{literal}')))(seq):
                raise ParseFailed(seq, self.literal)
            s = u''
        escape = seq.parse(option('{literal}'))
        skip_ws(seq)
        if escape is None:
            return String(s)
        else:
            s2 = seq.parse(until('{/literal}'))
            closing = seq.parse(option('{/literal}'))
            if not closing:
                raise ParseError(seq, self.literal, u'missing {/literal}')
            skip_ws(seq)
            return String(''.join([s, s2]))

    def delim(self, seq):
        if choice('{$ldelim}', '{$rdelim}')(seq) == '{$ldelim}':
            return String(u'{')
        return String(u'}')

    def comment(self, seq):
        seq.parse('{*')
        seq.parse(until('*}'))
        try:
            seq.parse('*}')
        except:
            raise ParseError(seq, self.comment, u'Missing end of comment')
        return Null()

    def statement(self, seq):
        s = seq.parse([self.if_, self.for_, self.include, try_(self.var), self.def_func, try_(self.call_func)])
        return s

    def var(self, seq):
        ob = seq.parse('{')
        ws = seq.parse(option(skip_ws))
        load = self.varload(seq)
        ws = seq.parse(option(skip_ws))
        cb = seq.parse('}')
        return Template([load, VarDisp()])

    def varload(self, seq):
        d = seq.parse('$')
        v = self.varref(seq)
        filters = many(self.filter_call)(seq)
        if not filters:
            return VarLoad(v, True)
        else:
            return Template([VarLoad(v, True)] + filters)

    def varref(self, seq):
        r = [self.varname(seq)]
        while True:
            v = option('.')(seq)
            if not v:
                break
            else:
                r.append(v+self.varname(seq))
        return ''.join(r)

    def varname(self, seq):
        name = seq.parse(choice(self.dynamic_property, Regex(r'[a-zA-Z_][a-zA-Z_0-9]*')))
        idx = seq.parse(many(self.index))
        return name + '.' + ('.'.join(idx)) if idx != [] else name

    def dynamic_property(self, seq):
        return choice(u'tag()', u'untagged()', u'content()', u'exp-tag()', u'length()')(seq)

    def index(self, seq):
        # [] を削除した上で値を戻す
        r = seq.parse([Regex(r'\[[0-9]+\]'), Regex(r'\[".+?"\]')])
        return  r[1:-1].strip('"')

    def filter_call(self, seq):
        skip_ws(seq)
        seq.parse('|')
        skip_ws(seq)
        name = seq.parse(Regex(r'[a-zA-Z_][a-zA-Z_0-9]*'))
        skip_ws(seq)
        args = many(self.argument)(seq)
        return FilterCall(name, args)

    def integer(self, s):
        return int(s.parse(Regex(r'-?[0-9]+')))

    def number(self, s):
        return float(s.parse(Regex(r'-?[0-9]+\.[0-9]+')))

    def boolean(self, s):
        return bool(s.parse(['true', 'false']).toupper())

    def string(self, s):
        s.parse('"')
        r = s.parse(until('"'))
        s.parse('"')
        return u'%s' % r

    def argument(self, seq):
        skip_ws(seq)
        seq.parse(':')
        skip_ws(seq)
        return seq.parse([self.integer, self.number, self.boolean, self.string])

    def include(self, seq):
        i = seq.parse('{include')
        ws = seq.parse(skip_ws)
        f = seq.parse('file')
        ws = seq.parse(option(skip_ws))
        e = seq.parse('=')
        ws = seq.parse(option(skip_ws))
        q = seq.parse('"')
        name = seq.parse(until('"'))
        q = seq.parse('"')
        ws = seq.parse(option(skip_ws))
        c = seq.parse(option('context'))
        if c:
            e = seq.parse('=')
            ws = seq.parse(option(skip_ws))
            q = seq.parse('"')
            cn = seq.parse(until('"'))
            q = seq.parse('"')
        else:
            cn = u'_CONTEXT'
        ws = seq.parse(option(skip_ws))
        cb = seq.parse('}')
        skip_ws(seq)
        return Include(name, cn)

    def if_(self, seq):
        _ = seq.parse('{if')
        ws = seq.parse(skip_ws)
        varnode = self.varload(seq)
        ws = seq.parse(skip_ws)
        _ = seq.parse('}')
        subtempl = self.smarty_template(seq)
        elifnodes = many(self.elif_)(seq) or Null()
        elsenode = option(self.else_, Null())(seq)
        _ = seq.parse('{/if}')
        skip_ws(seq)
        return If(varnode, subtempl, elifnodes, elsenode)

    def elif_(self, seq):
        _ = seq.parse('{elseif')
        ws = seq.parse(skip_ws)
        varnode = self.varload(seq)
        ws = seq.parse(skip_ws)
        _ = seq.parse('}')
        skip_ws(seq)
        subtempl = self.smarty_template(seq)
        return Elif(varnode, subtempl)

    def else_(self, seq):
        _ = seq.parse('{else}')
        skip_ws(seq)
        subtempl = self.smarty_template(seq)
        return Else(subtempl)

    def for_(self, seq):
        _ = seq.parse('{foreach')
        ws = seq.parse(skip_ws)
        attr = self.loop_attr(seq)
        loopitem = attr.get('item')
        loopkey = attr.get('key', 'key')
        loop_name = attr.get('name', 'default')
        varnode = attr.get('var')
        ws = seq.parse(skip_ws)
        _ = seq.parse('}')
        skip_ws(seq)
        subtempl = self.smarty_template(seq)
        elsetempl = option(self.for_else, Null())(seq)
        _ = seq.parse('{/foreach}')
        skip_ws(seq)
        index_name = "smarty.foreach.%s.index" % loop_name
        iteration_name = "smarty.foreach.%s.iteration" % loop_name
        counter_name = "smarty.foreach.%s.total" % loop_name
        first = "smarty.foreach.%s.first" % loop_name
        last = "smarty.foreach.%s.last" % loop_name
        return For(loopitem, 
                   varnode, 
                   loopkey, 
                   index_name, 
                   iteration_name, 
                   counter_name,
                   first,
                   last,
                   subtempl,
                   elsetempl)

    def loop_attr(self, seq):
        return dict(seq.parse(many1([self.loop_item, self.loop_key, self.loop_name, self.loop_var])))

    def loop_var(self, seq):
        skip_ws(seq)
        seq.parse('from')
        skip_ws(seq)
        seq.parse('=')
        skip_ws(seq)
        load = self.varload(seq)
        return ('var', load)

    def _loop_attr(self, seq, t):
        skip_ws(seq)
        seq.parse(t)
        skip_ws(seq)
        seq.parse('=')
        item = seq.parse(Regex(r'[a-zA-Z_][a-zA-Z0-9_]*'))
        return (t, item)

    def loop_item(self, seq):
        return self._loop_attr(seq, 'item')

    def loop_key(self, seq):
        return self._loop_attr(seq, 'key')

    def loop_name(self, seq):
        return self._loop_attr(seq, 'name')

    def for_else(self, seq):
        seq.parse('else}')
        skip_ws(seq)
        return self.smarty_template(seq)

    def def_func(self, seq):
        skip_ws(seq)
        seq.parse(keyword('{function'))
        skip_ws(seq)
        name = self.func_name(seq)
        skip_ws(seq)
        default_vars = many(self.func_vars)(seq)
        skip_ws(seq)
        S('}')(seq)
        body = self.smarty_template(seq)
        _ = seq.parse('{/function}')
        skip_ws(seq)
        return DefMacro(name, default_vars, body)

    def func_name(self, seq):
        n = option(keyword('name'))(seq)
        if n:
            if seq.current == '=':
                S('=')(seq)
                return seq.parse(Regex(r'[a-zA-Z_][a-zA-Z0-9_]*'))
            else:
                return n
        else:
            return seq.parse(Regex(r'[a-zA-Z_][a-zA-Z0-9_]*'))

    def func_vars(self, seq):
        name = seq.parse(Regex(r'[a-zA-Z_][a-zA-Z0-9_]*'))
        skip_ws(seq)
        S('=')(seq)
        value = seq.parse([self.integer, self.number, self.boolean, self.string])   
        skip_ws(seq)
        return (name, value)

    def call_func(self, seq):
        seq.parse('{call')
        skip_ws(seq)
        seq.parse('name')
        skip_ws(seq)
        seq.parse('=')
        skip_ws(seq)
        name = seq.parse(Regex(r'[a-zA-Z_][a-zA-Z0-9_]*'))
        skip_ws(seq)
        args = many(self.func_args)(seq)
        skip_ws(seq)
        S('}')(seq)
        skip_ws(seq)
        return ExpandMacro(name, args)

    def func_args(self, seq):
        arg_name = seq.parse(Regex(r'[a-zA-Z_][a-zA-Z0-9_]*'))
        skip_ws(seq)
        S('=')(seq)
        skip_ws(seq)
        var_name = seq.parse(Regex(r'\$[a-zA-Z_][a-zA-Z0-9_]*'))
        skip_ws(seq)
        return (arg_name, var_name[1:])

    def name(self, seq):
        return choice(Regex(r'[a-zA-Z_][a-zA-Z0-9_]*'), self.string)(seq)

