from topdown import *
from creole.tree import Element
from creole.syntax.base import BlockParser

class Horizonal(BlockParser):

    def __call__(self, seq):
        _ = seq.parse('----')
        seq.parse(EOL)
        return self.create_element('hr', None, None)

