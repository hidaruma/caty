class AbstractTreeWalker(object):
    def select_all(self, obj): # Object -> Set(AbstractCursor)
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'select_all'))

    def select_name(self, obj, name): # Object -> Set(AbstractCursor)
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'select_name'))

    def filter_class(self, lst, name): # Object -> Bool
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'filter_class'))

    def filter_id(self, lst, id): # Object -> Bool
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'filter_id'))

class _UNDEFINED(object):pass

class Operator(object):
    def select(self, obj):
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'select'))

class AbstractCursor(object):
    def insert(self, obj):
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'insert'))

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
            return r
        
class OrderedSet(list):
    def add(self, obj):
        if obj in self:
            pass
        else:
            self.append(obj)

