# -*- coding: utf-8 -*- 
# 
#
from caty.command import Command

import encodings
class Encodings(Command):
    def execute(self):
        return [unicode(x) for x in set(encodings.aliases.aliases.keys())]
