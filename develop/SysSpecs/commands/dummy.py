# -*- coding: utf-8 -*- 
# 
#
from caty.command import Command
from caty.core.exception import throw_caty_exception

class NotImplemented(Command):
    def execute(self):
        throw_caty_exception('NotImplemented',
                            u"This command or feature is not implemented"
                             )


