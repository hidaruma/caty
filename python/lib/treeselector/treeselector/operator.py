
class _UNDEFINED(object):pass

class OperatorFactory(object):
    def simple_selector(self, func, arg=_UNDEFINED()):
        return SimpleSelector(func, arg)

    def filter_selector(self, func, arg):
        return FilterSelector(func, arg)

    def filter_operator(self, op1, op2):
        return FilterOperator(op1, op2)

    def child_operator(self, op1, op2):
        return ChildOperator(op1, op2)

    def union_operator(self, op1, op2):
        return UnionOperator(op1, op2)

    def node_position_selector(self, sub, name):
        return NodePositionSelector(sub, name)

    def position_spec_selector(self, sub, name):
        return PositionSpecSelector(sub, name)

class Operator(object):
    def select(self, obj):
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'select'))


class SimpleSelector(Operator):
    def __init__(self, func, arg=_UNDEFINED()):
        self.func = func
        self.arg = arg
    
    def select(self, obj):
        r = OrderedSet()
        if isinstance(self.arg, _UNDEFINED):
            for o in self.func(obj):
                r.add(o)
        else:
            for o in self.func(obj, self.arg):
                r.add(o)
        return r

class FilterSelector(Operator):
    def __init__(self, func, arg):
        self.func = func
        self.arg = arg

    def select(self, obj):
        return self.func(obj, self.arg)

class BinOperator(Operator):
    def __init__(self, op1, op2):
        self.op1 = op1
        self.op2 = op2

class FilterOperator(BinOperator):

    def select(self, obj):
        r = OrderedSet()
        for o in self.op1.select(obj):
            if self.op2.select(o):
                r.add(o)
        return r

class ChildOperator(BinOperator):

    def select(self, obj):
        r = OrderedSet()
        for o1 in self.op1.select(obj):
            for o2 in self.op2.select(o1):
                if o2.get_parent() == o1:
                    r.add(o2)
        return r

class UnionOperator(BinOperator):

    def select(self, obj):
        r = OrderedSet()
        for o1 in self.op1.select(obj):
            r.add(o1)

        for o2 in self.op2.select(obj):
            r.add(o2)
        return r

class NodePositionSelector(Operator):
    def __init__(self, sub_selector, func_name):
        self.sub_selector = sub_selector
        self.func_name = func_name

    def select(self, obj):
        r = OrderedSet()
        for o in self.sub_selector.select(obj):
            if self.func_name == u'before':
                r.add(o.before())
            elif self.func_name == u'after':
                r.add(o.after())
            elif self.func_name == u'child':
                if o.child_nodes:
                    r.add(o.child_nodes[0].before())
                else:
                    r.add(o.current())
        return r

class PositionSpecSelector(Operator):
    def __init__(self, sub_selector, func_name):
        self.sub_selector = sub_selector
        self.func_name = func_name

    def select(self, obj):
        r = _UNDEFINED
        for o in self.sub_selector.select(obj):
            r = o
            if self.func_name == u'first':
                break
        if r is not _UNDEFINED:
            yield r
        
class OrderedSet(list):
    def add(self, obj):
        if obj in self:
            pass
        else:
            self.append(obj)


