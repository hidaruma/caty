#coding:utf-8
from caty.core.casm.cursor.base import *

class DependencyAnalizer(TreeCursor):
    def __init__(self, module):
        self.module = module
        self.dependency_graph = set()
        self.history = set()

    def _visit_root(self, node):
        if node.module != self.module:
            self.dependency_graph.add((self.module, node.module))
        node.body.accept(self)
        return self.dependency_graph

    def _visit_scalar(self, node):
        if isinstance(node, TypeReference):
            if node.module != node.body.module:
                self.dependency_graph.add((node.module, node.body.module))
            if node in self.history:
                return 
            self.history.add(node)
            node.body.accept(self)

    def _visit_option(self, node):
        node.body.accept(self)

    def _visit_enum(self, node):
        pass

    def _visit_object(self, node):
        for k, v in node.items():
            v.accept(self)

    def _visit_array(self, node):
        for i in node:
            i.accept(self)

    def _visit_bag(self, node):
        for i in node:
            i.accept(self)

    def _visit_intersection(self, node):
        node.left.accept(self)
        node.right.accept(self)

    def _visit_union(self, node):
        node.left.accept(self)
        node.right.accept(self)

    def _visit_updator(self, node):
        node.left.accept(self)
        node.right.accept(self)

    def _visit_tag(self, node):
        node.body.accept(self)


