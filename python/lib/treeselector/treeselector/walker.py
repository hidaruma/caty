class AbstractTreeWalker(object):
    def select_all(self, obj): # Object -> Set(AbstractCursor)
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'select_all'))

    def select_name(self, obj, name): # Object -> Set(AbstractCursor)
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'select_name'))

    def filter_class(self, lst, name): # Object -> Bool
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'filter_class'))

    def filter_id(self, lst, id): # Object -> Bool
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'filter_id'))

class AbstractCursor(object):
    def insert(self, obj):
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'insert'))

class AbstractNode(object):
    def get_child_nodes(self):
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'get_child_nodes'))

    def before(self):
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'before'))

    def after(self):
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'after'))

    def current(self):
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'current'))

    def get_parent(self):
        raise NotImplementedError(u'{0}.{1}'.format(self.__class__.__name__, u'get_parent'))

