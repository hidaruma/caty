#coding: utf-8
import re
replacer = re.compile(r'[\s"\']')
from string import Template

class I18nMessage(object):
    def __init__(self, messages, parent=None, writer=None, lang='en', app=None):
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
        self._app = app

    def _normalize(self, s):
        return replacer.sub('', s.lower())

    def get(self, msg, message_dict=None, language_code=None, **kwds):
        l = language_code or self._lang
        tmpl = self._get_message(msg, message_dict, l, **kwds)
        if not tmpl:
            if self._app and l != 'en':
                self._app.get_logger('app').debug(u'message is not translated yet:'  +msg)
            tmpl = {'en':Template(msg)} #フォールバック
        t = tmpl.get(l, tmpl['en'])
        if message_dict:
            return t.safe_substitute(message_dict)
        else:
            return t.safe_substitute(kwds)

    def _get_message(self, msg, message_dict=None, language_code=None, **kwds):
        l = language_code or self._lang
        k = self._normalize(msg)
        tmpl = self._messages.get(k, None)
        if not tmpl:
            if self._parent:
                return self._parent._get_message(msg, message_dict, l, **kwds)
        return tmpl

    def write(self, *args, **kwds):
        if 'nobreak' in kwds:
            del kwds['nobreak']
            self._writer.write(self.get(*args, **kwds) + '\n')
        else:
            self._writer.write(self.get(*args, **kwds) + '\n')

    def extend(self, app, messages):
        return I18nMessage(messages, self, self._writer, self._lang, app)

class I18nMessageWrapper(object):
    def __init__(self, catalog, env):
        self.catalog = catalog
        self.env = env

    def get(self, msg, message_dict=None, **kwds):
        return self.catalog.get(msg, language_code=self.env.get('LANGUAGE'), message_dict=message_dict, **kwds)

    def write(self, *args, **kwds):
        if 'nobreak' in kwds:
            del kwds['nobreak']
            self.catalog._writer.write(self.get(*args, **kwds) + '\n')
        else:
            self.catalog._writer.write(self.get(*args, **kwds) + '\n')



