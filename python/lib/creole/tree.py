
class Root(object):
    def __init__(self, childnode):
        self._childnode = childnode
        self.attrs = []
        self.tag = 'root'

    @property
    def childnode(self):
        return [c for c in self._childnode if not isinstance(c, Comment)]

    def __iter__(self):
        return iter(self.childnode)

class Element(object):
    def __init__(self, tag, attrs, node):
        self.tag = tag
        self.attrs = attrs if attrs else []
        self._childnode = node if node else []
        self.parent = None
        for c in self._childnode:
            if isinstance(c, Element):
                c.parent = self

    @property
    def childnode(self):
        return [c for c in self._childnode if not isinstance(c, Comment)]

    def set_attr(self, name, value):
        self.set_attrs([(name, value)])
    
    def set_attrs(self, attrs):
        _attrs = dict(attrs)
        for n, v in self.attrs:
            if not n in _attrs:
                _attrs[n] = v
            else:
                if n == 'class':
                    _attrs[n] = u'%s %s' % (_attrs[n], v)
        self.attrs = list(_attrs.items())


    def __iter__(self):
        return iter(self.childnode)


class Comment(object):
    def __init__(self, text):
        self.text = text

    

