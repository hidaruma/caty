from __future__ import absolute_import
from topdown import *
from creole.syntax.base import InlineParser

class SubScript(InlineParser):
    def __init__(self, inline, factory=None):
        self.start = u',,'
        self.end = u',,'
        self.syntax = inline
        InlineParser.__init__(self, factory)

    def __call__(self, seq, start):
        text = self._enter(seq)
        return self.create_element('sub', None, self.escape_tilda(text))



