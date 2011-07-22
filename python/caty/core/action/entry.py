from caty.core.schema.base import Annotations
from caty.util import indent_lines

class ResourceActionEntry(object):
    def __init__(self, proxy, source, name=u'', docstring=u'Undocumented', annotations=Annotations([]), resource_name=u'system', module_name=u'builtin', profile=None):
        self.profile = profile or ActionProfile()
        self.instance = proxy
        self.source = source
        self.name = name
        self.docstring = docstring
        self.annotations = annotations
        self.resource_name = resource_name
        self.module_name = module_name
        self._lock_cmd = None

    def set_lock_cmd(self, lock_cmd):
        self._lock_cmd = lock_cmd

    @property
    def lock_cmd(self):
        return self._lock_cmd

    @property
    def compiled(self):
        return self.instance is not None

    def __repr__(self):
        return repr(self.source)


    @property
    def canonical_name(self):
        return u'%s:%s.%s' % (self.module_name, self.resource_name, self.name)

    def to_str(self, invoker):
        buff = []
        buff.append(self.docstring + '\n')
        buff.append('action %s("%s") %s :: {\n' % (self.name, invoker, self.profile.to_str()))
        buff.append(indent_lines(self.source, '    '))
        buff.append('};\n')
        return ''.join(buff)

class ActionProfile(object):
    def __init__(self, input_type=None, output_type=None, inner_profile=None):
        pass

    def to_str(self):
        return u''

