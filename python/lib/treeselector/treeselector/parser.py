from topdown import *
from treeselector.walker import (SimpleSelector, 
                                 FilterSelector, 
                                 FilterOperator, 
                                 ChildOperator, 
                                 UnionOperator,
                                 PositionSpecSelector,
                                 NodePositionSelector
                                 )

class TreeSelectorParser(Parser):
    NONE = 0
    ID = 1
    CLASS = 2
    OPERATORS = (u'#', u'.')
    def __init__(self, walker):
        self.__walker = walker
        self.__mode = self.NONE

    def __call__(self, seq):
        r = self.pos_spec_selector(seq)
        if not seq.eof:
            raise ParseFailed(seq, self)
        return r 

    def pos_spec_selector(self, seq):
        k = option(choice(keyword(u'first'), keyword(u'last')))(seq)
        if k is not None:
            S(u'(')(seq)
            n = self.node_pos_selector(seq)
            S(u')')(seq)
            return PositionSpecSelector(n, k)
        else:
            n = option(self.node_pos_selector)(seq)
            if n is not None:
                return n
            else:
                return self.node_selector(seq)


    def node_pos_selector(self, seq):
        k = option(choice(keyword(u'before'), keyword(u'after'), keyword('child')))(seq)
        if k is not None:
            S(u'(')(seq)
            n = self.node_selector(seq)
            S(u')')(seq)
            return NodePositionSelector(n, k)
        else:
            return self.node_selector(seq)

    def node_selector(self, seq):
        return chainl(self.term, self.union_operator)(seq)

    def term(self, seq):
        return chainl(choice(self.all_selector, self.name_selector), self.child_operator)(seq)

    def all_selector(self, seq):
        if peek(option(choice(*self.OPERATORS)))(seq):
            pass
        else:
            S(u'*')(seq)
        s = SimpleSelector(self.__walker.select_all)
        return self.sub_selector(seq, s)

    def sub_selector(self, seq, s):
        op = option(choice(*self.OPERATORS))(seq)
        if op == u'#':
            i = self.parse_id(seq)
            fs = FilterSelector(self.__walker.filter_id, i)
            return FilterOperator(s, fs)
        elif op == u'.':
            c = self.parse_class(seq)
            fs = FilterSelector(self.__walker.filter_class, c)
            return FilterOperator(s, fs)
        else:
            return s

    def name_selector(self, seq):
        name = self.parse_name(seq)
        s = SimpleSelector(self.__walker.select_name, name)
        return self.sub_selector(seq, s)

    def parse_name(self, seq):
        return seq.parse(Regex(u'[a-zA-Z_][a-zA-Z0-9_]*'))

    def parse_class(self, seq):
        return seq.parse(Regex(u'[a-zA-Z_][a-zA-Z0-9_]*'))

    def parse_id(self, seq):
        return seq.parse(Regex(u'[a-zA-Z_][a-zA-Z0-9_]*'))

    def union_operator(self, seq):
        S(',')(seq)
        return UnionOperator

    def child_operator(self, seq):
        S('>')(seq)
        return ChildOperator
