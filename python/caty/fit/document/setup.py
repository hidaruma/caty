#coding:utf-8
from caty.fit.document.base import *
from caty.fit.document.section import *

class FitSetup(FitSection):
    def add(self, node):
        self._node_list.append(self._node_maker.make(node))


    @property
    def scripts(self):
        u"""セットアップスクリプトの出力
        """
        for n in self._node_list:
            if n.type in ('file', 'storage', 'script', 'schema'):
                yield n.script

    @property
    def teardown(self):
        for n in self._node_list:
            if n.type == 'teardown':
                return n.script
        return 'null'

    type = 'setup'

class NullSetup(FitSetup):
    def __init__(self): pass
    _node_list = []
    script = 'null'

class FitScript(FitSection):
    def _build(self, node):
        FitSection._build(self, node)
        self.content = u''
    
    def add(self, node):
        if node.type == 'code' and not self.content:
            self.content = node.text
        n = self._node_maker.make(node)
        self._node_list.append(n)

    def accept(self, test_runner):
        assert False, u'本来呼ばれることのないメソッド'

    @property
    def script(self):
        return self.content

    type = 'script'

class FitTearDown(FitScript):
    type = 'teardown'

class FitSchema(FitSection):
    def _build(self, node):
        FitSection._build(self, node)
        self.content = u''
    
    def add(self, node):
        if node.type == 'code' and not self.content:
            self.content = node.text
        n = self._node_maker.make(node)
        self._node_list.append(n)

    def accept(self, test_runner):
        assert False, u'本来呼ばれることのないメソッド'

    @property
    def script(self):
        return "'''%s''' | define-local-schema" % self.content

    type = 'schema'

class FitFile(FitSection):
    def _build(self, node):
        FitSection._build(self, node)
        self.path = node.text.split(':', 1)[1].strip()
        self.content = u''

    def add(self, node):
        if node.type == 'code' and not self.content:
            self.content = node.text
        n = self._node_maker.make(node)
        self._node_list.append(n)

    def accept(self, test_runner):
        assert False, u'本来呼ばれることのないメソッド'

    @property
    def script(self):
        return "'''%s''' | file:write %s" % (self.content, self.path)

    def __invariant__(self):
        assert self.path is not None
        assert self.content is not None

    type = 'file'

class FitStorage(FitSection):
    def _build(self, node):
        FitSection._build(self, node)
        t = node.text.split(':', 1)[1].split(' ')
        self.schema = t[0].strip()
        self.name = t[1].strip() if len(t) == 2 else u''

    def add(self, node):
        if node.type == 'code' and not self.content:
            self.content = node.text
        n = self._node_maker.make(node)
        self._node_list.append(n)

    def accept(self, test_runner):
        assert False, u'本来呼ばれることのないメソッド'

    @property
    def script(self):
        return self._create_table() + '|' + self._insert()

    def _create_table(self):
        return 'strg:create-table %s %s' % (self.schema, self.name)

    def _insert(self):
        if self.content.startswith('#!tcsv\n'):
            return '%s | each {strg:insert %s} ' % (self._tcsv(), self.name)
        else:
            return '%s | strg:insert %s' % (self.content, self.name)
    
    def _tcsv(self):
        import csv
        from StringIO import StringIO
        _, body = self.content.split('#!tcsv\n')
        reader = csv.reader(StringIO(body))
        header = reader.next()
        r = []
        for line in reader:
            e = []
            for k, v in zip(header, line):
                e.append('"%s":%s' % (k, self._to_literal(v)))
            r.append('{%s}' % (','.join(e)))
        return '[%s]' % (', '.join(r))

    def _to_literal(v):
        from caty.util import try_parse
        from decimal import Decimal
        if v == 'true' or v == 'false':
            return v
        if try_parse(int, v):
            return v
        if try_parse(Decimal, v):
            return v
        return '"%s"' % (v)

    def __invariant__(self):
        assert self.name is not None
        assert self.schema

    type = 'storage'

