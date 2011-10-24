# coding: utf-8
from topdown import *
from topdown.util import quoted_string
from HTMLParser import HTMLParser
import shlex
from caty.core.exception import InternalException
import caty.core.runtimeobject as ro
from caty.template import compilers

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
        raise InternalException(u'')
    body_start = st + len(t)
    end = body_end + 2
    return st, body_start, body_end, end


find_meta = lambda s: find_(s, '<?caty-meta')
find_script = lambda s: find_(s, '<?caty-script')

@as_parser
def schebang(seq):
    pre, meta = option(parse_meta, {})(seq)
    if meta:
        c = compilers[meta['template']].get_parser()
        skip_ws(seq)
        many(c.comment)(seq)
        script = option(parse_script, u'')(seq)
    else:
        script = u''
    return pre, meta, script, seq.rest

@try_
def parse_meta(seq):
    pre = until('<?')(seq)
    while not seq.eof:
        S(u'<?')(seq)
        try:
            keyword(u'caty-meta')(seq)
            break
        except:
            raise
        pre += until('<?')(seq)
    if len(pre) > 200:
        raise ParseError(seq, parse_meta)
    try:
        keyword(u'template')(seq)
        S(u'=')(seq)
        tmpl = quoted_string(seq)
        if seq.parse(option(keyword(u'type'))):
            S(u'=')(seq)
            tp = quoted_string(seq)
            r = {
                u'template': tmpl,
            }
        else:
            r = {
                u'template': tmpl,
            }
        S('?>')(seq)
    except ParseError, e:
        raise Exception(ro.i18n.get(u'caty-meta PI syntax error: $message', message=e._message))
    return pre, r

@try_
def parse_script(seq):
    S(u'<?')(seq)
    try:
        keyword(u'caty-script')(seq)
    except:
        raise
    try:
        r = until('?>')(seq)
        S('?>')(seq)
    except ParseError, e:
        raise Exception(ro.i18n.get(u'caty-script PI syntax error: $message', message=e._message))
    return r

def parse(s, associate=False):
    u"""shebang の読み取りを行う。
    Caty テンプレートの shebang は
    <?caty-meta?> と <?caty-script ?> の二種類がある。
    どちらも一つのファイルに最大で一回まで出現可能であり、
    二度目以降の shebang は処理されない。
    """
    pre, meta, script, content = schebang.run(s, auto_remove_ws=True)
    return meta, script if associate else u'', pre+content

