#coding:utf-8
from caty.core.casm.cursor.base import *
from caty.core.casm.cursor.dump import TreeDumper
from caty.core.exception import throw_caty_exception
from caty.core.schema import schemata
_builtin_types = schemata.keys()

class TypeNormalizer(TreeCursor):
    def __init__(self, module):
        self.module = module
        self.safe = False

    def _visit_root(self, node):
        return self.visit(node)

    def visit(self, node):
        ue = UndefinedEraser(self.module)
        ol = OptionLifter(self.module)
        tc = TypeCalcurator(self.module)
        normalized = tc.visit(ol.visit(ue.visit(node)))
        nc = NeverChecker(self.module, self.safe)
        nc.visit(normalized)
        vc = VariableChecker(self.module)
        vc.visit(normalized)
        dc = DefaultChecker(self.module)
        dc.visit(normalized)
        return normalized

    def _visit_kind(self, node):
        return node

class _SubNormalizer(SchemaBuilder):
    def _visit_root(self, node):
        try:
            body = node.body.accept(self)
        except Exception as e:
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

    @apply_annotation
    def _visit_object(self, node):
        w = node.wildcard.type
        r = _SubNormalizer._visit_object(self, node)
        if w == u'undefined':
            r.wildcard = UndefinedSchema()
        return r

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

    @apply_annotation
    def _visit_option(self, node):
        s = node.body.accept(self)
        if isinstance(s, UndefinedSchema):
            return s
        elif isinstance(s, OptionalSchema):
            return s.accept(self)
        return OptionalSchema(s)

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
            except Exception as e:
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
        if u'__empty__' in (lt, rt):
            # 宣言のみされたスキーマは計算不能
            # 仕方がないのでまとめて宣言のみのスキーマに潰す。
            res = EmptySchema()
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
            l = self._dereference(l, False)
            r = self._dereference(r, False)
            if l.is_extra_tag:
                if r.type == u'__variable__':
                    res = (self._dereference(l, True) & self._dereference(r, True)).accept(self)
                    res.set_tag_constraint(l.tag)
                else:
                    if r.is_extra_tag:
                        t = (l.tag & r.tag).accept(self)
                    else:
                        if rt.startswith('@'):
                            rt = rt[1:]
                        t = rt if rt not in l.tag.excludes else None
                    if t is None or isinstance(t, NeverSchema):
                        res = NeverSchema()
                    else:
                        n = (self._dereference(l, True) & self._dereference(r, True)).accept(self)
                        if t in _builtin_types:
                            res = n
                        else:
                            res = TagSchema(t, n)
            elif rt.startswith('@'): # 右辺がタグ型
                if lt != rt:
                    if r.is_extra_tag:
                        if lt.startswith('@'):
                            lt = lt[1:]
                        t = lt if lt not in r.tag.excludes else None
                        if t is None or isinstance(t, NeverSchema):
                            res = NeverSchema()
                        else:
                            n = (self._dereference(l, True) & self._dereference(r, True)).accept(self)
                            res = TagSchema(t, n)

                    elif lt == '@*!' or lt == '@*': 
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
            l = self._dereference(l, False)
            r = self._dereference(r, False)
            if r.is_extra_tag:
                if l.type == u'__variable__':
                    res = (self._dereference(l, True) & self._dereference(r, True)).accept(self)
                    res.set_tag_constraint(r.tag)
                else:
                    if l.is_extra_tag:
                        t = (l.tag & r.tag).accept(self)
                    else:
                        if lt.startswith('@'):
                            lt = lt[1:]
                        t = lt if lt not in r.tag.excludes else None
                    if t is None or isinstance(t, NeverSchema):
                        res = NeverSchema()
                    else:
                        n = (self._dereference(l, True) & self._dereference(r, True)).accept(self)
                        if t in _builtin_types:
                            res = n
                        else:
                            res = TagSchema(t, n)
            elif rt == u'@*':
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
        if node.operator != u'extract':
            if body.type != 'object':
               raise CatyException(u'SchemaCompileError', 
                    u'Unsupported operand type for $op: $type',
                    op=node.operator, type=body.type)
        if node.operator == u'open':
            if node.type_args:
                body.wildcard = node.type_args[0]
            else:
                body.wildcard = AnySchema()
        elif node.operator == u'close':
            body.wildcard = UndefinedSchema()
        else:
            if isinstance(body, TypeVariable):
                return node
            return node.path.select(body).next()
        return res

    def _visit_type_function(self, node):
        node.typename = node.typename.accept(self)
        schema = node.typename
        if isinstance(schema, TypeReference):
            schema = schema.body
        elif isinstance(schema, TypeVariable):
            if schema._schema:
                schema = schema._schema
            else:
                return node
        if node.funcname == u'typeName':
            return EnumSchema([schema.canonical_name])
        elif node.funcname == u'recordType':
            if u'__collection' not in schema.annotations:
                throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'Not a collection type: %s' % schema.name)
            return schema.accept(self).body

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
                throw_caty_exception(u'SCHEMA_COMPILE_ERROR', ro.i18n.get(u'Type representation is never: $typedef', typedef='\n'.join(paths)))
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
            if isinstance(r, NamedParameterNode):
                continue
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
        from caty.core.exception import throw_caty_exception, CatyException
        tc = TypeCalcurator(self.module)
        nodes = self.__flatten_union(node)
        unions = [(a, b) for a in nodes for b in nodes if a != b]
        for u in unions:
            try:
                o = u[0] & u[1]
                c = tc.visit(o)
                if c.optional:
                    c = c.body
            except CatyException as e:
                if e.tag == u'SCHEMA_COMPILE_ERROR': #&演算でエラーになる=排他
                    pass
                else:   
                    raise
            else:
                is_never = truth(c.accept(self))
                if is_never:
                    pass
                else:
                    throw_caty_exception(ro.i18n.get(u'types are not exclusive: $type', type=TreeDumper().visit(node)))
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

    def _visit_type_function(self, node):
        return []

    def _visit_unary_op(self, node):
        return [] #この時点で演算子が残っている=型変数なので

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
            var_list = zip([a for a in node.type_args if not isinstance(a, NamedParameterNode)], 
                           [b for b in node.type_params if not isinstance(b, NamedTypeParam)])
            rest_params = [b for b in node.type_params if not isinstance(b, NamedTypeParam)][len(var_list):]
            named_list = zip([a for a in node.type_args if isinstance(a, NamedParameterNode)], 
                           [b for b in node.type_params if isinstance(b, NamedTypeParam)])
            rest_params += [b for b in node.type_params if isinstance(b, NamedTypeParam)][len(named_list):]
            self.__suspcious_var.append([])
            for p in rest_params:
                self.__suspcious_var[-1].append(p.var_name)
            if self.__suspcious_var[-1]:
                node.body.accept(self)
            self.__suspcious_var.pop(-1)
        return node


class DefaultChecker(TreeCursor):
    def __init__(self, *args):
        self._path = []

    def visit(self, node):
        node.accept(self)

    def _visit_root(self, node):
        try:
            node.body.accept(self)
        except InvalidDefaultValue as e:
            throw_caty_exception(u'SCHEMA_COMPILE_ERROR', u'Invalid default value at %s: %s: %s' % (node.name, u'$.' + ''.join(self._path), json.pp(e.value)))

    def _visit_kind(self, node):
        pass

    def _visit_scalar(self, node):
        self._validate_default(node)

    def _visit_option(self, node):
        self._validate_default(node)

    def _visit_enum(self, node):
        self._validate_default(node)

    def _visit_object(self, node):
        self._validate_default(node)
        for k, v in node.items():
            self._path.append(k)
            v.accept(self)
            self._path.pop(-1)
        node.wildcard.accept(self)

    def _visit_array(self, node):
        self._validate_default(node)
        for k, v in enumerate(node):
            self._path.append(str(k))
            v.accept(self)
            self._path.pop(-1)

    def _visit_bag(self, node):
        self._validate_default(node)
        for k, v in enumerate(node):
            self._path.append(str(k))
            v.accept(self)
            self._path.pop(-1)

    def _visit_union(self, node):
        self._validate_default(node)
        l = node.left.accept(self)
        r = node.right.accept(self)
    
    def _visit_tag(self, node):
        self._validate_default(node)
        node.body.accept(self)

    def _visit_pseudo_tag(self, node):
        pass

    def _validate_default(self, node):
        if u'default' in node.annotations:
            dval = node.annotations[u'default'].value
            try:
                node.validate(dval)
            except:
                raise InvalidDefaultValue(dval)

    def _visit_type_function(self, node):
        pass

    def _visit_unary_op(self, node):
        pass #この時点で演算子が残っている=型変数なので

class InvalidDefaultValue(Exception):
    def __init__(self, value):
        Exception.__init__(self)
        self.value = value

    

