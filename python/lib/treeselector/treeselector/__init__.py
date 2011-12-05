from treeselector.parser import TreeSelectorParser

class TreeSelectorFactory(object):
    def __init__(self, walker):
        self.__walker = walker

    def make_selector(self, src):
        parser = TreeSelectorParser(self.__walker)
        return parser.run(src, auto_remove_ws=True)




