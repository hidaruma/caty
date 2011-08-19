from topdown import *
from topdown.util import line_by_itself
from creole.syntax.base import BlockParser

class Preformat(BlockParser):

    def __call__(self, seq):
        _ = seq.parse(line_by_itself('{{{'))
        t = u''
        while not seq.eof:
            t += until('}}}')(seq)
            if t.endswith(' '):
                t = t[:-1]
                t += seq.parse(option(line_by_itself('}}}')))
            else:
                seq.parse(option(line_by_itself('}}}')))
                break
        return self.create_element('pre', None, [t])

