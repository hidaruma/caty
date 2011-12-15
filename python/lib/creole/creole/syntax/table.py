from topdown import *
from creole.syntax.base import BlockParser

class Table(BlockParser):

    def __call__(self, seq):
        if not seq.current == '|':
            raise ParseFailed(seq, self)
        return self.create_element('table', None, many1(self.table_row)(seq))

    def table_row(self, seq):
        line = until('\n')(seq)
        lf = seq.parse('\n')
        return self.create_element('tr', None, many1(self.table_cell).run(line))

    def table_cell(self, seq):
        _ = seq.parse('|')
        c = ''
        anchor_point = 0
        while not seq.eof:
            c += until('|')(seq)
            if c.endswith('~') and seq.current == '|':
                c = c[:-1] + '|'
                seq.next()
            else:
                p = c.find('[[', anchor_point)
                if p == -1:
                    break
                seq.next()
                anchor_point = p+1
        if not c or (seq.current != '|' and not c.strip()):
            raise ParseFailed(seq, self.table_cell)
        h = c.startswith('=')
        if h:
            t = 'th'
            c = c[1:]
        else:
            t = 'td'
        return self.create_element(t, None, self.inline.run(c))

