import os
import re
import sys
from optparse import OptionParser
from zipfile import ZipFile, ZIP_DEFLATED
import locale
import shutil
import time
import datetime
import codecs
import hashlib
cout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)

def main(argv):
    o = OptionParser(usage='usage: python %s [OPTIONS] output' % argv[0])
    o.add_option('--dry-run', action='store_true', dest='dry_run')
    options, args = o.parse_args(argv[1:])
    cau = CatyUninstaller()
    cau.dry_run = options.dry_run
    if not args:
        print >>cout, u'[Error]', u'missing archive file'
        o.print_help()
        sys.exit(1)
    cau.uninstall(args[0])

class CatyUninstaller(object):
    def uninstall(self, log_file):
        log = open(log_file).read().replace('\r\n', '\n').replace('\r', '\n')
        self._log_buffer = []
        try:
            header, records = self._parse_log(log)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print '[Error] Invalid log format'
            sys.exit(1)
        log_contents = []
        for rec in records:
            if rec.result == '+':
                if os.path.exists(rec.destfile):
                    rec.result = '-'
                    if self._modified(rec):
                        rec.msg = 'modified'
                    if not self.dry_run:
                        os.unlink(rec.destfile)
                else:
                    if not self.dry_run:
                        rec.msg = 'missing'
                        rec.result = '*'
            elif rec.result == '*':
                rec.msg = 'ignore'
            else:
                if os.path.exists(rec.destfile):
                    if os.path.exists(rec.bkfile):
                        rec.result = '-'
                        if self._modified(rec):
                            rec.msg = 'modified ' + rec.bkfile.rsplit('.', 1)[0] + '.chg'
                            if not self.dry_run:
                                shutil.copyfile(rec.destfile, rec.bkfile.rsplit('.', 1)[0] + '.chg')
                        if not self.dry_run:
                            shutil.copyfile(rec.bkfile, rec.destfile)
                            os.unlink(rec.bkfile)
                    else:
                        rec.result = '-'
                        if self._modified(rec):
                            rec.msg = 'modified&backup-missing ' + rec.bkfile.rsplit('.', 1)[0] + '.chg'
                            if not self.dry_run:
                                shutil.copyfile(rec.destfile, rec.bkfile.rsplit('.', 1)[0] + '.chg')
                        else:
                            rec.msg = 'backup-missing'
                        os.unlink(rec.destfile)
                else:
                    rec.result = '*'
                    rec.msg = 'missing'
                    if os.path.exists(rec.bkfile):
                        if not self.dry_run:
                            shutil.copyfile(rec.bkfile, rec.destfile)
                    else:
                        rec.msg = 'missing&backup-missing'

            if not self.dry_run:
                log_contents.append(rec.to_str())
            else:
                print >>cout, rec.result, rec.destfile, rec.msg.split(' ')[0]
        self.end_time = time.localtime()
        if not self.dry_run:
            self._flush_log(log_file, header, log_contents)

    def _parse_log(self, log_data):
        chunk = log_data.split('\n\n')
        if len(chunk) != 2:
            raise Exception('invalid data')
        return self._parse_header(chunk[0]), self._parse_contents(chunk[1])

    def _parse_header(self, data):
        r = {}
        for l in data.split('\n'):
            name, val = l.split(':', 1)
            r[name.strip()] = val.strip()
        return r

    def _parse_contents(self, data):
        r = []
        for l in data.split('\n'):
            if l:
                chunk = l.split('|')
                r.append(LogRecord(*chunk))
        return r

    def _flush_log(self, install_log_name, header, contents):
        self._log_buffer.append('Operation: uninstall\n')
        for h in ['Local-Timestamp', 'Project-Dir', 'Destination-Dir', 'Destination-Name', 'Backup-Dir']:
            if h in header:
                self._log_buffer.append('%s: %s\n' % (h, header[h]))
        self._log_buffer.append('Uninstall-Backup-Suffix: %s\n' % (header['Backup-Suffix'].rsplit('.', 1)[0] + '.chg'))
        self._log_buffer.append(u'Date: %s:%s\n' % (time.strftime('%Y-%m-%dT%H:%M:%S', self.end_time), tz_to_str(time.timezone)))
        self._log_buffer.append('\n')
        for c in contents:
            self._log_buffer.append(c + '\n')
        with open(install_log_name.replace('install.log', 'uninstall.log'), 'wb') as logfile:
            logwriter = codecs.getwriter(locale.getpreferredencoding())(logfile)
            for l in self._log_buffer:
                logwriter.write(l) 

    def _modified(self, rec):
        if not os.path.exists(rec.destfile):
            return True
        md5 = hashlib.md5()
        md5.update(open(rec.destfile, 'rb').read())
        digest = md5.hexdigest()
        return digest != rec.md5

class LogRecord(object):
    def __init__(self, arcfile, size, date, md5, destfile, result, msg, bkfile=None):
        self.arcfile = arcfile
        self.size = size
        self.date = date
        self.md5 = md5
        self.destfile = destfile
        self.result = result
        self.msg = msg
        self.bkfile = bkfile

    def to_str(self):
        return '|'.join([self.arcfile, self.size, self.date, self.md5, self.destfile, self.result, self.msg])

def tz_to_str(t):
    return '%+05d' % (-t/(60*60.0) * 100)

if __name__ == '__main__':
    main(sys.argv)