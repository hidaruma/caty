#coding: utf-8
u"""CatyFIT テストランナー。
テストランナーは CatyFIT ドキュメントのツリーを辿り、個々のエクスペクテーションを実行する。
CatyFIT ドキュメントのうち、 Caty インタープリタで実行するものは大きく分けると

* セットアップ
* ホーアトリプル

の二つに分けられる。

セットアップは文書の冒頭に並べて配置されており、
一つの CatyFIT 文書に複数のセットアップを格納できる。
セットアップは即座に実行されるわけではなく、のちのホーアトリプルと組み合わせて実行される。

ホーアトリプルは事前条件、本体、事後条件で構成され、
以下の条件のいずれかで成功とみなされる。

* 事前条件が成立しない
* 事前条件が成立し、本体が成功し、事後条件が成立する

事前条件が成立しない場合、本体は実行されない。
そのため、すべての事前条件のパターンを満たすように複数のセットアップを書く必要がある。

ホーアトリプルの実行に先立ってセットアップが実行される。
セットアップが複数ある場合、まず最初のセットアップが実行され、そしてホーアトリプルが実行される。
ホーアトリプルの実行時はまず事前条件の確認を行い、ついで本体のエクスペクテーションを実行し、
事後条件の確認を行い、最後に処理をロールバックして次のエクスペクテーションを実行する。
一通り終了したら次のセットアップで同一のホーアトリプルを実行、といった具合に実行されていき、最終的には

   セットアップ×トリプル

の数だけ実行が行われる。

"""
from caty.core.command import PipelineErrorExit, PipelineInterruption
from caty.core.script import COMMIT, ROLLBACK, PEND
from caty.core.exception import InternalException, CatyException
from caty.util import error_to_ustr
from caty.fit.behparser import parser
from caty.fit.document import make_document
from caty.fit.document.setup import NullSetup
from caty.core.facility import FacilitySet

class FitRunner(object):
    def __init__(self, fo, interpreter, force=False, no_dry_run=False, debug=False):
        self._title = u''
        self._fo = fo
        self._interpreter = interpreter
        self._nodes = []
        self._report_html = u''
        self._succ = 0 # 成功
        self._fail = 0 # 失敗
        self._error = 0 # 予期せぬ例外（Caty スクリプトの構文エラーなど）
        self._indef = 0 # 結果のチェックなし、目視必須
        self._invalid = 0 # CatyFIT 構文エラーなど
        self._setups = []
        self._triples = []
        self._error_msg = u''
        self._force = force
        self._no_dry_run = no_dry_run
        self._debug = debug
        self.original_session = self._interpreter.facilities['session']
        self.original_env = self._interpreter.facilities['env']
        tree = parser.run(self._fo.read())
        try:
            document = make_document(tree)
            document.accept(self)
        except Exception, e:
            import traceback
            traceback.print_exc()
            raise InternalException(u'Unexpected error while $path: $error', path=fo.path, error=error_to_ustr(e))

    def error_msg():
        def get(self):
            return self._error_msg
        def set(self, v):
            self._error_msg += v
            self._error += 1
        return get, set
    error_msg = property(*error_msg())

    @property
    def succ(self):
        return self._succ

    @property
    def fail(self):
        return self._fail

    @property
    def error(self):
        return self._error if not self.force else 0

    @property
    def invalid(self):
        return self._invalid

    @property
    def indef(self):
        return self._indef

    @property
    def report(self):
        # ここにどんだけ情報を詰めるかはまだ不確定
        return {
            "succ": self.succ,
            "fail": self.fail,
            "error": self.error,
            "invalid": self.invalid,
            "indef": self.indef,
            "total": self.succ + self.fail + self.error + self.invalid + self.indef,
            "html": self._report_html,
            "error_msg": self.error_msg,
            "title": self._title
        }

    @property
    def title(self):
        return self._title

    @property
    def path(self):
        return self._fo.path

    @property
    def force(self):
        return self._force

    @property
    def transaction(self):
        if self._no_dry_run:
            return COMMIT
        else:
            return PEND

    def set_title(self, title):
        self._title = title

    def add(self, node):
        self._nodes.append(node)
        if node.type == 'setup':
            self._setups.append(node)
        elif node.type == 'triple':
            self._triples.append(node)

    def run(self):
        if self._setups == []:
            self._setups = [NullSetup()]
        self._execute()
        r = []
        for n in self._nodes:
            r.append(n.to_html())
        self._report_html = ''.join(r)

    def _execute(self):
        expectations = [(s, t) for s in self._setups for t in self._triples]
        for s, t in expectations:
            try:
                self._execute_expectation(s, t)
            except Exception, e:
                if self.error_msg == u'':
                    import traceback
                    self.error_msg = ''.join([error_to_ustr(e),
                                              unicode(traceback.format_exc(), 'utf-8')])
            finally:
                self._exec_teardown(s)
                self._cleanup()
                if self.error_msg:
                    break

    def _execute_expectation(self, s, t):
        if not self._exec_setup(s):
            return
        succ = True
        t.precond.run(self)
        if t.precond.fail:
            self._fail += 1
            return
        if t.precond.indefined:
            self._indef += 1
            succ = False
        if t.precond.invalid:
            self._invalid += 1
            return
        t.body.run(self)
        if t.body.fail:
            self._fail += 1
            return
        if t.body.indefined:
            self._indef += 1
            succ = False

        if t.body.invalid:
            self._invalid += 1
            return
        t.postcond.run(self)
        if t.postcond.fail:
            self._fail += 1
            return
        if t.postcond.indefined:
            self._indef += 1
            succ = False
        if t.precond.invalid:
            self._invalid += 1
        else:
            if succ:
                self._succ += 1

    def _exec_setup(self, s):
        try:
            for script in s.scripts:
                cmd = self._interpreter.build(script, transaction=self.transaction)
                cmd(None)
            return True
        except Exception, e:
            import traceback
            self.error_msg = ''.join([error_to_ustr(e),
                                      unicode(traceback.format_exc(), 'utf-8')])
            return False

    def _exec_teardown(self, s):
        try:
            cmd = self._interpreter.build(s.teardown, transaction=self.transaction)
            cmd(None)
            return True
        except Exception, e:
            import traceback
            self.error_msg = ''.join([error_to_ustr(e),
                                      unicode(traceback.format_exc(), 'utf-8')])
            return False



    def _iter_while_no_error(self, iterable):
        for i in iterable:
            if not self.error_msg:
                yield i

    def _cleanup(self):
        cmd = self._interpreter.build('null', transaction=ROLLBACK)
        cmd(None)
        facilities = {}
        app = self._interpreter.facilities.app
        for k, v in self._interpreter.facilities.items():
            facilities[k] = v
        facilities['session'] = self.original_session
        facilities['env'] = self.original_env
        self._interpreter.facilities = FacilitySet(facilities, app)

    def make_testcase(self):
        return TestCase(self._interpreter, self)

    def include_file(self, path):
        if '@' in path:
            tp, path = path.split('@', 1)
            return self._interpreter.facilities[tp].open(path).read()
        else:
            return self._interpreter.facilities['pub'].open(path).read()


class TestCase(object):
    def __init__(self, interpreter, runner):
        self._interpreter = interpreter
        self.command = u''
        self.input = u''
        self.output = u''
        self.exception = None
        self.signal = None
        self.params = u''
        self.session = u'{}'
        self.sessionAfter = u'{}'
        self.setenv = u'{}'
        self.unsetenv = u'[]'
        self.outputCond = None
        self.orElse = []
        self.runner = runner

    def test(self, case, opts=[]):
        if not self._valid_expectation():
            case.invalid()
        try:
            session = self._interpreter.build(self.session or '{}', transaction=self.runner.transaction)(None)
            self._set_session(session)
            cmdline = self._build_command_line(self.setenv, self.unsetenv)
            cmd = self._interpreter.build(cmdline, transaction=self.runner.transaction)
        except Exception, e:
            if self.exception:
                case.ok()
                return
            if self.judge == 'suspend':
                return
            import traceback
            self.runner.error_msg = ''.join([error_to_ustr(e),
                                         unicode(traceback.format_exc(), 'utf-8')])
            case.error()
            return 

        if self.runner._debug:
            print self.input, '|', self.command, self.params
        try:
            from caty.jsontools import normalize
            i = self._interpreter.build(self.input, transaction=self.runner.transaction)
            result = normalize(cmd(i(None)))
            if self.output:
                self._compare(case, result, self.output, opts)
            elif self.outputCond:
                self._eval_cond(case, result)
            elif self.outputMatch and isinstance(result, dict):
                self._match_result(case, result)
            else:
                if not self.exception and not self.signal:
                    case.set_actual(result)
                else:
                    case.ng(result)
            return
        except (PipelineErrorExit, PipelineInterruption), e:
            if self.signal:
                self._compare(case, e.json_obj, self.signal)
            else:
                case.ng(e.json_obj)
            return
        except Exception, e:
            if self.exception:
                self._check_exception(case, e)
                return
            if self.judge != 'ignore':
                import traceback
                self.runner.error_msg = ''.join([error_to_ustr(e),
                                                 unicode(traceback.format_exc(), 'utf-8')])
            case.error()
            return

    def _set_session(self, session):
        from caty.util.collection import merge_dict
        from caty.session.value import SessionInfoWrapper, SessionInfo
        facilities = {}
        app = self._interpreter.facilities.app
        for k, v in self._interpreter.facilities.items():
            facilities[k] = v
        orig_s = facilities['session']._to_dict()
        storage = facilities['session'].storage
        new_s = merge_dict(orig_s['objects'], session)
        facilities['session'] = SessionInfoWrapper(SessionInfo(orig_s['key'], storage, default=new_s))
        self._interpreter.facilities = FacilitySet(facilities, app)

    def _compare(self, case, json, target, opts=[]):
        if target is None:
            self.runner.error_msg = u"比較対照が null です"
            case.error()
            return
        cmd = self._interpreter.build(target, transaction=self.runner.transaction)
        expected = cmd(None)
        if self._rec_comp(json, expected):
            case.ok()
            return
        else:
            if ('ig' in opts or'ignore-space' in opts) and isinstance(json, basestring) and isinstance(target, basestring):
                import re
                c = re.compile('\s')
                if self._rec_comp(c.sub('', json), c.sub('', expected)):
                    case.ok()
                    return
            if self.orElse:
                for e in self.orElse:
                    cmd = self._interpreter.build(e, transaction=self.runner.transaction)
                    expected = cmd(None)
                    if self._rec_comp(json, expected):
                        case.ok()
                        return

            case.ng(json)
            return

    def _rec_comp(self, a, b):
        import caty.jsontools as json
        from caty.template.core.context import StringWrapper
        if isinstance(a, StringWrapper):
            a = a.string
        if isinstance(b, StringWrapper):
            b = b.string
        if type(a) != type(b):
            return False
        if isinstance(a, list):
            if len(a) != len(b):
                return False
            for x, y in zip(a, b):
                if not self._rec_comp(x, y):
                    return False
        elif isinstance(a, dict):
            if len(a) != len(b):
                return False
            for x, y in zip(a, b):
                if not self._rec_comp(a[x], b[y]):
                    return False
        elif isinstance(a, json.TaggedValue):
            if a.tag != b.tag:
                return False
            return self._rec_comp(json.untagged(a), json.untagged(b))
        elif isinstance(a, json.TagOnly):
            if a.tag != b.tag:
                return False
        elif a != b:
            return False
        return True

    def _eval_cond(self, case, result):
        try:
            cond = self._interpreter.build(self.outputCond, transaction=self.runner.transaction)
            r = cond(result)
            if r == True:
                case.ok()
            else:
                case.ng(r)
                return
        except Exception, e:
            import traceback
            self.runner.error_msg = ''.join([error_to_ustr(e),
                                             unicode(traceback.format_exc(), 'utf-8')])
            case.error()
            return

    def _match_result(self, case, result):
        if not isinstance(result, dict):
            self.runner.error_msg = u"コマンドの結果が object ではありません"
            case.error()
        cmd = self._interpreter.build(self.outputMatch, transaction=self.runner.transaction)
        expected = cmd(None)
        if not isinstance(expected, dict):
            self.runner.error_msg = u"比較対象が object ではありません"
            case.error()
        if self._partial_match(result, expected):
            case.ok()
        else:
            case.ng(result)
        return

    def _partial_match(self, o1, o2):
        r = []
        for k, v in o2.items():
            if k not in o1:
                return False
            e = o1[k]
            if isinstance(e, dict) and isinstance(v, dict):
                r.append(self._partial_match(e, v))
            else:
                r.append(e == v)
        return all(r)

    def _valid_expectation(self):
        u"""output, outputCond, signal, exception は排他
        command は必須
        """
        return all([
            len(filter(lambda x: self._truth(x), [self.output, self.signal, self.exception, self.outputCond])) == 1,
            self._truth(self.command),
            ])

    def _truth(self, v):
        if v is None: return False
        if v.strip() == '': return False
        return True

    def _build_command_line(self, setenv, unsetenv):
        if setenv != u'{}' or unsetenv != u'[]':
            return u'[%s, pass, %s] | unclose {%s %s}' % (setenv, unsetenv, self.command, self.params)
        else:
            return u'%s %s' % (self.command, self.params)

    def _setup(self):
        return '[%s]' % (', '.join(self._prepare))

    def _check_exception(self, case, eobj):
        if isinstance(eobj, CatyException):
            if eobj.tag == self.exception:
                case.ok()
                return
        if self.exception == u'Exception':
            case.ok()
        else:
            case.ng(eobj)
                
            

    @property
    def force(self):
        return self.runner.force

