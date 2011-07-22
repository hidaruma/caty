# coding: utf-8

def join(*names):
    def _join(a, b):
        if not a: return b
        if not b: return a
        if a.endswith('/'):
            if b.startswith('/'):
                return '%s/%s' % (a.rstrip('/'), b.lstrip('/'))
            else:
                return '%s/%s' % (a.rstrip('/'), b)
        else:
            if b.startswith('/'):
                return '%s/%s' % (a, b.lstrip('/'))
            else:
                return '%s/%s' % (a, b)
    return reduce(_join, names)

def splitext(s):
    if '.' in s:
        p, e = s.rsplit('.', 1)
        return p, '.' + e
    else:
        return s, u''

def dirname(s):
    return s.rsplit('/', 1)[0] if s != u'/' else s

def split(path):
    d, b = path.rsplit('/', 1)
    if d == '':
        d = u'/'
    return d, b
