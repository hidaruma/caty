#coding:utf-8
from caty.template.core.context import *
from caty.template.core.exceptions import TemplateRuntimeError
from caty.util import escape_html
import caty

class Renderer(object):
    def to_str(self, obj):
        if isinstance(obj, (list, tuple)):
            r = []
            for i in obj:
                v = self.to_str(i)
                if isinstance(i, basestring):
                    r.append('"%s"' % v)
                else:
                    r.append(v)
            return u'[%s]' % u','.join(r)
        elif isinstance(obj, dict):
            r = []
            for k, v in obj.items():
                r.append(u'"%s":%s' % (k, self.to_str(v)))
            return u'{%s}' % u','.join(r)
        elif isinstance(obj, bool):
            return unicode(obj).lower()
        elif obj is caty.UNDEFINED:
            return u''
        else:
            return unicode(obj)

    def render(self, obj):
        raise NotImplementedError()

class HTMLRenderer(Renderer):
    def render(self, obj):
        if isinstance(obj, StringWrapper):
            if obj.type == 'var':
                return self._escape(obj.get_string())
            else:
                return obj.get_string()
        elif isinstance(obj, basestring):
            return obj
        else:
            return self.to_str(obj)

    def _escape(self, s):
        return escape_html(s)

class TextRenderer(Renderer):
    def render(self, obj):
        if isinstance(obj, StringWrapper):
            return obj.get_string()
        elif isinstance(obj, basestring):
            return obj
        else:
            return self.to_str(obj)


