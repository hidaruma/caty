#coding:utf-8
from caty.fit.document.base import *
from caty.fit.document.literal import *
from caty.fit.document.section import *
from caty.fit.behparser import HeaderCell, DataCell
from caty.jsontools import pp
from caty.util import escape_html
import caty.core.runtimeobject as ro
from pbc import *

class FitTriple(FitNode):
    def __init__(self, precond, body, postcond, node_maker):
        self._precond = precond
        self._body = body
        self._postcond = postcond
        FitNode.__init__(self, None, node_maker)

    def _build(self, ignore):
        u"""FitTriple は preCond, exec, postCond の組で構成される。
        そのため、普通の _build メソッドでの構築は行われない
        """
        pass

    @property
    def precond(self):
        return self._precond if self._precond else EmptyExpectation()

    @property
    def body(self):
        return self._body

    @property
    def postcond(self):
        return self._postcond if self._postcond else EmptyExpectation()

    def accept(self, test_runner):
        test_runner.add(self)

    def apply_macro(self, macro):
        if self._precond: self._precond.apply_macro(macro)
        self._body.apply_macro(macro)
        if self._postcond: self._postcond.apply_macro(macro)

    def to_html(self):
        return '\n'.join([
            self._precond.to_html() if self._precond else u'',
            self._body.to_html(),
            self._postcond.to_html() if self._postcond else u''])
    type = 'triple'

class FitExpectation(FitSection):
    def __iter__(self):
        for n in self._node_list:
            if isinstance(n, FitMatrix):
                for c in n.cases:
                    yield c
    
    def add(self, node):
        if node.type == 'table':
            self._node_list.append(self._node_maker.make_matrix(node))
        else:
            self._node_list.append(self._node_maker.make(node))

    def run(self, runner):
        for i in self._node_list:
            if isinstance(i, FitMatrix):
                i.run(runner)

    @property
    def fail(self):
        return any([x.fail for x in self._node_list if isinstance(x, FitMatrix)])
    
    @property
    def indefined(self):
        return any([x.indefined for x in self._node_list if isinstance(x, FitMatrix)])

    @property
    def invalid(self):
        return any([x.invalid for x in self._node_list if isinstance(x, FitMatrix)])

class FitPreCond(FitExpectation):
    type = 'preCond'

class FitExec(FitExpectation):
    type = 'exec'

class FitPostCond(FitExpectation):
    type = 'postCond'

class EmptyExpectation(object):
    def __iter__(self):
        return iter([])

    def run(self, runner):
        pass

    fail = False
    error = False
    indefined = False
    invalid = False

class FitMatrix(FitTable):
    def __init__(self, node, node_maker, command_section=None):
        FitTable.__init__(self, node, node_maker)
        self.command_section = command_section

    def _build(self, node):
        FitTable._build(self, node)
        if not self.items[0].is_title_row:
            raise FitDocumentError(ro.i18n.get(u"Title line must described as header cell: Line $line", line=node.lineno))

    def apply_macro(self, macro):
        for n in self.items:
            n.apply_macro(macro)

    def accept(self, test_runner):
        self.runner.add(self)

    def row_maker(self, node):
        if all(map(lambda x:x.type=='header-cell', node.items)):
            return FitExpectationType(node, self._node_maker)
        else:
            return FitCase(node, self._node_maker)

    def run(self, runner):
        if not self.items: return
        title_row = self.items[0]
        cases = self.items[1:]
        for c in cases:
            try:
                c.set_column_type(title_row)
            except:
                c.invalid()
                break
            c.run(runner)
        else:
            if any(map(lambda c: c.actual_added, cases)):
                title_row.add_actual_header()

    @property
    def fail(self):
        return any(map(lambda x: x.succeed == False, self.items[1:]))

    @property
    def indefined(self):
        return any(map(lambda x: x.succeed is None, self.items[1:]))

    @property
    def invalid(self):
        return any(map(lambda x: x.succeed is INVALID, self.items[1:]))

    @property
    def cases(self):
        return self.items[1:]

CELL_TYPES = set(['command', 
                  'input', 
                  'output', 
                  'exception', 
                  'signal', 
                  'params', 
                  'session', 
                  'sessionafter',
                  'outputcond',
                  'outputmatch',
                  'env',
                  'judge'
              ])

class FitExpectationType(FitRow):
    def cell(self, node):
        r = FitRow.cell(self, node)
        t = node.text.strip(' ').lower()
        if t.startswith('!') and t.strip('!') not in CELL_TYPES:
            r.text = ro.i18n.get(u'Unknown directive: $type', type=t)
            r.style = u'syntactic_error'
            r.error = True
            self.error = True
        else:
            r.error = False
            self.error = False
        return r

    @property
    def output_opts(self):
        n = self.output_num
        if n != -1:
            opts = self.items[n].text.strip().split('output', 1)[1].strip('()')
            return opts.split(',')
        return []

    @property
    def command_num(self):
        return self._find_cell('command')

    @property
    def input_num(self):
        return self._find_cell('input')

    @property
    def output_num(self):
        return self._find_cell('output')

    @property
    def exception_num(self):
        return self._find_cell('exception')

    @property
    def signal_num(self):
        return self._find_cell('signal')

    @property
    def params_num(self):
        return self._find_cell('params')

    @property
    def session_num(self):
        return self._find_cell('session')

    @property
    def sessionAfter_num(self):
        return self._find_cell('sessionafter')

    @property
    def outputCond_num(self):
        return self._find_cell('outputcond')

    @property
    def outputMatch_num(self):
        return self._find_cell('outputmatch')

    @property
    def env_num(self):
        return self._find_cell('env')

    @property
    def judge_num(self):
        return self._find_cell('judge')

    @property
    def orElse_nums(self):
        r = []
        for i, cell in enumerate(self.items):
            t = cell.text.strip(' !').lower()
            if t == 'orelse':
                r.append(i)
        return r

    def _find_cell(self, s):
        import re
        for i, cell in enumerate(self.items):
            t = cell.text.strip(' !').lower()
            if t == s:
                return i
            if s == 'output' and re.sub('\s', '', t).startswith('output('):
                return i
        return -1

    def add_actual_header(self):
        self.items.append(self.cell(HeaderCell('actual', 0)))

    def to_html(self):
        return u'<tr class="fit_case_header">%s</tr>' % (''.join([c.to_html() for c in self.items]))

class FitCase(FitRow):
    def __init__(self, *args ,**kwds):
        FitRow.__init__(self, *args, **kwds)
        self._command = u''
        self.result = u'NotYet'
        self.initialized = False
        self.has_no_judge_col = False

    def apply_macro(self, macro):
        for n in self.items:
            n.apply_macro(macro)

    def set_column_type(self, title_row):
        if title_row.error:
            raise Exception('syntactic error')
        self.command_num = title_row.command_num
        self.input_num = title_row.input_num
        self.output_num = title_row.output_num
        self.output_opts = title_row.output_opts
        self.exception_num = title_row.exception_num
        self.signal_num = title_row.signal_num
        self.params_num = title_row.params_num
        self.env_num = title_row.env_num
        self.session_num = title_row.session_num
        self.sessionAfter_num = title_row.sessionAfter_num
        self.outputCond_num = title_row.outputCond_num
        self.outputMatch_num = title_row.outputMatch_num
        self.orElse_nums = title_row.orElse_nums
        self.judge_num = title_row.judge_num
        self.initialized = True
        self.actual_added = False
        self.has_no_judge_col = title_row.judge_num != -1 and len(self.items) < len(title_row.items)

    def run(self, test_runner):
        assert self.initialized, FitRow.to_html(self)
        try:
            testcase = test_runner.make_testcase()
            testcase.command = self.command
            testcase.input = self.input
            testcase.output = self.output
            testcase.exception = self.exception
            testcase.signal = self.signal
            testcase.params = self.params
            testcase.session = self.session
            testcase.sessionAfter = self.sessionAfter
            testcase.env = self.env
            testcase.outputCond = self.outputCond
            testcase.outputMatch = self.outputMatch
            testcase.orElse = self.orElse
            testcase.judge = self.judge
        except:
            if self.judge == 'suspend':
                self.result = 'Indef'
                return
            self.result = 'Inval'
        else:
            testcase.test(self, self.output_opts)
            if self.judge == 'suspend':
                self.result = 'Indef'
                return
            if self.result == 'Error' and not test_runner.force and not self.judge == 'ignore':
                raise RuntimeError('エラーを検出')

    def ok(self):
        self.result = 'OK'

    def error(self):
        self.result = 'Error'

    def invalid(self):
        self.result = 'Inval'

    def ng(self, actual):
        self.result = 'NG'
        self.items.append(self.cell(DataCell(pp(actual), 0)))
        self.actual_added = True

    def set_actual(self, actual):
        self.result = 'OK'
        self.items.append(self.cell(DataCell(pp(actual), 0)))
        self.actual_added = True

    def command():
        def _get(self):
            if self._command:
                return self._command
            else:
                if self.command_num != -1:
                    return self[self.command_num].text
                else:
                    return u''
        def _set(self, value):
            self._command = value

        return _get, _set
    command = property(*command())

    @property
    def input(self):
        if self.input_num != -1:
            i = self[self.input_num].text
            if i.strip() == '':
                return 'null'
            else:
                return i
        else:
            return 'null'


    @property
    def output(self):
        if self.output_num != -1:
            return self[self.output_num].text
        else:
            return None

    @property
    def exception(self):
        if self.exception_num != -1:
            return self[self.exception_num].text
        else:
            return None

    @property
    def signal(self):
        if self.signal_num != -1:
            return self[self.signal_num].text
        else:
            return None

    @property
    def params(self):
        if self.params_num != -1:
            return self[self.params_num].text
        else:
            return ''

    @property
    def session(self):
        if self.session_num != -1:
            return self[self.session_num].text
        else:
            return '{}'

    @property
    def sessionAfter(self):
        if self.sessionAfter_num != -1:
            return self[self.sessionAfter_num].text
        else:
            return '{}'

    @property
    def outputCond(self):
        if self.outputCond_num != -1:
            o = self[self.outputCond_num].text
            if o.strip() == '':
                return 'true'
            else:
                return o
        else:
            return None

    @property
    def outputMatch(self):
        if self.outputMatch_num != -1:
            o = self[self.outputMatch_num].text
            if o.strip() == '':
                return '{}'
            else:
                return o
        else:
            return None

    @property
    def orElse(self):
        if self.orElse_nums:
            r = []
            for i in self.orElse_nums:
                r.append(self[i].text)
            return r
        else:
            return []

    @property
    def env(self):
        if self.env_num != -1:
            return self[self.env_num].text
        else:
            return '{}'

    @property
    def judge(self):
        if self.judge_num != -1 and not self.has_no_judge_col:
            return self[self.judge_num].text.lower()
        else:
            return ''

    def to_html(self):
        return u'<tr class="%s">%s</tr>' % (self.result, (''.join([c.to_html() for c in self.items])))

    @property
    def succeed(self):
        if self.result == 'Inval':
            return INVALID
        assert self.judge in ('', 'negate', 'ignore', 'accept', 'suspend'), ro.i18n.get(u'judge column must be one of negate/ignore/accept/suspend or blank: $actual', actual=self.judge)
        if self.judge == '' or self.judge == 'accept':
            return self.result in ('OK', 'NotYet')
        elif self.judge == 'negate':
            return self.result not in ('OK', 'NotYet')
        elif self.judge == 'ignore':
            return True
        elif self.judge == 'suspend':
            return None

INVALID = 3

