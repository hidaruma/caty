import subprocess
import sys
import json
import os
from zipfile import ZipFile
from optparse import OptionParser

example = """pkg-list-file example(plain text):

requests==0.12.0
pygraphviz==1.1
PIL==1.1.7

or (json)

{
  "dependencies": {
    "python2": {
       "requests": "0.12.0",
       "pygraphviz": "1.1",
       "PIL": "1.1.7"
    }
  },
  :
  :
}
"""

def main():
    argv = sys.argv
    o = OptionParser(usage='usage: python %s [OPTIONS] pkg-list-file\n%s' % (argv[0], example))
    o.add_option('--verbose', action='store_true', default=None)
    o.add_option('--project', action='store', default='.')
    options, args = o.parse_args(argv[1:])
    if len(args) < 1:
        print '[Error] package list is not specified'
        o.print_help()
        sys.exit(1)
    f = args[0]
    if f.endswith('.json'):
        extractor = extract_from_json
    elif f.endswith('.zip'):
        extractor = extract_from_zip
    else:
        extractor = extract_from_text
    ok = True
    e = extractor(f)
    pkgmap = init_pkg_map()
    featuremap = init_feature_map(options.project)
    for pkg, versions in e.python2:
        found = False
        if pkg in pkgmap:
            for ver in versions:
                if compatible(ver, pkgmap[pkg]):
                    if options.verbose:
                        print '[OK]', pkg, ver
                    found = True
                    break
        if not found:
            ok = False
            print '[NG]', pkg, ', '.join(versions), 'is not installed.'
    for feature, versions in e.features:
        found = False
        if feature in featuremap:
            for ver in versions:
                for installed in featuremap[feature]:
                    if compatible(ver, installed):
                        if options.verbose:
                            print '[OK]', feature, ver
                        found = True
                        break
                if found:
                    break
        if not found:
            ok = False
            print '[NG]', feature, ', '.join(versions), 'is not installed.'
    return ok

def init_pkg_map():
    try:
        subp = subprocess.Popen(['pip', 'freeze'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        print '[Error] pip is not installed'
        sys.exit(1)
    r = subp.wait()
    if r != 0:
        p = subp.communicate()
        print '[Error]'
        print p
        sys.exit(r)
    p = subp.communicate()
    pkgmap = {}
    for l in p[0].split('\n'):
        if l:
            a, b = l.split('==')
            pkgmap[a] = b
    return pkgmap

def init_feature_map(base_dir):
    d = os.path.join(base_dir.rstrip('\\/'), 'features')
    map = {}
    for f in os.listdir(d):
        if f.endswith('.install.log'):
            name, version = f.rsplit('_', 1)
            version = version.rsplit('.', 1)[0]
            if name in map:
                map[name].add(version)
            else:
                map[name] = set([version])
    for f in os.listdir(d):
        if f.endswith('.uninstall.log'):
            name, version = f.rsplit('_', 1)
            version = version.rsplit('.', 1)[0]
            if version in map.get(name, []):
                map[name].discard(version)
    return map

def compatible(required, installed):
    if required.startswith('~'):
        return newer(fix(required[1:]), fix(installed)) < 1
    elif required.startswith('='):
        return fix(required[1:]) == fix(installed)
    else:
        return newer(fix(required), fix(installed)) < 1

def newer(v1, v2):
    for a, b in zip(v1.split('.'), v2.split('.')):
        if a == b:
            continue
        if len(a) != len(b):
            return cmp(len(a), len(b))
        return cmp(a, b)
    return 0

def fix(s):
    chunk = s.split('.')
    if len(chunk) >= 3:
        return s.strip()
    else:
        for i in range(3-len(chunk)):
            chunk.append('0')
        return '.'.join(chunk).strip()

def extract_from_text(f):
    r = []
    for l in open(f):
        l = l.strip()
        if l:
            pkg, version = map(lambda s: s.strip(), l.split('=='))
            r.append((pkg, version))
    return Requierement(r)

def extract_from_json(f):
    return _extract_from_json(open(f).read())

def _extract_from_json(c):
    j = json.loads(c)
    d = j.get('dependencies', {})
    p2 = d.pop('python2', {}).items()
    f = []
    for name, val in d.items():
        if isinstance(val, basestring):
            val = [val]
        f.append((name, val))
    return Requierement(p2, f)

def extract_from_zip(f):
    zp = ZipFile(open(f, 'rb'))
    for info in zp.infolist():
        if info.filename == 'META-INF/package.json':
            return _extract_from_json(zp.read(info))
    print '[Error] META-INF/package.json does not exists'
    sys.exit(1)

class Requierement(object):
    def __init__(self, python2, anythingelse=()):
        self.python2 = python2
        self.features = anythingelse

if __name__ == '__main__':
    if main():
        sys.exit(0)
    sys.exit(1)

