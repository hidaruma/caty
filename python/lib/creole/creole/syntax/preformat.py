from topdown import *
from creole.syntax.base import BlockParser

class Preformat(BlockParser):

    def __call__(self, seq):
        _ = seq.parse('{{{')
        t = u''
        while not seq.eof:
            t += until('}}}')(seq)
            if t.endswith(' '):
                t = t[:-1]
                t += seq.parse(option('}}}'))
            else:
                seq.parse(option('}}}'))
                break
        return self.create_element('pre', None, [t])

