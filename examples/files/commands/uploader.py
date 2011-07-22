#coding: utf-8
from caty.core.command import Command
from uuid import uuid4

class Upload(Command):
    def execute(self, input):
        dirname = '/' + self.user.userid + '/'
        obj = input['file']
        if not self.pub.opendir(dirname).exists:
            self.pub.opendir(dirname).create()
        if input.get('use_auto_gen', None):
            name = u'%s%s.%s' % (dirname, unicode(uuid4()), obj['filename'].rsplit('.', -1)[-1])
        elif input.get('filename', None):
            name = dirname + input['filename']
        else:
            name = dirname + obj['filename']
        if not '.' in name:
            return u'無拡張子のファイルには対応しておりません'
        f = self.pub.open(name, 'wb')
        f.write(obj['data'])
        f.close()
        return u'%s をアップロード完了' % (name)

class ListFiles(Command):
    def execute(self):
        dirname = '/' + self.user.userid + '/'
        if not self.pub.opendir(dirname).exists:
            return []
        else:
            r = []
            for e in self.pub.opendir(dirname).read():
                r.append({
                    "filename": e.basename,
                    "link": e.path,
                    "updated": unicode(e.last_modified)
                })
            return r
