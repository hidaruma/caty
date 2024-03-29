import subprocess
import sys
import json
import os
from zipfile import ZipFile
from optparse import OptionParser
if sys.version.startswith('2'):
    VERSION = 'python2'
else:
    VERSION = 'python3'
example = """pkg-list-file example(json):
{
  "engines": {
    "python2": ">=2.6"
  },
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

py_ver = sys.version.split(' ')[0].strip()
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
        print '[Error] package list must be json'
        o.print_help()
        sys.exit(1)
    ok = True
    e = extractor(f)
    pkgmap = init_pkg_map()
    featuremap = init_feature_map(options.project)
    for engine in e.engines:
        if compatible(engine, py_ver):
            if options.verbose:
                print '[OK]', sys.version
        else:
            print '[NG]', 'python', engine, 'required'
            return False
    for pkg, versions in e.packages:
        found = False
        if pkg in pkgmap:
            for ver in versions:
                if compatible(ver, pkgmap[pkg]):
                    if options.verbose:
                        print '[OK]', pkg, pkgmap[pkg]
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
                            print '[OK]', feature, installed
                        found = True
                        break
                if found:
                    break
        if not found:
            ok = False
            print '[NG]', feature, ', '.join(versions), 'is not installed.'
    return ok

def init_pkg_map():
    import re
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
    ptn = re.compile('[a-zA-Z0-9]+ *== *.+')
    for l in p[0].split('\n'):
        if l and ptn.match(l):
            a, b = l.split('==')
            pkgmap[a] = b
        elif l:
            print '[Warning] Unexpected output from pip:', l
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

def compatible(requireds, installed):
    installed = fix(installed)
    r = []
    for required in transform(requireds.split(' ')):
        if required.startswith('='):
            r.append(required[1:] == installed)
        elif required.startswith('>='):
            r.append((newer(required[2:], installed) < 1 
                 or required[2:] == installed))
        elif required.startswith('>'):
            r.append(newer(required[1:], installed) < 1)
        elif required.startswith('<'):
            r.append(not (newer(required[1:], installed) < 1 
                 or required[1:] == installed))
        elif required.startswith('<='):
            r.append(not (newer(required[1:], installed) < 1))
        elif required == '*':
            r.append(True)
        else:
            print '[Error] invalid version', required
            sys.exit(1)
    return all(r)

def transform(chunks):
    for c in chunks:
        c = c.strip()
        if not c:
            continue
        if c.startswith('~'):
            c = fix(c[1:])
            yield '>=' + c
            toks = c.split('.')
            if len(toks) < 2:
                next = 1
            else:
                next = int(toks[1]) + 1
            yield '<' + '.'.join([toks[0], str(next), '0'])
        else:
            yield fix(c)

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
        return '.'.join(chunk[0:3])
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
    e = j.get('engines', {}).get(VERSION, py_ver)
    d = j.get('dependencies', {})
    p = d.get(VERSION, {}).items()
    f = d.get('caty', {}).items()
    return Requierement(e, p, f)

def extract_from_zip(f):
    zp = ZipFile(open(f, 'rb'))
    for info in zp.infolist():
        if info.filename == 'META-INF/package.json':
            return _extract_from_json(zp.read(info))
    print '[Error] META-INF/package.json does not exists'
    sys.exit(1)

class Requierement(object):
    def __init__(self, engine, dependencies, features):
        self.packages = []
        for k, v in dependencies:
            if isinstance(v, basestring):
                v = [v]
            self.packages.append((k, concat_map(self.split_or, v)))
        self.engines = concat_map(self.split_or, [engine] if isinstance(engine, basestring) else engine)
        self.features = []
        for n, v in features:
            if isinstance(v, basestring):
                v = [v]
            self.features.append((n, concat_map(self.split_or, v)))

    def split_or(self, val):
        r = []
        for c in val.split('||'):
            r.append(c.strip())
        return r

def concat_map(f, l):
    return reduce(lambda a, b: a+b, map(f, l))

if __name__ == '__main__':
    if main():
        sys.exit(0)
    sys.exit(1)


