#coding: utf-8
from caty.core.command import Builtin, Internal
from caty.core.handler import AppDispatcher, RequestHandler
from caty.fit.runner import FitRunner
from caty.jsontools import stdjson as json
name = u'fit'
schema = u"""
"""
import caty
from caty.command import MafsMixin
class Run(Internal, MafsMixin):

    def setup(self, opts, path=None):
        self._path = path.strip() if path else path
        self._verbose = opts.get('verbose', caty.UNDEFINED)
        self._force = opts.get('force', caty.UNDEFINED)
        self._no_dry_run = opts.get('no-dry-run', caty.UNDEFINED)
        self._debug = opts.get('debug', caty.UNDEFINED)
        self._ext = opts.get('ext', '.beh')
        self._out_dir = opts.get('outdir')
        self._out_file = opts.get('out')
        if not self._ext.startswith('.'):
            self._ext = '.' + self._ext
        if not path:
            self._all = opts.get('all-apps', caty.UNDEFINED)
        else:
            self._all = False

    def execute(self):
        if self._path:
            if self._path[-1] in ('/', '*'):
                results = []
                p, place = self.parse_canonical_path(self._path.strip('*'), default='behaviors')
                d = place.opendir(p)
                for e in d.read(True):
                    if e.path.endswith(self._ext):
                        results.append(self._test(place.open(e.path)))
            else:
                results = [self._test(self.open(self._path, default='behaviors'))]
        else:
            if self._all:
                return self.run_all()
            results = []
            tests = self._list_test()
            for e in tests:
                results.append(self._test(e))
        for r in results: 
            # テストが終わる度にロールバックが行われるので、
            # 結果の書き込みは最後にまとめて行う
            r(self)

    def _list_test(self):
        d = self.opendir('/', default='behaviors')
        r = []
        for e in d.read(True):
            if e.path.endswith(self._ext):
                r.append(e)
        return r

    def _test(self, fo):
        if self._verbose:
            self.stream.write(u'%s を実行しています...\n' % fo.path)
        runner = FitRunner(fo, self.interpreter.clone(), self._force, self._no_dry_run, self._debug)
        runner.run()
        report = runner.report
        #report['tests'] = self._list_summary(self.opendir('/'))
        report['app'] = self._get_app_name()
        path = fo.path
        def _(o):
            if o._verbose:
                o.stream.write(u'%s の結果を書き込んでいます...\n' % path)
            o._create_target_dir(path)
            o._write_result(report, path)
        return _

    def _create_target_dir(self, path):
        if not self._out_dir:
            app = self._get_app_name()
            base_dir = 'fit-view:/%s' % app
            l = path.split('/')[:-1]
            dirs = ['/'.join(l[:i+1]) for i in range(len(l))]
            for d in dirs:
                target = self.pub.opendir(base_dir+d)
                if not target.exists:
                    target.create()

    def _write_result(self, result, path):
        app = self._get_app_name()
        if self._out_file:
            path = self._out_file
        elif self._out_dir:
            path = '%s%s' % (self._out_dir, path.rsplit('.', 1)[0] + '.fit')
        else:
            _path = 'pub@fit-view:/%s%s' % (app, path.rsplit('.', 1)[0] + '.fit')
            if self._path:
                _p, opener = self.parse_canonical_path(self._path, 'behaviors')
                if opener != self.behaviors:
                    _path = path
            path = _path
        f = self.open(path, 'wb', default='behaviors')
        json.dump(result, f)
        f.close()

    def _get_app_name(self):
        return self.env.get('CATY_APP')['name']

    def _list_summary(self, d):
        r = []
        for e in d.read(False):
            if e.is_dir:
                r.append({
                    'subdir': e.path,
                    'context': None,
                    'child_nodes': self._list_summary(e)
                    })
            else:
                if not e.path.endswith('.beh'): continue
                r.append({
                    'context': self._summary(e),
                    'child_nodes': []
                })
        return r
    
    def _summary(self, t):
        runner = FitRunner(t, self.interpreter.clone())
        return {
            'path': t.path.replace('.beh', '.fit'),
            'title': runner.title,
            'app': self._get_app_name()
        }

    def run_all(self):
        apps = self.current_app._system._apps
        for app in apps:
            self._run(app)

    def _run(self, app):
        import caty
        dispatcher = AppDispatcher(self._system)
        app = dispatcher.dispatch(app.web_path)
        f = app.create_facilities(lambda: self._facilities['session'])
        app.init_env(f, caty.DEBUG, ['console'], self._system, {})
        i = f['interpreter'] 
        if self._verbose:
            print u'* %sのFITを実行します' % app.name
            cmd = i.build('fit:run --verbose')
        else:
            cmd = i.build('fit:run')
        cmd(None)


class List(Builtin):

    def execute(self):
        d = self.behaviors.opendir('/')
        r = []
        for e in d.read(True):
            try:
                if e.path.endswith('.beh'):
                    runner = FitRunner(e, self.interpreter.clone())
                    self.stream.write('%s: %s\n' % (runner.path, runner.title))
            except:
                self.stream.write('ERROR: %s\n' % e.path)
                raise

class ClearReport(Internal):

    def setup(self, opts, dir_or_file=None):
        self.__all = opts.get('all', caty.UNDEFINED)
        self.__path = dir_or_file
        self.__all_apps = opts.get('all-apps', caty.UNDEFINED)

    def execute(self):
        app = self.env.get('CATY_APP')['name']
        if self.__all_apps:
            self.run_all()
        elif self.__path:
            path = 'fit-view:/%s/%s' % (app, self.__path.replace('.beh', '.fit'))
            if self.pub.is_dir(self.__path):
                d = self.pub.opendir(path)
                if self.__all:
                    d.delete(True)
                else:
                    self._delete_garbage()
            else:
                f = self.pub.open(path)
                f.delete()
        else:
            d = self.pub.opendir('fit-view:/%s' % app)
            if self.__all:
                if d.exists:
                    d.delete(True)
            else:
                self._delete_garbage()

    def _delete_garbage(self):
        from caty.core.exception import FileNotFound
        app = self.env.get('CATY_APP')['name']
        if self.__path:
            beh_dir = self.behaviors.opendir(self.__path)
            fit_dir = self.pub.opendir('fit-view:/%s%s' % (app, self.__path))
        else:
            beh_dir = self.behaviors.opendir('/')
            fit_dir = self.pub.opendir('fit-view:/%s' % app)
        if not fit_dir.exists:
            return
        if not beh_dir.exists:
            fit_dir.delete()
            return
        for e in beh_dir.read(True):
            if e.path.endswith('.beh'):
                b = self.behaviors.open(e.path)
                f = self.pub.open('fit-view:/%s%s' % (app, e.path.replace('.beh', '.fit')))
                if f.exists and f.last_modified < b.last_modified:
                    f.delete()
        delcount = 0
        fitcount = 0
        for e in fit_dir.read(True):
            if e.path.endswith('.fit'):
                fitcount += 1
                try:
                    b = self.behaviors.open(e.path.replace('/'+app + '/', '/').replace('.fit', '.beh'))
                    f = self.pub.open('fit-view:/%s%s' % (app, e.path.replace('/'+app, '')))
                    if not b.exists:
                        f.delete()
                        delcount += 1
                except FileNotFound, e:
                    f.delete()
                    delcount += 1
        if delcount == fitcount and delcount != 0:
            fit_dir.delete(True)

    def run_all(self):
        apps = self.current_app._system._apps
        for app in apps:
            self._run(app)

    def _run(self, app):
        import caty
        dispatcher = AppDispatcher(self._system)
        app = dispatcher.dispatch(app.web_path)
        f = app.create_facilities(lambda: self._facilities['session'])
        app.init_env(f, caty.DEBUG, ['console'], self._system, {})
        i = f['interpreter'] 
        if self.__all:
            cmd = i.build('fit:clean --all')
        else:
            cmd = i.build('fit:clean')
        cmd(None)

class SendReport(Builtin):

    def setup(self, opts):
        self._all = opts.get('all', caty.UNDEFINED)

    def execute(self):
        report = self._collect_report()
        self._send_report(report)

    def _collect_report(self):
        apps = {}
        if not self._all:
            d = self.pub.opendir(u'fit-view:/%s/' % self.env.get('CATY_APP')['name'])
            if not d.exists:
                print u'%sのCatyFITは実行されていません' % self.env.get('CATY_APP')['name']
                return 
        else:
            d = self.pub.opendir(u'fit-view:/')
        for e in d.read(True):
            if not e.path.endswith('.fit'): continue
            o = self.pub.open('fit-view:'+e.path).read()
            j = json.loads(o)
            if j['total'] != j['succ']:
                _, app, name = e.path.split('/', 2)
                if app not in apps:
                    apps[app] = [
                            {'path': u'/' + name, 'result': j}
                        ]
                else:
                    apps[app].append({'path': u'/' + name, 'result': j})

        return apps

    def _send_report(self, col):
        if not col: return
        s = self._format_report(col)
        print s

    def _format_report(self, col):
        s = []
        for app_name, app_result in col.items():
            s.append(app_name+':')
            for v in app_result:
                r = v['result']
                s.append('  %s:%s' % (r['title'], v['path']))
                s.append('    OK: %d' % (r['succ']))
                s.append('    NG: %d' % (r.get('fail', 0)))
                s.append('    Indef: %d' % (r.get('indef', 0)))
                s.append('    Error: %d' % (r.get('error', 0)))
                s.append('    Invalid: %d' % (r.get('invalid',0 )))
                m = r['error_msg']
                if m:
                    s.append('    Error Message:')
                    for l in m.split('\n'):
                        s.append('      '+l)
                s.append('\n')
        return '\n'.join(s).strip()

