import os
import re
import sys
from optparse import OptionParser
from zipfile import ZipFile, ZIP_DEFLATED



def main(argv):
    caar = CatyArchiver(usage='usage: python %s [OPTIONS] output' % argv[0])
    caar.add_option('--list', action='store_true', default=False)
    caar.add_option('--filter', action='store', default=None)
    caar.add_option('--meta', action='append', default=[])
    caar.add_option('--origin', action='store', default=os.getcwd())
    caar.add_option('-q', '--quiet', action='store_true')
    options, args = caar.parse_args(argv[1:])
    caar.list = options.list
    caar.filter = options.filter
    caar.origin = options.origin
    caar.quiet = options.quiet
    caar.meta = options.meta
    if not caar.list:
        caar.outfile = args[0]
    else:
        caar.outfile = None
    caar.read_filter_file()
    caar.archive()

class CatyArchiver(OptionParser):
    def read_filter_file(self):
        self.whitelist = DefaultWhiteListItemContainer()
        if self.filter:
            c = open(self.filter, 'r').read()
            wlp = WhiteListParser()
            for i in wlp.feed(c):
                self.whitelist.add(i)

    def archive(self):
        if self.outfile:
            outfile = ZipFile(self.outfile, u'w', ZIP_DEFLATED)
        incl = []
        for n in os.listdir(self.origin):
            path = self.origin.strip(os.path.sep)+os.path.sep+n.strip(os.path.sep) + os.path.sep
            if self.whitelist.includes(path):
                arcpath = path[len(self.origin):]
                incl.append(arcpath)
        for r, d, f in os.walk(self.origin):
            for e in f:
                src = r.rstrip(os.path.sep)+os.path.sep+e.strip(os.path.sep)
                path = r.strip(os.path.sep)+os.path.sep+e.strip(os.path.sep)
                if self.whitelist.includes(path):
                    arcpath = path[len(self.origin):]
                    if os.path.sep in arcpath:
                        for i in incl:
                            if arcpath.strip(os.path.sep).startswith('META-INF' + os.path.sep):
                                continue
                            if arcpath.startswith(i):
                                if self.list:
                                    print src
                                else:
                                    outfile.write(src, arcpath)
        for m in self.meta:
            if not os.path.exists(m):
                print u'[Warning]', m, 'not exists'
                continue
            if os.path.isdir(m):
                print u'[Warning]', m, 'is directory'
                continue
            outfile.write(m, 'META-INF/' + m.split(os.path.sep)[-1])
        if self.outfile:
            outfile.close()

class WhiteListItem(object):
    def __init__(self, pattern, directives=()):
        self.pattern = pattern
        self.directives = directives
        self.init_matcher()

    def init_matcher(self):
        self.matcher = re.compile(re.escape(self.pattern).replace(u'\\*', u'[^/]*') + '$')

    def set_parent(self, parent):
        self.pattern = parent.pattern+self.pattern
        self.init_matcher()

    def includes(self, path):
        return self.matcher.search(path.replace('\\', '/'))

class WhiteListParser(object):
    def feed(self, c):
        dirent = None
        for n, line in enumerate(c.splitlines()):
            if not line.strip():
                continue
            # remove comment
            if u'#' in line:
                line = line[:line.find(u'#')]
            if line.startswith(' '):
                if not dirent:
                    raise Exception('Syntax error ato line %d' % n)
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
        if line.startswith('-'):
            directive = ['excl']
            line = line.lstrip(' -\t')
        if line.endswith(u'/'):
            return WhiteListItemContainer(line, directive)
        else:
            return WhiteListItem(line, directive)

class WhiteListItemContainer(WhiteListItem):
    def __init__(self, pattern, directive=()):
        self._incl = []
        self._excl = []
        self._stack = []
        WhiteListItem.__init__(self, pattern, directive)

    def init_matcher(self):
        self.matcher = re.compile(re.escape(self.pattern).replace(u'\\*', u'[^/]*'))

    def add(self, item):
        if not 'excl' in item.directives:
            self._incl.append(item)
        else:
            self._excl.append(item)
        item.set_parent(self)

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
        return WhiteListItem.includes(self, path)


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

if __name__ == '__main__':
    main(sys.argv)
