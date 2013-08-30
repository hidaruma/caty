#coding: utf-8
from caty.core.command import Command
from caty.core.schema.base import JsonSchemaError, JsonSchemaErrorObject, JsonSchemaErrorList
try:
    from caty.core.std.command.builtin import TypeCalculator
except:
    print '[WARNING] Please update caty to latest version'
    from caty.command.builtin import TypeCalculator
from caty.util import escape_html
import caty.jsontools as json
from xjxlib import markup, strip

_BLOCK = [
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

class Markup(Command):
    def setup(self, opts):
        self.__html = opts['html']

    def execute(self, input):
        return markup(input, 'html' if self.__html else None)

class Strip(Command):

    def execute(self, input):
        return strip(input)

class Validate(Command, TypeCalculator):

    def setup(self, opts, schema_name):
        self.__schema_name = schema_name
        self.__embed_msg = opts.embed_msg

    def execute(self, input):
        s = self.schema[self.__schema_name]
        try:
            s.validate(input)
        except JsonSchemaError, e:
            if self.__embed_msg:
                return self._embed(input, e)
            else:
                return self.error_report(e)
        else:
            return input

    def _embed(self, source, errors):
        r = []
        for s, e in self._zip(source, errors):
            r.extend(self._merge(s, e))
        return r

    def _merge(self, s, e):
        if isinstance(e, JsonSchemaErrorObject):
            o = {}
            for k, v in s.items():
                if e[k].is_error:
                    o[k] = self._merge(v, e[k])
                else:
                    o[k] = v
            return [o]
        elif isinstance(e, JsonSchemaErrorList):
            if not isinstance(s, list):
                return [s, self._error_to_elem(e).pop()]
            else:
                l = []
                for a, b in zip(s, e):
                    l.append(self._merge(a, b))
                return l
        else:
            if e.is_error:
                if s:
                    return [json.tagged('span', {'':[e.message], 'class': u'error'}), s]
                else:
                    return [json.tagged('span', {'':[e.message], 'class': u'error'})]
            else:
                return [s]

    def _zip(self, source, errors):
        if not source:
            source = [u'']
        if isinstance(errors, JsonSchemaError):
            return zip(source, [errors])
        else:
            return zip(source, errors)

    def _error_to_elem(self, e, s=None):
        if s:
            return [json.tagged('span', {'':[e.message], 'class': u'error'}), s]
        else:
            return [json.tagged('span', {'':[e.message], 'class': u'error'})]

class Normalize(Command):
    
    def execute(self, input):
        r = []
        if isinstance(input, (basestring, json.TaggedValue)):
            return self.execute([input])
        for node in input:
            if json.tag(node) == 'string':
                if r and isinstance(r[-1], basestring):
                    r[-1] += node
                else:
                    r.append(node)
            else:
                tag, data = json.split_tag(node)
                attrs = {}
                body = []
                for k, v in data.items():
                    if k == '':
                        body = self.execute(v)
                    else:
                        attrs[k] = v
                attrs[''] = body
                elem = json.tagged(tag, attrs)
                r.append(elem)
        return r
