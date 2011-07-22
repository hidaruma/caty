# coding: utf-8
from topdown import *
from HTMLParser import HTMLParser
import shlex
from caty.core.exception import InternalException
def split_meta(s):
    if not s: return {}
    d = {}
    for t in shlex.split(str(s)):
        try:
            k, v = t.split('=', 1)
        except:
            raise Exception(s)
        else:
            d[k.strip().encode()] = v.strip().encode()
    return d

def find_(s, t):
    st = s.find(t)
    if st == -1:
        return 0, 0, 0, 0
    body_end = s.find('?>', st)
    if body_end == -1:
        raise InternalException(u'shebang syntax error')
    body_start = st + len(t)
    end = body_end + 2
    return st, body_start, body_end, end


find_meta = lambda s: find_(s, '<?caty-meta')
find_script = lambda s: find_(s, '<?caty-script')

def parse(s, associate=False):
    u"""shebang の読み取りを行う。
    Caty テンプレートの shebang は
    <?caty-meta?> と <?caty-script ?> の二種類がある。
    どちらも一つのファイルに最大で一回まで出現可能であり、
    二度目以降の shebang は処理されない。
    """
    meta_st, meta_main, meta_main_end, meta_end = find_meta(s)
    meta = s[meta_main:meta_main_end]
    script_st, script_main, script_main_end, script_end = find_script(s)
    script = s[script_main:script_main_end]
    a, b, c, d = list(sorted((meta_st, meta_end, script_st, script_end)))
    content = ''.join((s[:a].rstrip(), s[b:c].lstrip(), s[d:].lstrip()))
    return split_meta(meta), script if associate else u'', content

