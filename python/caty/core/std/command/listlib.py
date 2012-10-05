# coding: utf-8
from caty.core.command import Builtin
from caty import UNDEFINED
from caty.core.spectypes import reduce_undefined

name = 'list'
schema =''

class Zip(Builtin):

    def execute(self, input):
        return map(list, zip(input[0], input[1]))

class Zip3(Builtin):

    def execute(self, input):
        return map(list, zip(input[0], input[1], input[2]))

class UnZip(Builtin):

    def execute(self, input):
        r1 = []
        r2 = []
        for x, y in input:
            r1.append(x)
            r2.append(y)
        return [r1, r2]

class UnZip3(Builtin):

    def execute(self, input):
        r1 = []
        r2 = []
        r3 = []
        for x, y, z in input:
            r1.append(x)
            r2.append(y)
            r3.append(z)
        return [r1, r2, r3]

class Length(Builtin):

    def execute(self, input):
        return len(reduce_undefined(input))

class Cycle(Builtin):

    def setup(self, times):
        self.times = times

    def execute(self, input):
        times = self.times
        return [input for i in range(times)]

class Enumerate(Builtin):

    def execute(self, input):
        r = []
        for a, b in enumerate(input):
            r.append([a, b])
        return r

class Sort(Builtin):

    def setup(self, opts):
        self.key = opts.get('key', None)
        self.rev = opts.get('reverse', False)

    def execute(self, input):
        r = input[:]
        if self.key:
            r.sort(key=lambda a:a[self.key], reverse=self.rev)
        else:
            r.sort(reverse=self.rev)
        return r

class Slice(Builtin):

    def setup(self, start, end=None):
        self.start = start
        self.end = end

    def execute(self, input):
        if self.end:
            return input[self.start:self.end]
        else:
            return input[self.start:]


class Concat(Builtin):
    def execute(self, input):
        l = []
        for item in input:
            l[len(l):] = item
        return l

from caty.jsontools import tagged
class Contains(Builtin):
    def setup(self, opts):
        self._boolean = opts['boolean']

    def execute(self, input):
        v = input[1] in input[0]
        if self._boolean:
            return v
        else:
            return tagged(u'True' if v else u'False', input)

class Tighten(Builtin):
    def execute(self, input):
        return filter(lambda s: s is not UNDEFINED, input)

class Range(Builtin):
    def setup(self, opts, start, end):
        self.upto = opts['up-to']
        self.start = start
        self.end = end

    def execute(self):
        offset = 1 if self.upto else 0
        return range(self.start, self.end + offset)

class Reverse(Builtin):
    def execute(self, l):
        return list(reversed(l))
    

