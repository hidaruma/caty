# -*- coding: utf-8 -*- 
# 
#
from caty.core.exception import throw_caty_exception
from caty.command import Command

class Slice(Command):
    def setup(self, start, end=None):
        self.start = start
        self.end = end

    def execute(self, input):
        if self.end:
            return input[self.start:self.end]
        else:
            return input[self.start:]

class SliceTo(Command):
    def setup(self, start, end=None):
        self.start = start
        self.end = end

    def execute(self, input):
        if self.end:
            return input[self.start:self.end + 1]
        else:
            return input[self.start:]


class Length(Command):
    def execute(self, input):
        return len(input)

class EncodeFromString(Command):
    def setup(self, encoding):
        self.encoding = encoding

    def execute(self, input):
        try:
            return input.encode(self.encoding)
        except LookupError:
            tag ='BadArg'
            msg = "unknown encoding: " + self.encoding
            throw_caty_exception(tag, msg)

        except UnicodeEncodeError:
            tag ='InvalidInput'
            msg = "unencodable"
            throw_caty_exception(tag, msg)

class DecodeToString(Command):
    def setup(self, encoding):
        self.encoding = encoding

    def execute(self, input):
        try:
            return input.decode(self.encoding)
        except LookupError:
            tag ='BadArg'
            msg = "unknown encoding: " + self.encoding
            throw_caty_exception(tag, msg)

        except UnicodeDecodeError:
            tag ='InvalidInput'
            msg = "undecodable"
            throw_caty_exception(tag, msg)
