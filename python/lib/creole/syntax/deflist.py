from __future__ import absolute_import
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
            dts = []
            while not seq.eof:
                seq.parse('::')
                term = seq.parse(until(['*', '::', '\n\n']))
                t = self.create_element('dd', None, self.inline.run(self._format(term)))
                dts.append(t)
                if peek(option('::'))(seq):
                    continue
                break
            d = self.create_element('dt', None, self.inline.run(self._format(defn)))
            return d, dts 
        items = many1(item)(seq)
        l = []
        for d, ts in items:
            l.append(d)
            for t in ts:
                l.append(t)
        return self.create_element('dl', None, l)

