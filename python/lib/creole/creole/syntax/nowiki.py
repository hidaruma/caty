from topdown import *
from creole.syntax.base import InlineParser

class NoWiki(InlineParser):
    def __init__(self, factory=None):
        self.start = u'{{{'
        self.end = u'}}}'
        InlineParser.__init__(self, factory)

    def __call__(self, seq, start):
        t = seq.parse(until(self.end))
        while seq.current == '}':
            t += seq.current
            seq.next()
        if t.endswith(self.end):
            t = t[0:-3]
        return self.create_element('tt', None, self.escape_tilda(t))


