# -*- coding: utf-8 -*- 
# 
#
from caty.command import Command
from cStringIO import StringIO 
try:
    import Image 
except ImportError:
    print "Cannot use Image library."
    Image = None


class ShowImage(Command):

    def execute(self, input):
        im = Image.open(StringIO(input))
        im.show()
        return None
