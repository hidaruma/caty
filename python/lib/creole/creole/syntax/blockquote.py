from topdown import *
from creole.syntax.base import BlockParser
import re

class BlockQuote(BlockParser):
    def __call__(self, seq):
        bq_open = re.compile(' *\\|>> *\n')
        bq_close = re.compile(' *\\|<< *$')
        _ = seq.parse(Regex(' *\\|>> *\n'))
        lines = []
        nest = 1
        while not seq.eof:
            l = seq.readline()
            if bq_open.match(l):
                nest += 1
                lines.append('\n'+l)
            elif bq_close.match(l):
                nest -= 1
                if nest == 0:
                    break
                else:
                    lines.append(l)
            else:
                lines.append(l)
        t = ''.join(lines)
        return self.create_element('blockquote', None, self.syntax.block.run(t+'\n\n'))

