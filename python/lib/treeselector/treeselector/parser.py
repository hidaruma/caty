from topdown import *

class TreeSelectorParser(Parser):
    OPERATORS = (u'#', u'.')
    def __init__(self, walker, operator_factory):
        self.__walker = walker
        self.__operator_factory = operator_factory

    def __call__(self, seq):
        r = self.pos_spec_selector(seq)
        if not seq.eof:
            raise ParseFailed(seq, self)
        return r 

    def pos_spec_selector(self, seq):
        k = self.position_name(seq)
        if k is not None:
            S(u'(')(seq)
            n = self.node_pos_selector(seq)
            S(u')')(seq)
            return self.__operator_factory.position_spec_selector(n, k)
        else:
            n = option(self.node_pos_selector)(seq)
            if n is not None:
                return n
            else:
                return self.node_selector(seq)

    def node_pos_selector(self, seq):
        k = self.node_position_name(seq) 
        if k is not None:
            S(u'(')(seq)
            n = self.node_selector(seq)
            S(u')')(seq)
            return self.__operator_factory.node_position_selector(n, k)
        else:
            return self.node_selector(seq)

    def node_selector(self, seq):
        return chainl(self.term, self.union_operator)(seq)

    def term(self, seq):
        return chainl(choice(self.all_selector, self.name_selector), self.child_operator)(seq)

    def all_selector(self, seq):
        if peek(option(choice(u':', *self.OPERATORS)))(seq):
            pass
        else:
            S(u'*')(seq)
        s = self.__operator_factory.simple_selector(self.__walker.select_all)
        return self.sub_selector(seq, s)

    def sub_selector(self, seq, base):
        s = self._class_or_id_selector(seq, base)
        if option(S(':'))(seq):
            i = self.parse_pseudo_class(seq)
            return self.__operator_factory.pseudo_class_selector(s, i)
        else:
            return s

    def _class_or_id_selector(self, seq, s):
        op = option(choice(*self.OPERATORS))(seq)
        if op == u'#':
            i = self.parse_id(seq)
            fs = self.__operator_factory.filter_selector(self.__walker.filter_id, i)
            return self.__operator_factory.filter_operator(s, fs)
        elif op == u'.':
            c = self.parse_class(seq)
            fs = self.__operator_factory.filter_selector(self.__walker.filter_class, c)
            return self.__operator_factory.filter_operator(s, fs)
        else:
            return s

    def name_selector(self, seq):
        name = self.parse_name(seq)
        s = self.__operator_factory.simple_selector(self.__walker.select_name, name)
        return self.sub_selector(seq, s)

    def parse_name(self, seq):
        return seq.parse(Regex(u'[a-zA-Z_][a-zA-Z0-9_]*'))

    def parse_class(self, seq):
        return seq.parse(Regex(u'[a-zA-Z_][a-zA-Z0-9_]*'))

    def parse_id(self, seq):
        return seq.parse(Regex(u'[a-zA-Z_][a-zA-Z0-9_]*'))

    def parse_pseudo_class(self, seq):
        return choice(keyword('first-child'), keyword('last-child'), keyword('root'))(seq)

    def node_position_name(self, seq):
        return option(choice(keyword(u'before'), keyword(u'after'), keyword('child')))(seq)

    def position_name(self, seq):
        return option(choice(keyword(u'first'), keyword(u'last')))(seq)

    def union_operator(self, seq):
        S(',')(seq)
        return self.__operator_factory.union_operator

    def child_operator(self, seq):
        S('>')(seq)
        return self.__operator_factory.child_operator

