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

