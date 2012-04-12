#coding: utf-8
u"""Smarty 構文サブセットのパーサ。
"""
from caty.template.smarty.parser import *

class SmartyMXParser(SmartyParser):
    def statement(self, seq):
        s = seq.parse([self.if_, self.for_, self.include, try_(self.var), self.def_func, self.def_group, self.call_func, self.match_call])
        return s

    def def_func(self, seq):
        skip_ws(seq)
        seq.parse(keyword('{function'))
        skip_ws(seq)
        name = option(self.func_name)(seq)
        skip_ws(seq)
        match = option(self._func_match)(seq)
        skip_ws(seq)
        if not name and not match:
            raise ParseError(seq, self.def_func)
        context_type = option(self._type, 'any')(seq)
        skip_ws(seq)
        matched = option(self._matched, 'type')(seq)
        S('}')(seq)
        body = self.smarty_template(seq)
        _ = seq.parse('{/function}')
        skip_ws(seq)
        return DefFunc(name, match, context_type, matched, body)

    def func_name(self, seq):
        n = keyword('name')(seq)
        skip_ws(seq)
        S('=')(seq)
        skip_ws(seq)
        return seq.parse([self.name, Regex(r'[a-zA-Z_][a-zA-Z0-9_]*')])

    def _func_match(self, seq):
        seq.parse(keyword('match'))
        skip_ws(seq)
        S('=')(seq)
        skip_ws(seq)
        patn = seq.parse(['*!', '*', self.name, Regex(r'[-0-9a-zA-Z_]+')])
        return patn
    
    def _type(self, seq):
        seq.parse('type')
        skip_ws(seq)
        S('=')(seq)
        skip_ws(seq)
        return self.name(seq)

    def _matched(self, seq):
        seq.parse('matched')
        skip_ws(seq)
        S('=')(seq)
        skip_ws(seq)
        return self.name(seq)

    def def_group(self, seq):
        seq.parse(keyword('{group'))
        skip_ws(seq)
        keyword('name')(seq)
        skip_ws(seq)
        S('=')(seq)
        skip_ws(seq)
        name = self.name(seq)
        skip_ws(seq)
        S('}')(seq)
        member = many(choice(self.def_group, self.def_func))(seq)
        _ = seq.parse('{/group}')
        skip_ws(seq)
        return DefGroup(name, member)

    def call_func(self, seq):
        keyword('{call')(seq)
        skip_ws(seq)
        keyword('name')(seq)
        skip_ws(seq)
        S('=')(seq)
        skip_ws(seq)
        name = self.name(seq)
        skip_ws(seq)
        ctx = option(self._context, VarLoad('CONTEXT', True))(seq)
        S('}')(seq)
        return CallFunc(name, ctx)

    def _context(self, seq):
        keyword('context')(seq)
        skip_ws(seq)
        S('=')(seq)
        skip_ws(seq)
        ctx = self.varload(seq)
        skip_ws(seq)
        return ctx

    def match_call(self, seq):
        keyword('{apply')(seq)
        skip_ws(seq)
        if option(keyword('group'))(seq):
            skip_ws(seq)
            S('=')(seq)
            skip_ws(seq)
            name = self.name(seq)
        else:
            name = None
        skip_ws(seq)
        ctx = option(self._context, VarLoad('CONTEXT', True))(seq)
        S('}')(seq)
        return CallGroup(name, ctx)

