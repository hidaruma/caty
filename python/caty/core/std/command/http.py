# -*- coding: utf-8 -*- 
# 
#
import caty
from caty.command import Command
try:
    import requests
except:
    print '[Warning] requests is not installed.'

def make_response(resp):
    u"requests.Responseオブジェクトから、CatyのResposeデータを作る"

    header_fields = resp.headers.keys()
    headers = {}
    for fld in header_fields:
        headers[unicode(fld)] = unicode(resp.headers[fld])
    if resp.encoding:
        body = resp.text
    else:
        body = resp.content
    r = {
        u"status"   : resp.status_code,
        u"header"   : headers,
        u"body"     : body,
        }
    if resp.encoding:
        r[u"responseOriginalEncoding"] = unicode(resp.encoding)
    return r


def push_verb(url, verb=None):
    # print "url=" + unicode(url)
    # print "verb=" + unicode(verb)
    if verb is None:
        return url
    s = url.split('?')
    main = s[0]
    qs  = s[1] if len(s) == 2 else ''
    pqs = urlparse.parse_qsl(qs, keep_blank_values=True)
    pqs = [x for x in pqs if not x[0] == '_verb']
    pqs.append(('_verb', verb))
    return main + '?' + '&'.join([x[0]+'='+x[1] for x in pqs])

def _option_warning(opt):
    print "%s option is not supported" % opt


class PushVerb(Command):
    def setup(self, verb=None):
        self.verb = verb

    def execute(self, input):
        return push_verb(input, self.verb)

# requestsのバグか? bodyを捨ててしまう
class Head(Command):
    def setup(self, opts, url):
        self.url = url
        self.timeout = opts.get('timeout', None)
        self.verb = opts.get('verb', None)
        self.debug = opts.get('debug', False)
        if self.debug:
            _option_warning(u'debug')

    def execute(self):
        self.url = push_verb(self.url, self.verb)
        resp = requests.head(self.url, timeout=self.timeout)
        return make_response(resp)

class Get(Command):
    def setup(self, opts, url):
        self.url = url
        self.timeout = opts.get('timeout', None)
        self.verb = opts.get('verb', None)
        self.debug = opts.get('debug', False)
        if self.debug:
            _option_warning(u'debug')

    def execute(self):
        self.url = push_verb(self.url, self.verb)
        resp = requests.get(self.url, timeout=self.timeout)
        return make_response(resp)

class Post(Command):
    def setup(self, opts, url):
        self.url = url
        self.timeout = opts.get('timeout', None)
        self.content_type = opts.get('content-type', 'application/octet-stream')
        self.verb = opts.get('verb', None)
        self.debug = opts.get('debug', False)
        if self.debug:
            _option_warning(u'debug')

    def execute(self, input):
        self.url = push_verb(self.url, self.verb)
        headers ={'content-type': self.content_type}
        resp = requests.post(self.url, timeout=self.timeout, data=input, headers=headers)
        return make_response(resp)


class Put(Command):
    def setup(self, opts, url):
        self.url = url
        self.timeout = opts.get('timeout', None)
        self.content_type = opts.get('content-type', 'application/octet-stream')
        self.verb = opts.get('verb', None)
        self.debug = opts.get('debug', False)
        if self.debug:
            _option_warning(u'debug')

    def execute(self, input):
        self.url = push_verb(self.url, self.verb)
        headers ={'content-type': self.content_type}
        resp = requests.put(self.url, timeout=self.timeout, data=input, headers=headers)
        return make_response(resp)

import urllib
import urlparse

def _quote(x):
    if isinstance(x, unicode):
       return  urllib.quote_plus(x.encode('utf-8'))
    elif x is None:
        return "null"
    elif x is True:
        return "true"
    elif x is False:
        return "false"
    else:
        return x

def urlencode(jsonobj):
    keys = jsonobj.keys()
    q = {}
    for k in keys:
        qk = _quote(k)
        qv = _quote(jsonobj[k])
        q[qk] = qv
    return urllib.urlencode(q)

def urldecode(jsonstr, flat=False, keep_illegal=False):
    unquote = lambda u:unicode(urllib.unquote_plus(u.encode('utf-8')), 'utf-8')
    is_unit_list = lambda x: isinstance(x, list) and len(x) == 1

    pqs = urlparse.parse_qs(jsonstr, keep_blank_values=True)
    keys = pqs.keys()
    uq = {}
    for k in keys:
        if not keep_illegal:
            # 名前のチェックはイイカゲン
            # 先頭が英字かどうかのみ確認
            if len(k) == 0 or not k[0].isalpha():
                continue
        uqk = unquote(k)
        uqv = map(lambda item:unquote(item), pqs[k])
        if flat:
            uq[uqk] = uqv[0] if is_unit_list(uqv) else uqv
        else:
            uq[uqk] = uqv
    return uq

def parse_qs(jsonstr, flat=False, keep_illegal=False):
    if len(jsonstr) > 0 and jsonstr[0] == '?':
        jsonstr = jsonstr[1:]
    return urldecode(jsonstr, flat, keep_illegal)


class UrlEncode(Command):
    def execute(self, input):
        return unicode(urlencode(input))

class UrlDecode(Command):
    def setup(self, opts):
        self.flat = opts.get('flat')
        self.keep_illegal = opts.get('keep-illegal')

    def execute(self, input):
        return urldecode(input, self.flat, self.keep_illegal)

class ParseQS(Command):
    def setup(self, opts):
        self.flat = opts.get('flat')
        self.keep_illegal = opts.get('keep-illegal')

    def execute(self, input):
        return parse_qs(input, self.flat, self.keep_illegal)



def parse_content_type(ct):
    lis = ct.split(';')
    media_type = lis[0]
    items = lis[1:]
    params = {}
    encoding = None
    for p in items:
        kv = p.split('=')
        if len(kv) == 2:
          params[kv[0]] = kv[1]
          if kv[0] == 'charset':
              encoding = kv[1]
    r = {
        u'mediaType': media_type,
        u'params' : params
        }
    if encoding:
        r[u'encoding'] = encoding
    return r

class ParseContentType(Command):
    def execute(self, input):
        return parse_content_type(input)


