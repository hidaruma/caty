from __future__ import absolute_import
from creole.tree import Element

class PluginContainer(object):
    def __init__(self, plugins, factory=None):
        self._plugins = {}
        if not factory:
            self.factory = Element
        else:
            self.factory = factory
        if plugins:
            for p in plugins:
                self._plugins[p.name] = p

    def get(self, name):
        return self._plugins.get(name, NullPlugin(name, self.factory))
    
class Plugin(object):
    def __init__(self):
        self._element_factory = Element

    def set_factory(self, factory):
        self._element_factory = factory
    
    def create_element(self, *args, **kwds):
        return self._element_factory(*args, **kwds)

class NullPlugin(Plugin):
    def __init__(self, name, factory):
        self._name = name
        self.set_factory(factory)

    def execute(self, arg):
        return self.create_element('p', None, [u'Plugin Not Found: %s' % (self._name)])


