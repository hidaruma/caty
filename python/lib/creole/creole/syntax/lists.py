from topdown import *
from creole.syntax.base import BlockParser

class List(BlockParser):
    def __init__(self, syntax, level, symbol, another, factory=None):
        BlockParser.__init__(self, syntax, factory)
        self.__syntax = syntax
        self.level = level
        self.symbol = symbol
        self.another = another

    def __call__(self, seq):
        level = self.level
        symbol = self.symbol * level
        another = self.another * level
        def list_item(seq):
            seq.parse(Regex(' *'+(symbol.replace('*', '\\*'))))
            if seq.current == symbol[0]:
                raise ParseFailed(seq, self)
            seq.parse(many(' '))
            node = [seq.parse(until('\n'))]
            if seq.eof:
                return self.create_element('li', None, node)
            seq.parse('\n')
            seq.parse(many(' '))
            next = self.symbol * (level + 1)
            another_next = self.another * (level + 1)
            not_next = Regex(r'\*{1,%d}[^*]|#{1,%d}[^#]' % (level, level))
            while True:
                if seq.peek(option('\n')) or seq.eof or seq.peek(option(not_next)):
                    return self.create_element('li', None, self.inline.run(self._format('\n'.join(node))))
                elif seq.peek(option(next)):
                    next_parser = try_(self.__class__(self.__syntax, level + 1, self.symbol, self.another, self._element_factory))
                    return self.create_element('li', None, self.inline.run(self._format('\n'.join(node))) + [next_parser(seq)])
                elif seq.peek(option(another_next)):
                    next_parser = try_(self.__class__(self.__syntax, level + 1, self.another, self.symbol, self._element_factory))
                    return self.create_element('li', None, self.inline.run(self._format('\n'.join(node))) + [next_parser(seq)])
                else:
                    node.append(seq.parse(until('\n')))
                    if seq.peek(option('\n')):
                        seq.parse('\n')
                        seq.parse(many(' '))
        items = many(list_item)(seq)
        if not items:
            raise ParseFailed(seq, self)
        if self.symbol == '*':
            tag = 'ul'
        elif self.symbol == '#':
            tag = 'ol'
        return self.create_element(tag, None, items)

OrderedList = lambda i, f=None: List(i, 1, '#', '*', f)
UnorderedList = lambda i, f=None: List(i, 1, '*', '#', f)

