#coding:utf-8
from caty.fit.document.base import *
from caty.util.cx import creole2html
from caty.core.exception import InternalException
from topdown import *

class FitParagraph(FitNode):
    def _build(self, node):
        self.text = node.text

    def accept(self, test_runner):
        test_runner.add(self)

    def to_html(self):
        return creole2html(self.text)

    type = 'text'

class FitCode(FitNode):
    def _build(self, node):
        self.text = node.text
        self.cls = node.cls

    def accept(self, test_runner):
        test_runner.add(self)
        
    def to_html(self):
        if not self.cls:
            return u'<pre>%s</pre>' % escape_html(self.text)
        else:
            return u'<pre class="%s">%s</pre>' % (self.cls, escape_html(self.text))

    type = 'code'

class FitTable(FitNode):
    def __init__(self, node, node_maker):
        FitNode.__init__(self, node, node_maker)

    def _build(self, node):
        self.items = map(self.row_maker, node.items)
        
    def row_maker(self, node):
        return FitRow(node, self._node_maker)

    def accept(self, test_runner):
        test_runner.add(self)

    def to_html(self):
        return '<table>%s</table>\n\n' % ('\n'.join([r.to_html() for r in self.items]))

    type = 'table'

class FitRow(FitNode):
    def _build(self, node):
        self.items = map(self.cell, node.items)

    def is_title_row(self):
        return all(map(lambda x:x.type == 'header-cell', self.items))

    def accept(self, test_runner):
        assert False, u'このメソッドは本来呼び出されない'

    def to_html(self):
        return u'<tr>%s</tr>' % (''.join([c.to_html() for c in self.items]))

    def cell(self, node):
        if node.type == 'header-cell':
            return FitHeaderCell(node, self._node_maker)
        else:
            return FitDataCell(node, self._node_maker)

    def __getitem__(self, n):
        return self.items[n]

class FitHeaderCell(FitNode):
    def _build(self, node):
        self.text = node.text.strip()
        self.style = u''

    def apply_macro(self, macro):
        mp = MacroParser()
        r = []
        t = self.text
        while True:
            l, m, t = mp.run(t)
            r.append(l)
            if m:
                if m in macro:
                    r.append(macro[m])
                else:
                    raise InternalException('Undefined macro: $macro', macro=m)
            else:
                break
        self.text = ''.join(r)

    def accept(self, test_runner):
        assert False, u'このメソッドは本来呼び出されない'

    def to_html(self):
        if not self.style:
            return u'<th>%s</th>' % escape_html(self.text)
        else:
            return u'<th class="%s">%s</th>' % (self.style, escape_html(self.text))

class MacroParser(Parser):
    def __call__(self, seq):
        leading = until('%%')(seq)
        is_macro = option('%%')(seq)
        if is_macro:
            macro = seq.parse(Regex(u'[a-zA-Z][a-zA-Z0-9-]*'))
            return leading, macro, seq.rest
        else:
            return leading, '', ''

class FitDataCell(FitHeaderCell):
    def to_html(self):
        return u'<td>%s</td>' % escape_html(self.text)


