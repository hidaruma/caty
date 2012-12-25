from treeselector.parser import TreeSelectorParser
from treeselector.operator import BaseOperatorFactory

class BaseTreeSelectorFactory(object):
    def __init__(self, walker, operator_factory=BaseOperatorFactory()):
        self.__walker = walker
        self.__operator_factory = operator_factory

    def get_parser(self):
        return TreeSelectorParser(self.__walker, self.__operator_factory)

    def make_selector(self, src):
        parser =self.get_parser() 
        return parser.run(src, auto_remove_ws=True)




