# -*- coding: utf-8 -*- 
# 
from caty.command import Command
from caty.core.exception import throw_caty_exception
# throw_caty_exception(tag, message, error_class=None, error_id=None, stack_trace=None, **kwds):

class Dup(Command):
    def setup(self, count):
        self.count = count;

    def execute(self, input):
        l = []
        while self.count > 0 :
            l.append(input)
            self.count -= 1
        return l

class Nest(Command):
    def setup(self, opts):
        self.length = opts["length"];
        self.strict = opts["strict"];

    def execute(self, input):
        start = 0
        next = length = self.length
        limit = len(input)
        l = []
        while start < limit :
            if self.strict and (limit < next) :
                throw_caty_exception(u'InvalidInput', u'bad list length: ' + unicode(str(limit)))
            l.append(input[start:next])
            start += length
            next += length
        return l

class Flatten(Command):
    def execute(self, input):
        l = []
        for item in input:
            l[len(l):] = item
        return l

class Group(Command):
    def execute(self, input):
        r = {}
        i = 0
        while i < len(input) :
            item = input[i]
            key = item[0]
            if key in r :
                r[key].append(item)
            else:
                r[key] = [item]
            i += 1
        return r
