#coding: utf-8
from caty.fit.document.base import *
from caty.fit.document.literal import *
import caty.core.runtimeobject as ro

class FitTitle(FitNode):
    def _build(self, node):
        self.text = node.text

    def accept(self, test_runner):
        test_runner.set_title(self.text)
        test_runner.add(self)

    def to_html(self):
        return u'<h1>%s</h1>\n' % escape_html(self.text)

    type = 'title'

class FitInclude(FitNode):
    u"""include ディレクティブに対応
    """
    def _build(self, node):
        self._path = node.text.split(':', 1)[1]
        self._text = u''

    def accept(self, test_runner):
        self._text = test_runner.include_file(self._path)
        test_runner.add(self)

    def to_html(self):
        return u'<pre>%s</pre>' % escape_html(self._text)

    type = 'include'

class FitSection(FitNode):
    u"""コマンドやマクロなど、セクション構造を作る要素の基底クラス。
    """
    def _build(self, node):
        self.text = node.text
        self.level = min(node.level, 6)
        self._node_list = []

    def add(self, node):
        self._node_list.append(self._node_maker.make(node))
    
    def apply_macro(self, macro):
        for n in self._node_list:
            n.apply_macro(macro)

    def append_macro(self, macro):
        for n in self._node_list:
            n.append_macro(macro)

    def accept(self, test_runner):
        test_runner.add(self)

    def to_html(self):
        return u"""
<div class="section">
    <h%d>%s</h%d>
%s
</div>""" % (self.level, escape_html(self.text), self.level, ''.join([n.to_html() for n in self._node_list]))

    type = 'section'
    is_section = True

class FitCommand(FitSection):
    u"""コマンドセクション。
    コマンドセクションでは、マクロか見出しの文字列から構築した Caty スクリプトをテスト対象とし、
    直下のテーブル要素をテストデータの記載されたマトリックスとして扱い、
    Caty FIT のテストスートを構成する。
    """

    def _build(self, node):
        FitSection._build(self, node)
        self.cmd = u''

    def add(self, node):
        if node.type == 'table':
            n = self._node_maker.make_matrix(node, self)
        else:
            n = self._node_maker.make(node)
        self._node_list.append(n)

    def apply_macro(self, macro):
        seq = self.text.strip().split(':', 1)[1].strip().split(' ')
        r = []
        for s in seq:
            if s.startswith('%'):
                try:
                    r.append(macro[s[1:]])
                except:
                    raise FitDocumentError(ro.i18n.get(u"Macro '$name' is not defined", name=cmd))
            else:
                r.append(s)
        self.cmd = ' '.join(r)

    def _cmd_is_empty(self, *args, **kwds):
        assert self.cmd == u''

    def _cmd_has_value(self, *args, **kwds):
        assert self.cmd != u''

    def accept(self, test_runner):
        test_runner.add(self)
        for n in self._node_list:
            n.accept(test_runner)
    
class FitLiteral(FitSection):

    def add(self, node):
        if node.type == 'table':
            n = self._node_maker.make_table(node)
        else:
            n = self._node_maker.make(node)
        self._node_list.append(n)

    def accept(self, test_runner):
        test_runner.add(self)
        for n in self._node_list:
            n.accept(test_runner)

class FitMacro(FitSection):
    def _build(self, node):
        FitSection._build(self, node)
        name = self.text.strip().split(':', 1)[1].strip()
        self.name = name
        self.value = None

    def add(self, node):
        n = self._node_maker.make(node)
        if n.type == 'code' and self.value is None:
            self.value = n.text
        self._node_list.append(n)

    def accept(self, test_runner):
        test_runner.add(self)
        #for n in self._node_list:
        #    n.accept(test_runner)

    def append_macro(self, macro):
        assert self.name not in macro, u'Conflict: %s' % self.name
        macro[self.name] = self.value

    def to_html(self):
        return u''

    type = 'macro'

class FitMacroTable(FitTable):
    def _build(self, node):
        FitTable._build(self, node)
        self.macro = {}
        for n in node.items[1:]:
            self.macro[n.items[0].text.strip()] = n.items[1].text.strip()
    
    def accept(self, test_runner):
        pass

    def append_macro(self, macro):
        for k, v in self.macro.items():
            assert k not in macro, u'Conflict: %s' % k
            macro[k] = v
        
    type = 'macro-table'

