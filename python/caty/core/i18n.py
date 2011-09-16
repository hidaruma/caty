#coding: utf-8
import re
replacer = re.compile(r'[\s"\']')
from string import Template

class I18nMessage(object):
    def __init__(self, messages, parent=None, writer=None, lang='en'):
        self._parent = parent
        self._messages = {}
        for k, v in messages.items():
            key = self._normalize(k)
            if 'en' not in v:
                v['en'] = k
            self._messages[key] = {}
            for l, m in v.items():
                self._messages[key][l] = Template(m)
        self._writer = writer
        self._lang = lang

    def _normalize(self, s):
        return replacer.sub('', s.lower())

    def get(self, msg, message_dict=None, language_code=None, **kwds):
        l = language_code or self._lang
        k = self._normalize(msg)
        tmpl = self._messages.get(k, None)
        if not tmpl:
            if self._parent:
                return self._parent.get(msg, message_dict, **kwds)
            else:
                tmpl = {'en':Template(msg)} #フォールバック
        t = tmpl.get(l, tmpl['en'])
        if message_dict:
            return t.safe_substitute(message_dict)
        else:
            return t.safe_substitute(kwds)

    def write(self, *args, **kwds):
        if 'nobreak' in kwds:
            del kwds['nobreak']
            self._writer.write(self.get(*args, **kwds) + '\n')
        else:
            self._writer.write(self.get(*args, **kwds) + '\n')

    def extend(self, messages):
        return I18nMessage(messages, self, self._writer, self._lang)

