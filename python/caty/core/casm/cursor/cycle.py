#coding:utf-8
from caty.core.casm.cursor.base import *

class CycleDetecter(SchemaBuilder):
    def __init__(self, module):
        SchemaBuilder.__init__(self, module)
        self._current_node = None

    def _visit_root(self, node):
        if not self._current_node:
            self._current_node = node
            node.body.accept(self)
            self._current_node = None
        else:
            node.body.accept(self)
        return node

    def _visit_scalar(self, node):
        if isinstance(node, TypeReference):
            # 型引数の中に自身への言及があり、それが型パラメータを取る場合、
            # コンパイル不能なのでエラーメッセージを出す。
            for t in node.type_args:
                if t.name == self._current_node.name:
                    if t.type_args:
                        raise Exception(ro.i18n.get(u'Self-reference that took type parameter in type argument was detected'))
            if node.name != self._current_node.name: return node
            args_num = len(node.type_args)
            if args_num == 0:
                return node #型引数なしは有限のサイクル
            else:
                # 検出されたサイクル数
                # サイクル数はパラメータ毎に管理される。
                # type foo<x, y>なら[0, 0]というリストがサイクル初期状態である。
                # {x=x, y=y}という形式の場合、各サイクルの値0である。
                # {x=y, y=x}という形式の場合、各サイクルの値は1である。
                # {x=F}という形式の場合、x⊆Fならば即座にエラーとなる。
                # y⊆Fの場合、サイクルのyの値は2となる。
                # すべてのサイクルの値が0ないし1であるか、
                # サイクルが2のノードが一つかつ残りが0であれば、無限展開にはならない。
                cycles = [0 for n in range(len(self._current_node.type_params))]
                for num, param in enumerate(self._current_node.type_params):
                    if args_num < num: pass
                    rest = []
                    for _, a in enumerate(node.type_args):
                        if _ == num:
                            t = a
                        else:
                            rest.append(a)
                    if t.type != '__variable__':
                        target = _AlphaTransformer(t).visit(t)
                        if _VariableFinderInRecType(param.var_name).visit(target):
                            #cycles[num] = max(cycles[num], 2)
                            raise Exception(ro.i18n.get(u'Infinite expansion was detected'))
                        else:
                            for i, p in enumerate(self._current_node.type_params):
                                if p != param:
                                    if _VariableFinderInRecType(p.name).visit(target):
                                        cycles[i] = max(cycles[i], 2)
                    else:
                        if t.name != param.var_name:
                            for i, p in enumerate(self._current_node.type_params):
                                if p != param:
                                    if t.name == p.name:
                                        cycles[i] = max(cycles[i], 1)
                    for r in rest:
                        target = _AlphaTransformer(r).visit(r)
                        if _VariableFinderInRecType(param).visit(target):
                            cycles[num] = max(cycles[num], 2)
                            #cycles.append(param.name)
                if (all(map(lambda c: c<=1, cycles)) or
                    (cycles.count(2) == 1 and all(map(lambda c: c==0 or c==2, cycles)))
                   ):
                    return node
                raise Exception(ro.i18n.get(u'Infinite expansion was detected'))
        return node

class _VariableFinderInRecType(TreeCursor):
    def __init__(self, param_name):
        self._param_name = param_name
        self._is_in_composed_type = []

    def _visit_root(self, node):
        return node.body.accept(self)

    def _visit_scalar(self, node):
        if isinstance(node, TypeReference):
            return node.body.accept(self)
        elif isinstance(node, TypeVariable):
            if node.name == self._param_name:
                if self._is_in_composed_type:
                    return node.name
        return

    def _visit_option(self, node):
        return node.body.accept(self)

    def _visit_tag(self, node):
        return node.body.accept(self)

    def _visit_array(self, node):
        self._is_in_composed_type.append(0)
        try:
            for n in node:
                v = n.accept(self)
                if v:
                    return v
        finally:
            self._is_in_composed_type.pop()

    _visit_bag = _visit_array

    def _visit_object(self, node):
        self._is_in_composed_type.append(0)
        try:
            for k, v in node.items():
                r = v.accept(self)
                if r:
                    return r
        finally:
            self._is_in_composed_type.pop()

    def _visit_enum(self, node):
        pass

    def _visit_intersection(self, node):
        s = node.left.accept(self)
        if s:
            return s
        s = node.right.accept(self)
        if s:
            return s

    def _visit_updator(self, node):
        s = node.left.accept(self)
        if s:
            return s
        s = node.right.accept(self)
        if s:
            return s

    def _visit_union(self, node):
        s = node.left.accept(self)
        if s:
            return s
        s = node.right.accept(self)
        if s:
            return s

class _AlphaTransformer(TreeCursor):
    def __init__(self, ref_node):
        params = []
        if isinstance(ref_node, TypeReference):
            for a in ref_node.type_args:
                params.append(TypeParam(a.name, None))
        self.params = params
        self.translation_map = {}

    def _visit_root(self, node):
        for n, p in enumerate(node.type_params):
            self.translation_map[p.name] = self.params[n].name
        return NamedSchema(node.name, 
                           [TypeParam(self.translation_map[p.name], None) for p in node.type_params], 
                           node.body.accept(self), 
                           node.module)

    def _visit_scalar(self, node):
        if isinstance(node, TypeReference):
            if isinstance(node.body, NamedSchema):
                r = TypeReference(node.name, node.type_args, node.module)
                r.body = node.body.accept(self)
                return r
            else:
                return node
        elif isinstance(node, TypeVariable):
            return TypeVariable(self.translation_map.get(node.name, node.name), node.type_args, node.options, node._module)
        return node

    def _visit_option(self, node):
        return node.body.accept(self)

    def _visit_tag(self, node):
        return node.body.accept(self)

    def _visit_array(self, node):
        r = []
        for n in node:
            r.append(n.accept(self))
        return ArraySchema(r)

    def _visit_bag(self, node):
        r = []
        for n in node:
            r.append(n.accept(self))
        return BagSchema(r)

    def _visit_object(self, node):
        o = {}
        for k, v in node.items():
            o[k] = v.accept(self)
        w = node.wildcard.accept(self)
        return ObjectSchema(o, w)

    def _visit_enum(self, node):
        return node

    def _visit_intersection(self, node):
        return IntersectionSchema(
            node.left.accept(self),
            node.right.accept(self)
        )

    def _visit_updator(self, node):
        return UpdatorSchema(
            node.left.accept(self),
            node.right.accept(self)
        )

    def _visit_union(self, node):
        return UnionSchema(
            node.left.accept(self),
            node.right.accept(self)
        )



