#coding: utf-8
from caty.core.command import Builtin
from caty.util.cx import creole2html

name = 'text'
schema = u"""

"""

class Chop(Builtin):

    def execute(self, input):
        return input.strip()

class Trim(Builtin):

    def setup(self, text):
        self.text= text

    def execute(self, input):
        while input.startswith(self.text):
            input = input[len(self.text):]
        while input.endswith(self.text):
            input = input[:-len(self.text)]
        return input

class Creole(Builtin):

    def execute(self, input):
        return creole2html(input)

class Join(Builtin):

    def setup(self, sep):
        self.sep = sep

    def execute(self, input):
        return self.sep.join(input)

class Concat(Builtin):


    def execute(self, input):
        return u''.join(input)

class ToUpper(Builtin):

    def execute(self, input):
        return input.upper()

class ToLower(Builtin):

    def execute(self, input):
        return input.lower()

class Split(Builtin):

    def setup(self, sep, num=0):
        self.num = num
        self.sep = sep

    def execute(self, input):
        if self.num:
            return input.split(self.sep, self.num)
        else:
            return input.split(self.sep)

class RSplit(Builtin):

    def setup(self, sep, num=0):
        self.num = num
        self.sep = sep

    def execute(self, input):
        if self.num:
            return input.rsplit(self.sep, self.num)
        else:
            return input.rsplit(self.sep)

from caty.jsontools import tagged
class RegMatch(Builtin):
    def setup(self, pattern):
        import re
        self.regexp = re.compile(pattern)

    def execute(self, input):
        m = self.regexp.search(input)
        if not m:
            return tagged(u'NG', input)
        else:
            return tagged(u'OK', 
                {
                    'src': input,
                    'group': m.group(),
                    'groups': list(m.groups()),
                }
            )

class VerifyChars(Builtin):
    def setup(self, opts):
        self.max = opts['max']

    def execute(self, input):
        r = []
        line = 1
        col = 0
        prev = 0
        for c in input:
            col += 1
            n = ord(c)
            if n > 127:
                pass
            elif n == 127:
                r.append(self._report(line, col, n))
            else:
                if n == 13:
                    line += 1
                    col = 0
                elif n == 10:
                    if prev != 13:
                        line += 1
                    col = 0
                elif n == 9:
                    pass
                else:
                    if n <= 31:
                        r.append(self._report(line, col, n))
            if len(r) >= self.max:
                break
            prev = n
        if r:
            return tagged(u'NG', r)
        else:
            return tagged(u'OK', r)

    def _report(self, line, col, code):
        return {
            'location': u'Line %d, Col %d' % (line, col),
            'code': unicode(str(hex(code)))
        }

