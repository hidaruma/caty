import subprocess
import sys
from optparse import OptionParser

example = '''pkg-list-file example:

requests==0.12.0
pygraphviz==1.1
PIL==1.1.7
'''

def main():
    argv = sys.argv
    o = OptionParser(usage='usage: python %s [OPTIONS] pkg-list-file\n%s' % (argv[0], example))
    o.add_option('--verbose', action='store_true', default=None)
    options, args = o.parse_args(argv[1:])
    p = subprocess.Popen(['pip', 'freeze'], stdout=subprocess.PIPE).communicate()
    pkgmap = {}
    for l in p[0].split('\n'):
        if l:
            a, b = l.split('==')
            pkgmap[a] = b
    if len(args) < 1:
        print '[Error] package list is not specified'
        o.print_help()
        sys.exit(1)
    f = args[0]
    ok = True
    for l in open(f):
        l = l.strip()
        if l:
            pkg, version = map(lambda s: s.strip(), l.split('=='))
            if pkg in pkgmap:
                if newer(version, pkgmap[pkg]):
                    if options.verbose:
                        print '[OK]', pkg, pkgmap[pkg]
                    continue
            ok = False
            print '[NG]', pkg, version, 'is not installed.'
    return ok

def newer(v1, v2):
    for a, b in zip(v1.split('.'), v2.split('.')):
        if a == b:
            continue
        if len(a) != len(b):
            return cmp(len(a), len(b))
        return cmp(a, b)
    return 1

if __name__ == '__main__':
    if main():
        sys.exit(0)
    sys.exit(1)


