from caty.core.casm.language.casmparser import module_decl
from caty.core.camb.binding import ModuleBindings, Binding
from caty.core.language.util import docstring, annotation, fragment_name, annotation, identifier_token, identifier_token_m, name_token, some_token
from topdown import *
from topdown.util import quoted_string

class BindingParser(Parser):
    def __init__(self, module_name, app):
        self._module_name = module_name
        self._app = app

    def __call__(self, seq):
        mn = module_decl(seq, u'camb')
        ds = mn.docstring or u''
        if name != self._module_name:
            raise ParseFailed(seq, self, u'module name mismatched: %s' % name)
        bindings = many(self.bindings)
        return ModuleBindings(self._module_name, bindings, ds)

    def bindings(self, seq):
        ds = option(docstring, u'')(seq)
        ann = annotations(seq)
        keyword(u'bind')(seq)
        keyword(u'port')(seq)
        port = name_token(seq)
        S(u'-->')(seq)
        target, type = self.target(seq)
        S(u';')(seq)
        return Binding(port, target, type)

    def target(self, seq):
        return choice(self.action, self.url)(seq)

    def action(self, seq):
        tp = keyword(u'action')(seq)
        name = identifier_token_m(seq)
        return name, tp

    def url(self, seq):
        tp = keyword(u'url')
        dest = quoted_string(seq)
        return dest, tp

class LiterateBindingParser(BindingParser):
    def __call__(self, seq):
        h = seq.ignore_hook
        seq.ignore_hook = True
        while True:
            x = until(u'<<{')(seq)
            S(u'<<{')(seq)
            if x.endswith('~'):
                continue
            break
        seq.ignore_hook = h
        mn = module_decl(seq, u'camb')
        ds = mn.docstring or u''
        if name != self._module_name:
            raise ParseFailed(seq, self, u'module name mismatched: %s' % name)
        bindings = self._parse_top_level(seq)
        return ModuleBindings(self._module_name, bindings, ds)

    def _parse_top_level(self, seq):
        s = []
        while not seq.eof:
            n = seq.parse(map(try_, [self.bindings, peek(S(u'}>>'))]))
            if n == u'}>>':
                break
            s.append(n)
        until(u'}>>')(seq)
        S(u'}>>')(seq)
        literal = True
        while not seq.eof:
            h = seq.ignore_hook
            seq.ignore_hook = True
            while literal:
                x = until(u'<<{')(seq)
                if seq.eof:
                    break
                S(u'<<{')(seq)
                if x.endswith('~'):
                    continue
                literal = False
            if seq.eof:
                break
            seq.ignore_hook = h
            n = seq.parse(map(try_, [self.bindings, peek(S(u'}>>'))]))
            if n == u'}>>':
                S(u'}>>')(seq)
                literal = True
            else:
                s.append(n)
        return s

