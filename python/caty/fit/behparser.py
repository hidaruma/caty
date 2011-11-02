#coding: utf-8
from topdown import *

@as_parser
def parser(seq):
    return [e for e in many(elements)(seq) if e is not None]

def elements(seq):
    return seq.parse([comment, heading, table, code, code2, paragraph])

def heading(seq):
    _ = skip_ws(seq)
    l = seq.line
    h = seq.parse(many1('='))
    t = seq.parse(until('\n'))
    _ = seq.parse(many('\n'))
    return Heading(t, len(h), l)

def table(seq):
    l = seq.line
    rows = many1(row)(seq)
    return Table(rows, l)

def row(seq):
    _ = seq.parse('|')
    t = seq.parse(until('\n'))
    l = seq.line
    cells = many1(cell).run(t)
    _ = seq.parse('\n')
    return Row(cells, l)

def cell(seq):
    c = option('=')(seq)
    t = ''
    while not seq.eof:
        t += seq.parse(until('|'))
        if t.endswith('~') and seq.current == '|':
            t = t[:-1] + u'|'
            seq.next()
        else:
            break
    _ = seq.parse('|')
    l = seq.line
    if c == '=':
        return HeaderCell(t.strip(), l)
    else:
        return DataCell(t.strip(), l)

def code(seq):
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
    return Code(t.strip('\n'), t)

def code2(seq):
    _ = seq.parse(line_by_itself('<<{'))
    t = u'\n'
    while not seq.eof:
        t += until('}>>')(seq)
        if not t.endswith('\n'):
            if t.endswith(' '):
                t = t[:-1]
            t += seq.parse('}>>')
        else:
            seq.parse(option(line_by_itself('}>>'), u''))
            break
    return Code(t.strip('\n'), t)


def paragraph(seq):
    t = seq.parse(until(['\n\n', 
                         '\n<<{', 
                         '\n= ', 
                         '\n== ', 
                         '\n=== ',
                         '\n==== ',
                         '\n===== ',
                         '\n====== ',
                         '\n|=',
                         ]))
    l = seq.line
    _ = seq.parse(many('\n'))
    return Paragraph(t.strip(), l)

class Heading(object):
    type = 'heading'

    def __init__(self, text, level, lineno):
        self.text = text.strip('=').strip()
        self.level = level
        self.lineno = lineno

    def __eq__(self, another):
        return (self.level == another.level
                and self.text == another.text)

    def __str__(self):
        return '<heading%d> %s' % (self.level, self.text)

class Text(object):
    def __init__(self, text, lineno):
        self.text = text
        self.lineno = lineno

    def __eq__(self, another):
        return self.text == another.text

    def __str__(self):
        return self.text

class Paragraph(Text):
    type = 'paragraph'

class Code(Text):
    type = 'code'

def container(type):
    class Container(object):
     
        def __init__(self, items, lineno):
            assert all(map(lambda x:isinstance(x, type), items)), (type, items)
            self.items = items
            self.lineno = lineno

        def __iter__(self):
            return iter(self.items)

        def __getitem__(self, i):
            return self.items[i]

        @property
        def item_num(self):
            return len(self.items)

        def __eq__(self, another):
            return (self.item_num == another.item_num and 
                    all(map(lambda x:x[0] == x[1], zip(self.items, another.items))))
    return Container

class Cell(Text):
    def __init__(self, text, lineno):
        Text.__init__(self, text.strip(), lineno)

def row_type():
    return container(Row)

def cell_type():
    return container(Cell)

class Row(cell_type()):
    type = 'row'

    def __str__(self):
        return '|%s|' % ('|'.join(map(str, self.items)) )

class Table(row_type()):
    type = 'table'

    def __str__(self):
        return '\n'.join(map(str, self.items))

class HeaderCell(Cell):
    type = 'header-cell'

    def __str__(self):
        return '= ' + self.text

class DataCell(Cell):
    type = 'data-cell'

def comment(seq):
    seq.parse('<<')
    seq.parse(skip_ws)
    seq.parse('ignore')
    seq.parse(until('>>'))
    seq.parse('>>')
    return None
