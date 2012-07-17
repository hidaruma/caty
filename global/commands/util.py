# -*- coding: utf-8 -*- 
# 
#
import random
from caty.command import Command

class RandIndex(Command):
    def setup(self, opts, length):
        self.to_string = opts.get(u'string', False)
        self.length = length

    def execute(self):
        n = random.randint(0, self.length - 1)
        return unicode(n) if self.to_string else n

def _rand_insert(lis, n1, n2):
    result = []
    n = len(lis)
    i = 0
    while i < (n - 1):
        result.append(lis[i])
        result.append(unicode(random.randint(n1, n2)))
        i += 1
    result.append(lis[n - 1])
    return ''.join(result)

class FillWildcard(Command):
    def execute(self, pattern):
        lislis = map(lambda x: x.split('*'), pattern.split('**'))
        result = _rand_insert(map(lambda lis: _rand_insert(lis, 100, 999), lislis), 1000, 9999)
        return result

