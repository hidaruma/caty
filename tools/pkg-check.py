import subprocess
import sys

def main():
    p = subprocess.Popen(['pip', 'freeze'], stdout=subprocess.PIPE).communicate()
    pkgmap = {}
    for l in p[0].split('\n'):
        if l:
            a, b = l.split('==')
            pkgmap[a] = b
    f = sys.argv[1]
    ng = False
    for l in open(f):
        l = l.strip()
        if l:
            pkg, version = map(lambda s: s.strip(), l.split('=='))
            if pkg in pkgmap:
                if newer(version, pkgmap[pkg]):
                    continue
            ng = True
            print pkg, version, 'is not installed.'
    return ng

def newer(v1, v2):
    for a, b in zip(v1.split('.'), v2.split('.')):
        if a == b:
            continue
        if len(b) != len(a):
            return cmp(len(b), len(a))
        return cmp(b, a)
    return 1

if __name__ == '__main__':
    if main():
        sys.exit(0)
    sys.exit(1)


