from topdown import *
from creole.syntax.base import InlineParser

class Em(InlineParser):
    def __init__(self, inline, factory=None):
        self.start = u'//'
        self.end = u'//'
        self.inline = inline
        InlineParser.__init__(self, factory)

    def __call__(self, seq, start):
        text = self._enter(seq)
        return self.create_element('em', None, self.inline.run(text))

    def _enter(self, seq):
        t = []
        end = [u'~', self.end]
        while not seq.eof:
            s = seq.parse(until(end))
            t.append(s)
            if s.endswith('http:') or s.endswith('https:'):
                t.append(seq.parse(self.end))
            else:
                if seq.eof:
                    break
                s = seq.parse(end)
                if s == u'~':
                    t.append(s)
                    t.append(seq.current)
                    seq.next()
                else:
                    break
        text = ''.join(t)
        return text
