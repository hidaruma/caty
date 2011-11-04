from topdown import *
from topdown.util import *
from creole.syntax.base import WikiParser, BlockParser

class BlockPlugin(BlockParser):
    def __call__(self, seq):
        _ = seq.parse(Regex(' *<<'))
        skip_ws(seq)
        name = seq.parse(Regex('[a-zA-Z][a-zA-Z0-9_-]*'))
        skip_ws(seq)
        raw_arg = until(u'>>')(seq)
        S('>>')(seq)
        skip_ws(seq)
        return self.syntax.call_plugin(name, raw_arg)

class InlinePlugin(WikiParser):
    
    def __init__(self, syntax, element_factory=None):
        WikiParser.__init__(self, element_factory)
        self.__syntax = syntax
        self.start = u'<<'
        self.end = u'>>'

    def __call__(self, seq, s):
        content = until([self.end, '\n'])(seq)
        choice(self.end, '\n')(seq)
        if not content:
            return u'<<>>'
        if ' ' not in content:
            return self.__syntax.call_plugin(content)
        name, raw_args = content.split(' ', 1)
        return self.__syntax.call_plugin(name.strip(), raw_args)


