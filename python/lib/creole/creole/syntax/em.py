from topdown import *
from creole.syntax.base import InlineParser

class Em(InlineParser):
    def __init__(self, inline, factory=None):
        self.start = u'//'
        self.end = u'//'
        self.inline = inline
        InlineParser.__init__(self, factory)

    def __call__(self, seq, start):
        #t = []
        #while not seq.eof:
        #    s = seq.parse(until(self.end))
        #    if s.endswith('http:') or s.endswith('https:'):
        #        t.append(s)
        #        t.append(seq.parse(self.end))
        #    elif s.endswith('~') and seq.peek(option(self.end)):
        #        t.append(s[:-1])
        #        t.append(seq.parse(self.end))
        #    else:
        #        seq.parse(option(self.end))
        #        t.append(s)
        #        break
        text = self._enter(seq)
        return self.create_element('em', None, self.inline.run(text))

