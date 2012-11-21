import os
import re
import sys
from optparse import OptionParser
from zipfile import ZipFile



def main(argv):
    o = OptionParser(usage='usage: python %s [OPTIONS] output' % argv[0])
    o.add_option('--project', action='store', default=None)
    o.add_option('--dest', action='store', default=None)
    o.add_option('--update', action='store_true')
    o.add_option('--dry-run', action='store_true', dest='dry_run')
    o.add_option('-q', '--quiet', action='store_true')
    options, args = o.parse_args(argv[1:])
    cai = CatyInstaller()
    cai.project = options.project
    cai.dest = options.dest
    cai.quiet = options.quiet
    cai.update = options.update
    cai.dry_run = options.dry_run
    if not args:
        print u'[Error]', u'missing archive file'
        o.print_help()
        sys.exit(1)
    cai.install(args[0])

class CatyInstaller(object):
    def install(self, path):
        zp = ZipFile(open(path))
        files = zp.infolist()
        self.__memo = set()
        if not self.project:
            base_dir = self.dest
        else:
            base_dir = os.path.join(self.project.rstrip(os.path.sep), 'main', self.dest)
        if not os.path.exists(base_dir):
            if self.dry_run:
                print base_dir
            else:
                os.mkdir(base_dir)
        for file in files:
            self._make_dir(file.filename, base_dir)
            if self._not_modified(file, base_dir):
                continue
            if self.dry_run:
                print file.filename
            else:
                open(os.path.join(base_dir, file.filename), 'wb').write(zp.read(file.filename))

    def _make_dir(self, filename, base_dir):
        chunk = filename.split(os.path.sep)[:-1]
        target = base_dir
        for c in chunk:
            target = os.path.join(target, c)
            if not os.path.exists(target):
                if self.dry_run:
                    if target not in self.__memo:
                        print target
                        self.__memo.add(target)
                else:
                    os.mkdir(target)

    def _not_modified(self, file, base_dir):
        import datetime
        import time
        if not self.update:
            return False
        target = os.path.join(base_dir, file.filename)
        if not os.path.exists(target):
            return False
        desttime = os.stat(target).st_mtime
        srctime = time.mktime(datetime.datetime(*file.date_time).timetuple())
        return desttime > srctime

if __name__ == '__main__':
    main(sys.argv)
