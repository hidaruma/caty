from topdown import *
from creole.syntax.base import InlineParser

class Strong(InlineParser):
    def __init__(self, inline, factory=None):
        self.start = u'**'
        self.end = u'**'
        self.inline = inline
        InlineParser.__init__(self, factory)

    def __call__(self, seq, start):
        text = self._enter(seq)
        return self.create_element('strong', None, self.inline.run(text, ['//']))

