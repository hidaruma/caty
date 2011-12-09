from topdown import *
from creole.syntax.base import InlineParser

class SuperScript(InlineParser):
    def __init__(self, inline, factory=None):
        self.start = u'^^'
        self.end = u'^^'
        self.inline = inline
        InlineParser.__init__(self, factory)

    def __call__(self, seq, start):
        t = self._enter(seq)
        return self.create_element('sup', None, self.escape_tilda(t))


