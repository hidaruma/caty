from __future__ import absolute_import
from topdown import *
from creole.syntax.base import WikiParser

class Break(WikiParser):
    def __init__(self, factory=None):
        self.start = '\\\\'
        self.end = ''
        WikiParser.__init__(self, factory)

    def __call__(self, seq, start):
        return self.create_element('br', None, None)


