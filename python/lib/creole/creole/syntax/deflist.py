from topdown import *
from creole.syntax.base import BlockParser

class DefList(BlockParser):
    def __call__(self, seq):
        def item(seq):
            seq.parse('*')
            seq.parse(many1(' '))
            defn = seq.parse(until(['::', '\n']))
            seq.parse(option('\n'))
            seq.parse(many(' '))
            seq.parse('::')
            term = seq.parse(until(['*', '\n\n']))
            d = self.create_element('dt', None, self.inline.run(self._format(defn)))
            t = self.create_element('dd', None, self.inline.run(self._format(term)))
            return d,t 
        items = many1(item)(seq)
        l = []
        for d, t in items:
            l.append(d)
            l.append(t)
        return self.create_element('dl', None, l)

