from topdown import *
from creole.tree import Element
from creole.syntax.base import BlockParser

class Heading(BlockParser):
    def __call__(self, seq):
        level = 0
        while seq.current == '=':
            seq.next()
            level += 1
        if not level:
            raise ParseFailed(seq, self)
        ws = seq.parse(many(' '))
        line = seq.parse(until('\n'))
        s = line.strip().rstrip('=')
        if not s:
            raise ParseFailed(seq, self)
        if level > 6: level = 6
        tag = 'h%d' % level
        return self.create_element(tag, None, [s])


