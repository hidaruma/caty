#coding:utf-8
from caty.core.casm.cursor.base import *
from caty.core.casm.cursor.dump import TreeDumper
from caty.core.exception import throw_caty_exception

class TypeNormalizer(TreeCursor):
    def __init__(self, module):
        self.module = module

    def _visit_root(self, node):
        return self.visit(node)

    def visit(self, node):
        ue = UndefinedEraser(self.module)
        ol = OptionLifter(self.module)
        tc = TypeCalcurator(self.module)
        normalized = tc.visit(ol.visit(ue.visit(node)))
        nc = NeverChecker(self.module)
        nc.visit(normalized)
        vc = VariableChecker(self.module)
        vc.visit(normalized)
        return normalized

    def _visit_kind(self, node):
        return node

class _SubNormalizer(SchemaBuilder):
    def _visit_root(self, node):
        try:
            body = node.body.accept(self)
        except:
            print u'[DEBUG]', node.name
            raise
        node._schema = body
        return node

    @apply_annotation
    def _visit_object(self, node):
        o = {}
        for k, v in node.items():
            try:
                o[k] = v.accept(self)
            except:
                print '[DEBUG]', k
                raise
        try:
            w = node.wildcard.accept(self)
        except:
            print '[DEBUG] *'
            raise
        return ObjectSchema(o, w, node.options)

class UndefinedEraser(_SubNormalizer):
    @apply_annotation
    def _visit_scalar(self, node):
        if isinstance(node, UndefinedSchema):
            return OptionalSchema(NeverSchema())
        else:
            return node

class OptionLifter(_SubNormalizer):
    def __init__(self, *args):
        _SubNormalizer.__init__(self, *args)

    def _visit_scalar(self, node):
        return node

    @apply_annotation
    def _visit_union(self, node):
        l = node.left.accept(self)
        r = node.right.accept(self)
        o1 = False
        o2 = False
        if l.optional:
            l = l.body.accept(self)
            o1 = True
        if r.optional:
            r = r.body.accept(self)
            o2 = True
        i = UnionSchema(l, r, node.options)
        if o1 or o2:
            i = OptionalSchema(i)
        return i

class TypeCalcurator(_SubNormalizer):
    def __init__(self, module):
        _SubNormalizer.__init__(self, module)
        self.history = set()
        self.traced = set()
    
    @apply_annotation
    def _visit_scalar(self, node):
        if isinstance(node, TypeReference):
            if node in self.history:
                return node
            self.history.add(node)
            try:
                node.body = node.body.accept(self)
            except:
                print '[DEBUG]', node.name
        return node

    @apply_annotation
    def _visit_union(self, node):
        l = node.left.accept(self)
        r = node.right.accept(self)
        if l.type == 'never':
            return r
        elif r.type == 'never':
            return l
        elif l.type == 'enum' and r.type == 'enum':
            return l.union(self._dereference(r))
        else:
            return UnionSchema(l, r, node.options)

    @apply_annotation
    def _visit_intersection(self, node):
        l = node.left.accept(self)
        r = node.right.accept(self)
        if l.optional:
            l = l.body
        if r.optional:
            r = r.body
        lt = l.type
        rt = r.type
        # 型変数の場合はデフォルトもしくはカインドを元に計算する。
        # XXX:現状デフォルトのみ実装
        if lt == '__variable__':
            d = self._dereference(l)._default_schema
            if d:
                lt = d.type
                l = self._dereference(d)
        if rt == '__variable__':
            d = self._dereference(r)._default_schema
            if d:
                rt = d.type
                r = self._dereference(d)
        # 一方がneverであれば演算結果はnever
        if lt == 'never' or rt == 'never':
            res = NeverSchema()
        # univは&演算では単位元
        elif lt == 'univ':
            res = r
        elif rt == 'univ':
            res = l
        # フォーリンデータはどうしようもないのでnever
        elif lt == 'foreign' or rt == 'foreign':
            res = NeverSchema()
        elif lt == 'undefined' or rt == 'undefined':
            if lt == rt:
                res = UndefinedSchema()
            else:
                res = NeverSchema()
        # anyはforeignとundefined以外に対して単位元
        elif lt == 'any':
            res = r
        elif rt == 'any':
            res = l
        # ユニオン演算
        elif lt == '__union__' and rt == '__union__':
            l = self._dereference(l)
            r = self._dereference(r)
            xl = self.__intersect(l.left, r.left)
            xr = self.__intersect(l.right, r.left)
            yl = self.__intersect(l.left, r.right)
            yr = self.__intersect(l.right, r.right)
            comb = filter(lambda x: x.type != 'never', [xl, xr, yl, yr])
            length = len(comb)
            if length == 0:
                res = NeverSchema()
            elif length == 1:
                res = comb[0]
            else:
                import operator
                res = reduce(operator.or_, comb)
        elif lt == '__union__':
            l = self._dereference(l)
            r = self._dereference(r)
            xl = self.__intersect(l.left, r)
            xr = self.__intersect(l.right, r)
            comb = filter(lambda x: x.type != 'never', [xl, xr])
            length = len(comb)
            if length == 0:
                res = NeverSchema()
            elif length == 1:
                res = comb[0]
            else:
                res = comb[0] | comb[1]
        elif rt == '__union__':
            l = self._dereference(l)
            r = self._dereference(r)
            xl = self.__intersect(l, r.left)
            xr = self.__intersect(l, r.right)
            comb = filter(lambda x: x.type != 'never', [xl, xr])
            length = len(comb)
            if length == 0:
                res = NeverSchema()
            elif length == 1:
                res = comb[0]
            else:
                res = comb[0] | comb[1]
        elif lt.startswith('@'): # タグ型の場合はタグ名一致時は中身を計算
            if rt.startswith('@'): # 右辺がタグ型
                if lt != rt:
                    if lt == '@*!' or lt == '@*': 
                        # ワイルドカードタグ & 通常タグ
                        n = (self._dereference(l, True) & self._dereference(r, True)).accept(self)
                        res = TagSchema(r.tag, n)
                    elif  rt == '@*!' or rt == '@*':
                        # 通常タグ & ワイルドカードタグ 
                        n = (self._dereference(l, True) & self._dereference(r, True)).accept(self)
                        res = TagSchema(l.tag, n)
                    else:
                        res = NeverSchema()
                else:
                    # タグ名が一致
                    n = (self._dereference(l, True) & self._dereference(r, True)).accept(self)
                    res = TagSchema(r.tag, n.accept(self))
            else:
                if lt == '@*': 
                    # ワイルドカードタグ
                    n = (self._dereference(l, True) & r).accept(self)
                    res = n
                else:
                    if lt == 'integer': lt = 'number'
                    if rt == 'integer': rt = 'number'
                    if '@' + rt == lt:
                        res = (self._dereference(l, True) & r).accept(self)
                    else:
                        res = NeverSchema()
        elif rt.startswith('@'):
            if rt == u'@*':
                n = (l & self._dereference(r, True)).accept(self)
                res = n
            else:
                if lt == 'integer': lt = 'number'
                if rt == 'integer': rt = 'number'
                if '@' + lt == rt:
                    res = (l & self._dereference(r, True)).accept(self)
                else:
                    res = NeverSchema()
        else:
            # どちらもタグ型でない場合
            if lt == rt or (lt in ('number', 'integer') and rt in ('number', 'integer')):
                # デフォルト指定された型変数が含まれている場合、そちらを返す。
                if isinstance(l, TypeVariable):
                    return l
                if isinstance(r, TypeVariable):
                    return r
                # 同じ型であればそのまま計算(numberとintegerも)
                if lt == rt == 'object':
                    if self.__exclusive_pseudotag(l, r):
                        return NeverSchema()
                res = l.intersect(r).accept(self)
            elif lt == 'enum' and isinstance(r, Scalar):
                res = self._intersect_enum_and_scalar(self._dereference(l), r)
            elif rt == 'enum' and isinstance(l, Scalar):
                res = self._intersect_enum_and_scalar(self._dereference(r), l)
            elif set([lt, rt]) == set([u'null', u'void']):
                res = l
            else:
                res = NeverSchema()
        if (node.left.optional and node.right.optional) or (lt == 'univ' and node.right.optional) or (rt == 'univ' and node.left.optional):
            res = OptionalSchema(res)
        return res

    def __intersect(self, l, r):
        l = self._dereference(l)
        r = self._dereference(r)
        if l == r:
            return l
        if isinstance(l, EnumSchema):
            if isinstance(r, OperatorSchema):
                x = (l & r.left).accept(self)
                y = (l & r.right).accept(self)
                return r.operate(x, y).accept(self)
            else:
                return l.intersect(self._dereference(r))
        elif isinstance(r, EnumSchema):
            if isinstance(r, OperatorSchema):
                x = (l & r.left).accept(self)
                y = (l & r.right).accept(self)
                return r.operate(x, y)
            else:
                return r.intersect(self._dereference(l))
        else:
            if l in self.history and r in self.history:
                return NeverSchema() # 再帰的定義で止まってしまうのを修正
            return (l & r).accept(self)

    def _intersect_enum_and_scalar(self, enum, scalar):
        r = []
        for e in enum:
            try:
                scalar.validate(e)
            except:
                pass
            else:
                r.append(e)
        if not r:
            return NeverSchema()
        return EnumSchema(r, enum.options)

    def __exclusive_pseudotag(self, a, b):
        if a.type != 'object':
            return False
        p1 = self.__traverse_pseudotag(a)
        p2 = self.__traverse_pseudotag(b)
        if p1 and p2 and p1.name and p2.name:
            return p1.exclusive(p2)
        return False

    def __traverse_pseudotag(self, o):
        if isinstance(o, TypeReference):
            if o.pseudoTag:
                return o.pseudoTag
            else:
                return self.__traverse_pseudotag(o.body)
        elif isinstance(o, NamedSchema):
            return self.__traverse_pseudotag(o.body)
        elif isinstance(o, ObjectSchema):
            return o.pseudoTag
        else:
            return None

    @apply_annotation
    def _visit_updator(self, node):
        l = node.left
        r = node.right
        if self.__can_not_merge(l, r):
            t1 = l.type if l.type != '__variable__' else ro.i18n.get(u'type variable($name)', name=l.name)
            t2 = r.type if r.type != '__variable__' else ro.i18n.get(u'type variable($name)', name=r.name)
            raise Exception(ro.i18n.get(u'unsupported operand types for $op: $type1, $type2', type1=str(t1), type2=t2, op='++'))

        l = l.accept(self)
        r = r.accept(self)
        n = l.update(r)
        return n.accept(self)

    def __can_not_merge(self, l, r):
        if '__variable__' in (l.type, r.type):
            return True

        if l.type != r.type:
            if len(set([l.type, r.type]).union(set(['__merging__', '__intersection__', 'object']))) != 3:
                if l.type not in ('integer', 'number') and r.type not in ('integer', 'number'):
                    return True
        return False

    @apply_annotation
    def _visit_unary_op(self, node):
        res = node.body.accept(self)
        body = dereference(res)
        if body.type != 'object':
           raise CatyException(u'SCHEMA_COMPILE_ERROR', 
                u'Unsupported operand type for $op: $type',
                op=node.operator, type=body.type)

        if node.operator == u'open':
            body.wildcard = AnySchema()
        elif node.operator == u'close':
            body.wildcard = NeverSchema()
        else:
            return node.path.select(body).next()
        return res

class NeverChecker(_SubNormalizer):
    def __init__(self, module, safe=False, into_optional=False):
        _SubNormalizer.__init__(self, module)
        self.safe = safe
        self.into_optional = into_optional

    def _visit_scalar(self, node):
        if node.type == 'never' and not node.optional:
            return [[u'never']]

    def _visit_root(self, node):
        r = node.body.accept(self)
        if r:
            paths = []
            for p in r:
                if len(p) >= 2:
                    paths.append('$.' + '.'.join(p[:-1]) + ':' + p[-1])
                else:
                    paths.append(p[0])
            if not self.safe:
                raise Exception(ro.i18n.get(u'Type representation is never: $typedef', typedef='\n'.join(paths)))
        return r

    def _visit_option(self, node):
        if not self.into_optional:
            return None
        else:
            return node.body.accept(self)

    def _visit_enum(self, node):
        for e in node:
            if isinstance(e, SchemaBase):
                r = e.accept(self)
                if r:
                    return r

    def _visit_object(self, node):
        never_found = []
        for k, v in node.items():
            r = v.accept(self)
            if r:
                for p in r:
                    never_found.append([k] + p)
        return never_found

    def _visit_array(self, node):
        never_found = []
        for k, v in enumerate(node):
            r = v.accept(self)
            if r:
                for p in r:
                    never_found.append([str(k)] + p)
        return never_found

    def _visit_bag(self, node):
        never_found = []
        for k, v in enumerate(node):
            r = v.accept(self)
            if r:
                for p in r:
                    never_found.append([str(k)] + p)
        return never_found

    def _visit_intersection(self, node):
        assert False, TreeDumper().visit(node)

    def _visit_union(self, node):
        # タイミングの関係上、ノーマライズ後のユニオンの排他性チェックはここで
        from operator import truth
        tc = TypeCalcurator(self.module)
        nodes = self.__flatten_union(node)
        unions = [(a, b) for a in nodes for b in nodes if a != b]
        for u in unions:
            o = u[0] & u[1]
            c = tc.visit(o)
            if c.optional:
                c = c.body
            is_never = truth(c.accept(self))
            if is_never:
                pass
            else:
                throw_caty_exception('CompileError', ro.i18n.get(u'types are not exclusive: $type', type=TreeDumper().visit(node)))
            a = u[0].accept(self)
            b = u[1].accept(self)
            if a and b:
                return a

        return []

    def __flatten_union(self, node):
        r = []
        if node.left.type == '__union__':
            r.extend(self.__flatten_union(self._dereference(node.left)))
        else:
            r.append(node.left)
        if node.right.type == '__union__':
            r.extend(self.__flatten_union(self._dereference(node.right)))
        else:
            r.append(node.right)
        return r

    def _visit_updator(self, node):
        assert False, TreeDumper().visit(node)

    def _visit_tag(self, node):
        return node.body.accept(self)

    def _visit_pseudo_tag(self, node):
        assert False

    def _visit_function(self, node):
        assert False


class VariableChecker(_SubNormalizer):
    def __init__(self, *args):
        _SubNormalizer.__init__(self, *args)
        self.__suspcious_var = []

    def _visit_scalar(self, node):
        if isinstance(node, TypeVariable):
            if node._schema is None and node._default_schema is None:
                if self.__suspcious_var and node.name in self.__suspcious_var[-1]:
                    raise CatyException(
                        u'SCHEMA_COMPILE_ERROR',
                        u'Type variable which neither instantiated nor a default value was given: $name', 
                        name=node.name)
        elif isinstance(node, TypeReference):
            var_list = zip(node.type_args, node.type_params)
            rest_params = node.type_params[len(var_list):]
            self.__suspcious_var.append([])
            for p in rest_params:
                self.__suspcious_var[-1].append(p.var_name)
            if self.__suspcious_var[-1]:
                node.body.accept(self)
            self.__suspcious_var.pop(-1)
        return node



