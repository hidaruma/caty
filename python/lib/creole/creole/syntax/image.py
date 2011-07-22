from topdown import *
from creole.syntax.base import WikiParser

class Image(WikiParser):
    def __init__(self, factory=None):
        self.start = '{{'
        self.end = '}}'
        WikiParser.__init__(self, factory)

    def __call__(self, seq, start):
        url = seq.parse(until('|'))
        seq.parse('|')
        text = seq.parse(until('}}'))
        seq.parse('}}')
        attr = [('src', url), ('alt', text)]
        return self.create_element('img', attr, None)


