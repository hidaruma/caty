# -*- coding: utf-8 -*- 
# 
#
from caty.command import Command
import caty.jsontools as json

def _result(tagged, result):
    if tagged:
        return json.tagged(result, None)
    else:
        return result

class Or(Command):
    def setup(self, opts):
        self.tagged = opts['tag']

    def execute(self, input):
        for item in input:
            if item == u'True':
                return _result(self.tagged, u'True')
        return _result(self.tagged, u'False')

class And(Command):
    def setup(self, opts):
        self.tagged = opts['tag']

    def execute(self, input):
        for item in input:
            if item == u'False':
                return _result(self.tagged, u'False')
        return _result(self.tagged, u'True')

class TagOr(Command):
    def setup(self, opts):
        self.tagged = opts['tag']

    def execute(self, input):
        for item in input:
            if json.tag(item) == 'True':
                return _result(self.tagged, u'True')
        return _result(self.tagged, u'False')

class TagAnd(Command):
    def setup(self, opts):
        self.tagged = opts['tag']

    def execute(self, input):
        for item in input:
            if json.tag(item) == 'False':
                return _result(self.tagged, u'False')
        return _result(self.tagged, u'True')

class BAnd(Command):
    def setup(self, opts):
        self.tagged = opts['tag']

    def execute(self, input):
        for item in input:
            if item == False:
                return _result(self.tagged, u'False')
        return _result(self.tagged, u'True')

class BOr(Command):
    def setup(self, opts):
        self.tagged = opts['tag']

    def execute(self, input):
        for item in input:
            if item == True:
                return _result(self.tagged, u'True')
        return _result(self.tagged, u'False')
