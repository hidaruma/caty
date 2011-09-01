#coding: utf-8
from caty.core.schema.base import Annotations
from caty.util import indent_lines, justify_messages

class ResourceActionEntry(object):
    def __init__(self, proxy, source, name=u'', docstring=u'Undocumented', annotations=Annotations([]), resource_name=u'system', module_name=u'builtin', profile=None):
        self.profile = profile
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

    def usage(self, invoker):
        from caty.core.action.selector import verb_parser
        buff = []
        buff.append((u'  アクション名: ', self.name))
        v, m, p = verb_parser.run(invoker)
        buff.append((u'  メソッド: ', m))
        if v:
            buff.append((u'  動詞: ', v))
        buff.append((u'  入力型: ', self.profile.input_type.name if self.profile.input_type else u'入力なし'))
        return justify_messages(buff)

class ActionProfiles(object):
    def __init__(self, profiles):
        self._profiles = profiles
        self._next_states = []
        self._input_type = None
        for p in profiles:
            if p.io_type != 'in':
                self._next_states.extend(p.next_states)
            if p.io_type in ('in', 'io') and self._input_type is None:
                self._input_type = p.input_type

    def to_str(self):
        return ',\n'.join([p.to_str() for p in self._profiles])

    @property
    def input_type(self):
        return self._input_type

    @property
    def next_states(self):
        return self._next_states

class ActionProfile(object):
    def __init__(self, io_type, name, input_type, output_type, relay_list, next_states):
        self._name = name
        self._io_type = io_type
        self._input_type = input_type
        self._output_type = output_type
        self._relay_list = relay_list
        self._next_states = next_states

    def to_str(self):
        if self._io_type == 'in':
            i = self._input_type.name
            o = self._output_type if self._output_type == '_' else self._output_type.name
            if self.relay_list:
                return u'#%s %s -> %s relays [%s]' % (self._name, i, o, ', '.join(self.relay_list))
            else:
                return u'#%s %s -> %s' % (self._name, i, o)
        elif self._io_type == 'out':
            o = self._output_type.name
            i = self._input_type if self._input_type == '_' else self._input_type.name
            if self.next_states:
                return u'#%s %s -> %s produces [%s]' % (self._name, i, o, ', '.join(self.next_states))
            else:
                return u'#%s %s -> %s' % (self._name, i, o)
        else:
            o = self._output_type.name
            i = self._input_type.name
            if self.next_states:
                return u'#%s %s -> %s produces [%s]' % (self._name, i, o, ', '.join(self.next_states))
            else:
                return u'#%s %s -> %s' % (self._name, i, o)

    @property
    def name(self):
        return self._name

    @property
    def io_type(self):
        return self._io_type

    @property
    def input_type(self):
        return self._input_type

    @property
    def output_type(self):
        return self._output_type

    @property
    def relay_list(self):
        return self._relay_list

    @property
    def next_states(self):
        return self._next_states
    
