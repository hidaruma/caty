import os
import re
import sys
from optparse import OptionParser
from zipfile import ZipFile, ZIP_DEFLATED
import locale
import codecs
import time
import hashlib
import shutil
import datetime
cout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)

def normalize_path(path):
    if sys.platform == 'win32':
        return path.replace('/', '\\')
    return path

def main(argv):
    o = OptionParser(usage='usage: python %s [OPTIONS] output' % argv[0])
    o.add_option('--project', action='store', default=None)
    o.add_option('--dest', action='store', default='project')
    o.add_option('--update', action='store_true')
    o.add_option('--compare', choices=['digest', 'timestamp'], default='digest')
    o.add_option('--dry-run', action='store_true', dest='dry_run')
    o.add_option('--log', action='store', default=None)
    o.add_option('--no-md5', action='store_true', dest='no_md5')
    o.add_option('-q', '--quiet', action='store_true')
    options, args = o.parse_args(argv[1:])
    cai = CatyInstaller()
    cai.project = options.project
    cai.dest = options.dest
    cai.quiet = options.quiet
    cai.update = options.update
    cai.dry_run = options.dry_run
    cai.log = options.log
    cai.compare = options.compare
    cai.no_md5 = options.no_md5
    if not args:
        print >>cout, u'[Error]', u'missing archive file'
        o.print_help()
        sys.exit(1)
    cai.install(args[0])


class CatyInstaller(object):
    def install(self, path):
        bksuffix = time.strftime('%Y%m%d%H%M%S')+'.bak'
        self.bksuffix = bksuffix
        zp = ZipFile(open(path, 'rb'))
        files = zp.infolist()
        self.__memo = set()
        if not self.project:
            base_dir = self.dest
        elif self.dest == 'project':
            base_dir = self.project.rstrip(os.path.sep)
        else:
            base_dir = os.path.join(self.project.rstrip(os.path.sep), 'main', self.dest)
        if not os.path.exists(base_dir):
            if self.dry_run:
                print >>cout, base_dir
            else:
                os.mkdir(base_dir)
        if self.log:
            self._init_log()
        log_contents = []
        pkg = None
        for file in files:
            if file.filename == 'META-INF/package.json':
                if pkg:
                    p = zp.read(file.filename)
                    if p != pkg:
                        print '[Error]', 'confliction between /package.json and /META-INF/package.json'
                    else:
                        pkg = p
                continue
            if file.filename.startswith('META-INF/'):
                continue
            if file.filename == 'package.json':
                if pkg:
                    p = zp.read(file.filename)
                    if p != pkg:
                        print '[Error]', 'confliction between /package.json and /META-INF/package.json'
                    else:
                        pkg = p
                continue
            self._make_dir(normalize_path(file.filename), base_dir)
            if self._not_modified(file, base_dir):
                mode = '*'
                digest = ''
                destfile = ''
            elif self.dry_run:
                print >>cout, normalize_path(file.filename)
                continue
            else:
                c = zp.read(file.filename)
                destfile = os.path.join(base_dir, normalize_path(file.filename))
                mode = '+'
                if os.path.exists(destfile):
                    shutil.copyfile(destfile, destfile+'.' + bksuffix)
                    mode = '!'
                open(destfile, 'wb').write(c)
                if not self.no_md5:
                    md5 = hashlib.md5()
                    md5.update(c)
                    digest = md5.hexdigest()
            log_contents.append((file, os.path.abspath(destfile), digest, mode))
        if self.log:
            self._write_header(path, base_dir, bksuffix)
        if self.log:
            self._write_file(log_contents)
            if not self.dry_run:
                self.logfile.close()

    def _init_log(self):
        if self.dry_run:
            return
        self.logfile = open(self.log, 'wb')
        self.logwriter = codecs.getwriter(locale.getpreferredencoding())(self.logfile)

    def _write_header(self, path, base_dir, bksuffix):
        if self.dry_run:
            return
        self.logwriter.write(u'Operation: install\n')
        self.logwriter.write(u'Dist-Package-Name: %s\n' % os.path.basename(path).rsplit('.', 1)[0])
        if self.project:
            self.logwriter.write(u'Project-Dir: %s\n' % os.path.abspath(self.project))

        if self.project:
            self.logwriter.write(u'Destination-Dir: %s\n' % os.path.abspath(base_dir))
            if self.dest:
                self.logwriter.write(u'Destination-Name: %s\n' % self.dest)
        self.logwriter.write(u'Backup-Suffix: .%s\n' % bksuffix)
        self.logwriter.write(u'Installed-Date: %s\n' % time.strftime('%Y-%m-%dT%H:%M:%S'))
        self.logwriter.write('\n')

    def _write_file(self, log_contents):
        if self.dry_run:
            return
        for l in log_contents:
            c = ['/' + l[0].filename, str(l[0].file_size), time.strftime('%Y-%m-%dT%H:%M:%S', datetime.datetime(*l[0].date_time).timetuple()), l[2], l[1], l[3], '']
            if l[3] == '!':
                c[-1] = l[1] + self.bksuffix
            self.logwriter.write(u'|'.join(c)+u'\n')

    def _make_dir(self, filename, base_dir):
        chunk = filename.split(os.path.sep)[:-1]
        target = base_dir
        for c in chunk:
            target = os.path.join(target, c)
            if not os.path.exists(target):
                if self.dry_run:
                    if target not in self.__memo:
                        print >>cout, target
                        self.__memo.add(target)
                else:
                    os.mkdir(target)

    def _not_modified(self, file, base_dir):
        import binascii
        if not self.update:
            return False
        target = os.path.join(base_dir, normalize_path(file.filename))
        if not os.path.exists(target):
            return False
        if self.compare == 'timestamp':
            desttime = os.stat(target).st_mtime
            srctime = time.mktime(datetime.datetime(*file.date_time).timetuple())
            return desttime > srctime
        else:
            return file.CRC == (binascii.crc32(open(target).read()) & 0xffffffff)

if __name__ == '__main__':
    main(sys.argv)
