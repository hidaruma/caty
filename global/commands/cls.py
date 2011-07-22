# -*- coding: utf-8 -*-
from caty.command import Command
import sys

class Clear(Command):
    def execute(self):
        if sys.platform.startswith('win'):
            import win32cls
            win32cls.clear_screen()
        else:
            # とりあえずANSIエスケープシーケンスで
            sys.stdout.write("\x1b[2J\x1b[0;0H")
#            print u'%s ではこのコマンドは利用できません' % sys.platform

 
