#coding: utf-8
from caty.core.schema.base import *
import caty.core.runtimeobject as ro
import random
printable = list('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ \t\n')

class StringSchema(ScalarSchema):

    minLength = attribute('minLength')
    maxLength = attribute('maxLength')
    format = attribute('format', None)
    profile = attribute('profile')
    pattern = attribute('pattern', None)
    excludes = attribute('excludes', [])

    __options__ = SchemaBase.__options__ | set(['maxLength', 'minLength', 'format', 'profile', 'pattern', 'excludes'])
    
    def __init__(self, *args, **kwds):
        ScalarSchema.__init__(self, *args, **kwds)
        if (self.minLength > self.maxLength) and (self.maxLength is not None):
            raise JsonSchemaError(dict(msg='minLength($min) is longer than maxLength($max)', min=self.minLength, max=self.maxLength))
        if self.excludes:
            if not isinstance(self.excludes, list) or not all(map(lambda a: isinstance(a, unicode), self.excludes)):
                raise JsonSchemaError(dict(msg='excludes attribute must be list of string'))

    def _validate(self, value):
        if not self.optional and value == None:
            raise JsonSchemaError(dict(msg=u'null is not allowed'))
        elif self.optional and value == None:
            return
        if not isinstance(value, unicode):
            raise JsonSchemaError(dict(msg=u'value should be $type', type='string'), value, '')
        if self.minLength != None and self.minLength > len(value):
            raise JsonSchemaError(dict(msg=u'value should longer than $len', len=self.minLength))
        if self.maxLength != None and self.maxLength < len(value):
            raise JsonSchemaError(dict(msg=u'value should shorter than $len', len=self.maxLength))
        if self.pattern is not None:
            import re
            c = re.compile('^(' + self.pattern + ')$')
            if not c.match(value):
                raise JsonSchemaError(dict(msg=u'value does not matched to $pattern', pattern=self.pattern))
        if self.excludes:
            if value in self.excludes:
                raise JsonSchemaError(dict(msg=u'value matched to exclusion pattern: $pattern', pattern='|'.join(self.excludes)))
                

    def intersect(self, another):
        if another.type != self.type:
            return NeverSchema()
        minLength = max(self.minLength, another.minLength)
        maxLength = min(self.maxLength, another.maxLength)
        if self.format is not None and another.format is not None and self.format != another.format:
            raise JsonSchemaError(dict(msg=u'Different format: $format1, $format2', format1=self.format, format2=another.format))
        if self.profile is not None and another.profile is not None and self.profile != another.profile:
            raise JsonSchemaError(dict(msg=u'Different profile: $profile1, $profile2', profile1=self.profile, profile2=another.profile))
        if self.pattern is not None and another.pattern is not None and self.pattern != another.pattern:
            raise JsonSchemaError(dict(msg=u'Different pattern: $pattern1, $pattern2', pattern1=self.pattern, pattern2=another.pattern))
        excludes = []
        if self.excludes:
            if another.excludes:
                excludes = list(set(self.excludes).union(set(another.excludes)))
            else:
                excludes = self.excludes
        opts = {
            'minLength': minLength,
            'maxLength': maxLength,
            'format': self.format or another.format,
            'profile': self.profile or another.profile,
            'pattern': self.pattern or another.pattern,
            'excludes': self.excludes,
        }
        return self.clone(opts)
        
    def _convert(self, value):
        if value == None or isinstance(value, unicode):
            return value
        elif isinstance(value, basestring):
            return unicode(value)
        else:
            raise JsonSchemaError(dict(msg=u'An error occuered while converting to $type', type=self.type), unicode(repr(value)), '')

    def dump(self, depth, node=[]):
        return u'string'

    @property
    def type(self):
        return u'string'



