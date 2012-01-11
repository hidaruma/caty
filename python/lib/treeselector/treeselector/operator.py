
class _UNDEFINED(object):pass

class BaseOperatorFactory(object):
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

    def pseudo_class_selector(self, sub, name):
        return PseudoClassSelector(sub, name)

class Operator(object):
    def select(self, obj):
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'select'))

    def __repr__(self):
        return '{0} "{1}"'.format(object.__repr__(self), self.to_notation())

    def __str__(self):
        return '{0}.{1}({2})'.format(self.__module__, self.__class__.__name__, self.to_notation())

    def select_child(self, parent):
        for o in self.select(parent):
            if o.get_parent() == parent:
                yield o

    def to_notation(self):
        return u''

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

    def to_notation(self):
        if isinstance(self.arg, _UNDEFINED):
            return u'*'
        else:
            return self.arg

class FilterSelector(Operator):
    def __init__(self, func, arg):
        self.func = func
        self.arg = arg

    def select(self, obj):
        return self.func(obj, self.arg)

    def to_notation(self):
        if self.func.__name__ == 'filter_id':
            return u'#' + self.arg
        elif self.func.__name__ == 'filter_class':
            return u'.' + self.arg
        else:
            return u'?' + self.func.__name__

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

    def to_notation(self):
        return u'{0}{1}'.format(self.op1.to_notation(), self.op2.to_notation()) 

class ChildOperator(BinOperator):

    def select(self, obj):
        r = OrderedSet()
        for o1 in self.op1.select(obj):
            for o2 in self.op2.select_child(o1):
                r.add(o2)
        return r

    def to_notation(self):
        return u'{0} > {1}'.format(self.op1.to_notation(), self.op2.to_notation()) 

class UnionOperator(BinOperator):

    def select(self, obj):
        r = OrderedSet()
        for o1 in self.op1.select(obj):
            r.add(o1)

        for o2 in self.op2.select(obj):
            r.add(o2)
        return r


    def to_notation(self):
        return u'{0}, {1}'.format(self.op1.to_notation(), self.op2.to_notation()) 

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
                cs = get_child_nodes()
                if cs:
                    r.add(cs[0].before())
                else:
                    r.add(o.current())
        return r

    def to_notation(self):
        return u'{0}:{1}'.format(self.sub_selector.to_notation(), self.func_name) 

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

    def to_notation(self):
        return u'{1}({0})'.format(self.sub_selector.to_notation(), self.func_name) 
        
class PseudoClassSelector(Operator):
    def __init__(self, sub_selector, func_name):
        self.sub_selector = sub_selector
        self.func_name = func_name

    def select(self, obj):
        for r in self._select(obj, self.sub_selector.select):
            yield r

    def select_child(self, obj):
        for r in self._select(obj, self.sub_selector.select_child):
            yield r

    def _select(self, obj, func):
        r = _UNDEFINED
        if self.func_name == 'root':
            yield obj
        else:
            for o in func(obj):
                r = o
                if self.func_name == u'first-child':
                    break
            if r is not _UNDEFINED:
                yield r

    def to_notation(self):
        return u'{0}:{1}'.format(self.sub_selector.to_notation(), self.func_name) 

class OrderedSet(list):
    def add(self, obj):
        if obj in self:
            pass
        else:
            self.append(obj)


