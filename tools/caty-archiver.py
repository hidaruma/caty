import os
import re
import sys
from optparse import OptionParser
from zipfile import ZipFile, ZIP_DEFLATED
import locale
import codecs
import time
cout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)

def normalize_path(path):
    if sys.platform == 'win32':
        return path.replace('/', '\\')
    return path

def main(argv):
    o = OptionParser(usage='usage: python %s [OPTIONS] output' % argv[0])
    o.add_option('--dry-run', dest='list', action='store_true', default=False)
    o.add_option('--fset', action='store', default=None)
    o.add_option('--help-exts', action='store_true', help=u'Outputs default pattern')
    o.add_option('--meta', action='append', default=[])
    o.add_option('--meta-inf', action='store')
    o.add_option('--package-json', action='store', default=None)
    o.add_option('--project', action='store', default=None)
    o.add_option('--origin', action='store', default=None)
    o.add_option('--ignore-missing', action='store_true')
    o.add_option('-q', '--quiet', action='store_true')
    options, args = o.parse_args(argv[1:])
    caar = CatyArchiver()
    caar.list = options.list
    caar.fset = options.fset
    caar.origin = options.origin
    caar.quiet = options.quiet
    caar.project = options.project
    caar.meta = options.meta
    caar.meta_inf = options.meta_inf
    caar.ignore_missing = options.ignore_missing
    caar.package_json = options.package_json
    caar.help_exts = options.help_exts
    if caar.help_exts:
        for i in DefaultWhiteListItemContainer()._incl:
            print i.pattern
        sys.exit(0)
    if not caar.origin:
        if not caar.project:
            caar.origin = os.getcwd()
        else:
            caar.origin = 'project'
    if not caar.list:
        if len(args) == 0:
            print >>cout, u'[Error]', u'missing output file'
            o.print_help()
            sys.exit(1)
        caar.outfile = args[0]
    else:
        caar.outfile = None
    caar.read_fset_file()
    caar.archive()

class CatyArchiver(object):
    def read_fset_file(self):
        self.whitelist = DefaultWhiteListItemContainer()
        if self.fset:
            c = unicode(open(self.fset, 'r').read(), 'utf-8')
            wlp = WhiteListParser()
            for i in wlp.feed(c):
                self.whitelist.add(i)

    def archive(self):
        self.setup_origin_dir()
        if self.outfile:
            outfile = ZipFile(self.outfile, u'w', ZIP_DEFLATED)
        for file in self.whitelist.files:
            path = file.pattern.lstrip('/')
            src = self.origin.rstrip(os.path.sep)+os.path.sep+path.strip(os.path.sep)
            if not os.path.exists(src):
                if self.ignore_missing or 'optional' in file.directives:
                    if not self.quiet:
                        print >>cout, u'[Warning]', src, 'does not exist'
                    continue
            if self.list:
                if not os.path.exists(src):
                    print >>cout, u'[Warning]', src, 'does not exist'
                else:
                    print >>cout, src
            else:
                outfile.write(src, path)
        pkg = None
        for directory in self.whitelist.directories:
            base_dir = self.origin.rstrip(os.path.sep) + os.path.sep + directory.pattern.strip(os.path.sep)
            for r, d, f in os.walk(base_dir):
                for e in f:
                    src = r.rstrip(os.path.sep)+os.path.sep+e.strip(os.path.sep)
                    if directory.includes(src):
                        arcpath = src[len(self.origin):]
                        if arcpath.strip(os.path.sep).startswith('META-INF' + os.path.sep):
                            continue
                        if self.list:
                            print >>cout, src
                        else:
                            outfile.write(src, arcpath)
                        if arcpath == 'package.json':
                            pkg = open(src).read()
        for m in self.meta:
            if not os.path.exists(m):
                if not self.quiet:
                    print >>cout, u'[Warning]', m, 'not exists'
                continue
            if os.path.isdir(m):
                if not self.quiet:
                    print >>cout, u'[Warning]', m, 'is directory'
                continue
            m = normalize_path(m)
            fname = m.split(os.path.sep)[-1] 
            outfile.write(m, 'META-INF/' + fname)
            if fname == 'package.json':
                if pkg:
                    if pkg != open(m).read():
                        print >>cout, '[Error]', 'confliction between /package.json and /META-INF/package.json'
                        if self.outfile:
                            outfile.close()
                            os.unlink(self.outfile)
        if self.meta_inf:
            if not os.path.exists(self.meta_inf):
                if not self.quiet:
                    print >>cout, u'[Warning]', self.meta_inf, 'not exists'
            else:
                for r, d, f in os.walk(self.meta_inf):
                    for e in f:
                        if self.outfile:
                            outfile.write(os.path.join(r, e), 'META-INF/' + e)
                        else:
                            print >>cout, os.path.join(r, e)
        if self.package_json:
            if not os.path.exists(self.package_json):
                print >> cout, '[Error]', '%s does not exists' % self.package_json
                if self.outfile:
                    outfile.close()
                    os.unlink(self.outfile)
            if self.outfile:
                outfile.write(self.package_json, 'META-INF/package.json')
        if self.outfile:
            outfile.writestr('META-INF/timezone.txt', tz_to_str(time.timezone))
            outfile.close()

    def setup_origin_dir(self):
        if not self.project:
            return
        else:
            for ag in os.listdir(self.project):
                if ag.strip(os.path.sep) in GROUP_NAMES:
                    pd = os.path.join(self.project.rstrip(os.path.sep), ag)
                    for a in os.listdir(pd):
                        if a == self.origin:
                            self.origin = os.path.join(pd, a)
                            return
            else:
                if self.origin == 'global':
                    self.origin = os.path.join(self.project.rstrip(os.path.sep), self.origin)
                elif self.origin == 'caty':
                    print >>cout, u'[Error]', 'Application name `caty` is defined'
                    sys.exit(1)
                elif self.origin == 'project':
                    self.origin = self.project
                else:
                    print >>cout, u'[Error]', 'Application name `%s` does not exist' % self.origin
                    sys.exit(1)

GROUP_NAMES = ['examples', 'main', 'develop', 'extra', 'common']

class WhiteListItem(object):
    def __init__(self, pattern, directives=()):
        self.pattern = pattern
        self.directives = directives
        self.init_matcher()

    def init_matcher(self):
        if self.pattern.startswith('.'):
            self.matcher = re.compile('/\\.' + re.escape(self.pattern[1:]).replace(u'\\*', u'[^/]*') + '$')
        else:
            self.matcher = re.compile(re.escape(self.pattern).replace(u'\\*', u'[^/]*') + '$')

    def includes(self, path):
        return self.matcher.search(path.replace('\\', '/'))

    @property
    def is_glob(self):
        return '*' in self.pattern

    @property
    def is_file(self):
        return True

def tz_to_str(t):
    return '%+05d' % (-t/(60*60.0) * 100)

class WhiteListParser(object):
    def feed(self, c):
        dirent = None
        for n, line in enumerate(c.splitlines()):
            # remove comment
            if u'#' in line:
                line = line[:line.find(u'#')]
            if not line.strip():
                continue
            if line.startswith(' '):
                if not dirent:
                    raise Exception('Syntax error at line %d' % n)
                else:
                    dirent.add(self.parseline(line))
            else:
                if dirent:
                    yield dirent
                    dirent = None
                e = self.parseline(line)
                if isinstance(e, WhiteListItemContainer):
                    dirent = e
                else:
                    yield e
        if dirent:
            yield dirent

    def parseline(self, line):
        line = line.strip()
        directive = []
        line, directive = self.parse_directive(line, directive)
        if line.endswith(u'/'):
            return WhiteListItemContainer(line, directive)
        else:
            return WhiteListItem(line, directive)

    def parse_directive(self, line, directive):
        if line.startswith('-'):
            directive.append('excl')
            line = line.lstrip(' -\t')
            return self.parse_directive(line, directive)
        elif line.startswith('?'):
            directive.append('optional')
            line = line.lstrip(' ?\t')
            return self.parse_directive(line, directive)
        elif line.startswith('+'):
            line = line.lstrip(' +\t')
            return line, directive
        else:
            return line, directive

class WhiteListItemContainer(WhiteListItem):
    def __init__(self, pattern, directive=()):
        self._incl = []
        self._excl = []
        self._stack = []
        self.parent = None
        WhiteListItem.__init__(self, pattern, directive)
        self.path_matcher = WhiteListItem(pattern, directive)
        self.path_matcher.matcher = self.matcher

    @property
    def is_file(self):
        return False

    @property
    def is_glob(self):
        return False

    @property
    def files(self):
        for e in self._incl:
            if e.is_file and not e.is_glob:
                yield e

    @property
    def directories(self):
        found = False
        for e in self._incl:
            if not e.is_file:
                found = True
                yield e
        if not found:
            yield self

    def init_matcher(self):
        self.matcher = re.compile(re.escape(self.pattern).replace(u'\\*', u'[^/]*'))

    def add(self, item):
        if not 'excl' in item.directives:
            self._incl.append(item)
        else:
            self._excl.append(item)
        item.parent = self

    def includes(self, path):
        for e in self._list_exclude():
            if e.includes(path):
                if not 'excl' in self.directives:
                    return False
                else:
                    return True
        for i in self._list_include():
            if i.includes(path):
                if not 'excl' in self.directives:
                    return True
                else:
                    return False

    def _list_include(self):
        if self.parent:
            for i in self.parent._list_include():
                if i.is_file:
                    yield i
        for i in self._incl:
            yield i

    def _list_exclude(self):
        if self.parent:
            for i in self.parent._list_exclude():
                if i.is_file:
                    yield i
                else:
                    yield i.path_matcher
        for i in self._excl:
            yield i
        if 'excl' in self.directives:
            yield self.path_matcher

class DefaultWhiteListItemContainer(WhiteListItemContainer):
    def __init__(self):
        WhiteListItemContainer.__init__(self, u'')
        self._incl = [
            WhiteListItem('*.atom'),
            WhiteListItem('*.beh'),
            WhiteListItem('*.bin'),
            WhiteListItem('*.bmp'),
            WhiteListItem('*.cara'),
            WhiteListItem('*.casm'),
            WhiteListItem('*.caty'),
            WhiteListItem('*.cgi'),
            WhiteListItem('*.css'),
            WhiteListItem('*.csv'),
            WhiteListItem('*.dot'),
            WhiteListItem('*.eps'),
            WhiteListItem('*.gif'),
            WhiteListItem('*.gz'),
            WhiteListItem('*.htm'),
            WhiteListItem('*.html'),
            WhiteListItem('*.icaty'),
            WhiteListItem('*.jpe'),
            WhiteListItem('*.jpeg'),
            WhiteListItem('*.jpg'),
            WhiteListItem('*.js'),
            WhiteListItem('*.json'),
            WhiteListItem('*.lit'),
            WhiteListItem('*.mp3'),
            WhiteListItem('*.mpe'),
            WhiteListItem('*.mpeg'),
            WhiteListItem('*.mpg'),
            WhiteListItem('*.ogg'),
            WhiteListItem('*.pdf'),
            WhiteListItem('*.png'),
            WhiteListItem('*.ps'),
            WhiteListItem('*.py'),
            WhiteListItem('*.rdf'),
            WhiteListItem('*.svg'),
            WhiteListItem('*.svge'),
            WhiteListItem('*.tar'),
            WhiteListItem('*.tex'),
            WhiteListItem('*.tsv'),
            WhiteListItem('*.txt'),
            WhiteListItem('*.wav'),
            WhiteListItem('*.wiki'),
            WhiteListItem('*.xhtml'),
            WhiteListItem('*.xjson'),
            WhiteListItem('*.xml'),
            WhiteListItem('*.zip'),
        ]
        self._orig_len = len(self._incl)

    def includes(self, path):
        for e in self._excl:
            if e.includes(path):
                if not 'excl' in self.directives:
                    return False
                else:
                    return True
        for i in self._incl:
            if i.includes(path):
                if not 'excl' in self.directives:
                    return True
                else:
                    return False

    @property
    def directories(self):
        found = False
        for e in self._incl:
            if not e.is_file:
                found = True
                yield e
        if not found and len(self._incl) == self._orig_len:
            yield self

if __name__ == '__main__':
    main(sys.argv)
