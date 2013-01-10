#coding: utf-8
from caty.command import Command
import caty.jsontools as json

class ListAllResult(Command):
    def execute(self):
        d = self.pub.opendir('fit-view:/')
        r = []
        for e in d.read(False):
            if e.is_dir:
                r.append({
                    'name': e.path.split('/')[1],
                    'contents':self._list_summary(e),
                    })
        return r

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
                if not e.path.endswith('.fit'): continue
                if e.path.endswith('/index.fit'): continue
                r.append({
                    'context': self._summary(e),
                    'child_nodes': []
                })
        return r
 
    def _summary(self, t):
        import re
        f = self.pub.open(t.path)
        j = json.load(f)
        return {
            'path': f.path,
            'title': j['title'],
            'result': u'succ' if j['fail'] == 0 and j['error'] == 0 and j['invalid'] == 0 else u'fail',
            'app': f.path.split('/')[1]
        }

class Read(ListAllResult):
    def setup(self, path):
        self.__path = path

    def execute(self):
        f = self.pub.open(self.__path)
        r = json.load(f)
        app_dir = u'/%s/' % f.path.split('/')[1]
        r['tests'] = self._list_summary(self.pub.opendir(app_dir))
        return r


