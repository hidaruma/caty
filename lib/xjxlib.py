#coding: utf-8
from caty.core.schema.base import JsonSchemaError, JsonSchemaErrorObject, JsonSchemaErrorList
from caty.util import escape_html, error_to_ustr
import caty.jsontools as json
import urllib

BLOCK = [
    'p',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'hr',
    'table',
    'tr',
    'li',
    'ul',
    'ol',
    'pre',
    'dt',
    'dd',
    'dl',
    'div',
    'blockquote',
]

def markup(input, mode):
    return XJXMarkup(input, mode).transform()

def strip(input):
    return XJXMarkup(input, None).strip()

class XJXMarkup(object):
    def __init__(self, input, mode):
        self.input = input
        self.mode = mode

    def transform(self):
        return self.markup(self.input)

    def strip(self):
        return self._strip(self.input)

    def markup(self, input):
        r = []
        if isinstance(input, (basestring, json.TaggedValue)):
            return self.markup([input])
        for node in input:
            if json.tag(node) == 'string':
                r.append(self.escape_html(node))
            else:
                tag, data = json.split_tag(node)
                if tag == 'charref':
                    r.append(u''.join(data['']))
                elif tag == 'section':
                    tag = 'div'
                    body = []
                    attrs = {}
                    for k, v in data.items():
                        if k == '':
                            body = self.markup(self.compress(v))
                        else:
                            attrs[k] = escape_html(v)
                    cls = attrs.get('class', u'')
                    elem = self._to_element(tag, attrs, body)
                    r.append(elem)
                    r.append(u'\n')
                elif tag == 'ruby':
                    r.append(self._transform_ruby(data))
                else:
                    attrs = {}
                    body = []
                    for k, v in data.items():
                        if k == '':
                            body = self.markup(self.compress(v))
                        else:
                            attrs[k] = v
                    elem = self._to_element(tag, attrs, body)
                    r.append(elem)
                    if tag in BLOCK:
                        r.append(u'\n')
        return u''.join(r)

    def _attrs_to_str(self, data):
        attrs = {}
        for k, v in data.items():
            if k:
                attrs[k] = escape_html(v)
        return self._to_attr(attrs)

    def _to_element(self, tag, attrs, body):
        tag = tag.lstrip()
        if body:
            if attrs:
                return u'<%(tag)s %(attrs)s>%(body)s</%(tag)s>' % ({'tag': tag,
                                                              'attrs':self._to_attr(attrs),
                                                              'body': body})
            else:
                return u'<%(tag)s>%(body)s</%(tag)s>' % ({'tag': tag, 'body': body})
        else:
            if attrs:
                if tag in ('li', 'ul', 'ol') and self.mode == u'html':
                    return u'<%s %s></%s>' % (tag, self._to_attr(attrs), tag) 
                return u'<%s %s />' % (tag, self._to_attr(attrs)) 
            elif tag in ('li', 'ul', 'ol') and self.mode == u'html':
                return u'<%s></%s>' % (tag, tag) 
            else:
                return u'<%s />' % (tag)

    def _to_attr(self, attrs):
        r = []
        for k, v in attrs.items():
            r.append('%s="%s"' % (k, escape_html(v)))
        return ' '.join(r)

    def escape_html(self, s):
        r = escape_html(s)
        return r

    def compress(self, seq):
        r = []
        t = []
        for s in seq:
            if isinstance(s, basestring):
                t.append(s)
            else:
                r.append(u''.join(t))
                r.append(s)
                t = []
        if t:
            r.append(u''.join(t))
        return r

    def _transform_ruby(self, data):
        rb = self._transform_rb(data[''][0])
        rp1 = self._transform_rp(data[''][1])
        rt = self._transform_rt(data[''][2])
        rp2 = self._transform_rp(data[''][3])
        return u'<ruby>%s%s%s%s</ruby>' % (rb, rp1, rt, rp2)

    def _transform_rb(self, obj):
        c = json.untagged(obj)['']
        return u'%s' % self.markup(c)
        
    def _transform_rp(self, obj):
        c = json.untagged(obj)['']
        return u'<rp>%s</rp>' % self.markup(c)

    def _transform_rt(self, obj):
        c = json.untagged(obj)['']
        return u'<rt>%s</rt>' % self.markup(c)


    def _strip(self, input, paragraphfound=False):
        r = []
        if isinstance(input, (basestring, json.TaggedValue)):
            return self._strip([input])
        for node in input:
            if json.tag(node) == 'string':
                r.append(node)
            else:
                tag, data = json.split_tag(node)
                if tag in ('div', 'span') and '__mathjaxsection__' in data.get('class', '').split():
                    # 数式は区切り記号を一つにして数式の文字列自体はそのまま
                    r.append(u'$%s$' % (''.join(data[''])))
                elif tag in BLOCK and tag != 'p':
                    # 最初に出現したパラグラフ以外のブロック要素は削除
                    continue 
                elif tag == 'p':
                    if paragraphfound:
                        continue
                    else:
                        paragraphfound = True
                    r.extend(self._strip(data[''], paragraphfound))
                elif tag == 'charref':
                    r.append(u''.join(data['']))
                elif tag == 'br':
                    # 改行タグは削除
                    continue
                elif tag in ('sup', 'sub', 'em', 'strong', 'a'):
                    # タグのみ削除
                    r.extend(self._strip(data[''], paragraphfound))
                elif tag == 'span' and self._is_special_span(data.get('class', '').split()):
                    # 特殊なspanはタグのみ削除
                    r.extend(self._strip(data[''], paragraphfound))
                elif tag == 'img':
                    # imgはaltを残す
                    if data.get('ah_filled') != u'auto':
                        r.append(data.get('alt', u''))
                elif tag == 'ruby':
                    # テキスト(ルビ)にする
                    rb = u''.join(self._strip(json.untagged(data[''][0])['']))
                    rp1 = u''.join(self._strip(json.untagged(data[''][1])['']))
                    rt = u''.join(self._strip(json.untagged(data[''][2])['']))
                    rp2 = u''.join(self._strip(json.untagged(data[''][3])['']))
                    r.append(u'%s%s%s%s' % (rb, rp1, rt, rp2))
        return u''.join(r)

    def _is_special_span(self, classes):
        if not classes:
            return True
        for c in ['tt', 'note', 'notice', 'gext']:
            if c in classes:
                return True
        return False


def find_mathjax(input):
    r = []
    if isinstance(input, (basestring, json.TaggedValue)):
        return find_mathjax([input])
    for node in input:
        if json.tag(node) == 'string':
            pass
        else:
            tag, data = json.split_tag(node)
            for k, v in data.items():
                if k == '':
                    r.extend(find_mathjax(v))
                else:
                    if k == 'class':
                        cls = v.split()
                        if '__mathjaxsection__' in cls or '__rawmathml__' in cls:
                            r.append(True)
    return r

def extract_image(input):
    if isinstance(input, (basestring, json.TaggedValue)):
        for i in extract_image([input]):
            yield i
    for node in input:
        if json.tag(node) == 'string':
            pass
        else:
            tag, data = json.split_tag(node)
            for k, v in data.items():
                if k == 'src' and tag == 'img':
                    yield v
                elif k == '':
                    for i in extract_image(v):
                        yield i



