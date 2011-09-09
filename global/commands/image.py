# -*- coding: utf-8 -*- 
# 
#
from caty.command import Command
import Image 
from cStringIO import StringIO 

class ShowImage(Command):

    def execute(self, input):
        im = Image.open(StringIO(input))
        im.show()
        return None
