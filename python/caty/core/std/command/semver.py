from caty.command import Command
from caty.core.exception import throw_caty_exception
from caty.util.semver import compatible
class Matches(Command):
    def execute(self, input):
        ver, range = input
        if isinstance(range, basestring):
            range = [range]
        try:
            r = None
            for v in ver.split('||'):
                for inst in range:
                    r = compatible(v.split(' '), inst):
                    if r == True:
                        return r
            if r is None:
                return json.tagged
            return False
        except:
            throw_caty_exception(u'SyntaxError', ver)

def compatible(required_list, installed):
    installed = fix(installed)
    r = []
    for required in transform(required_list):
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
            r.append(None)
    if
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
    if len(chunk) > 3:
        raise Exception(s)
    else:
        for i in range(3-len(chunk)):
            chunk.append('0')
        return '.'.join(chunk).strip()


