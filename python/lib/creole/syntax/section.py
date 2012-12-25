from __future__ import absolute_import
from topdown import *
from creole.syntax.base import WikiParser

class Section(WikiParser):
    def __init__(self, creole, factory=None):
        self.creole = creole
        WikiParser.__init__(self, factory)

    def __call__(self, seq):
        _ = seq.parse('[[[')
        classess = map(basestring.strip, split(seq, Regex(r' *[a-zA-Z]+[a-zA-Z0-9_-]* *'), '|'))
        t = until(']]]')(seq)
        _ = seq.parse(']]]')
        c = self.creole.process(t).childnode
        return self.create_element('div', [('class', classes)], c if isinstance(c, list) else [c])


