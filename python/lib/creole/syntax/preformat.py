from topdown import *
from topdown.util import line_by_itself
from creole.syntax.base import BlockParser

class Preformat(BlockParser):

    def __call__(self, seq):
        _ = seq.parse(line_by_itself('{{{'))
        t = u'\n'
        while not seq.eof:
            t += until('}}}')(seq)
            if not t.endswith('\n'):
                if t.endswith(' '):
                    t = t[:-1]
                t += seq.parse('}}}')
            else:
                seq.parse(option(line_by_itself('}}}'), u''))
                break
        return self.create_element('pre', None, [t])

