from __future__ import absolute_import
from topdown import *
from creole.syntax.base import BlockParser

class Paragraph(BlockParser):

    def __call__(self, seq):
        t = []
        t.append(seq.parse(until('\n')))
        seq.next()
        if seq.current != '\n':
            while self._not_next_block(seq):
                t.append(seq.parse(until('\n')))
                seq.next()
                if seq.current == '\n':
                    break
        return self.create_element('p', None, self.inline.run(self._format('\n'.join(t))))

    def _not_next_block(self, seq):
        return not (self._is_ul(seq) or 
                self._is_ol(seq) or 
                self._is_table(seq) or 
                self._is_quote(seq) or
                self._is_pre(seq) or
                self._is_heading(seq) or
                self._is_horizonal(seq) or
                self._other_element(seq))

    def _is_ul(self, seq):
        return seq.peek(option(Regex(r' *\*[^*]')))

    def _is_ol(self, seq):
        return seq.peek(option(Regex(r' *#[^#]')))

    def _is_table(self, seq):
        return seq.peek(option(Regex(r' *\|')))

    def _is_quote(self, seq):
        return seq.peek(option(Regex(r' *\|>>')))

    def _is_heading(self, seq):
        return seq.peek(option('='))

    def _is_horizonal(self, seq):
        return seq.peek(option('----'))

    def _is_pre(self, seq):
        return seq.peek(option('{{{'))

    def _other_element(self, seq):
        return False





