# -*- coding: utf-8 -*- 
# 
#
from caty.command import Command
import base64

class Encode(Command):
    def execute(self, input):
        return unicode(base64.b64encode(input))

class Decode(Command):
    def execute(self, input):
        return base64.b64decode(input)
