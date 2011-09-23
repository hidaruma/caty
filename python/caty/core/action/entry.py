#coding: utf-8
from caty.core.schema.base import Annotations
from caty.util import indent_lines, justify_messages
from caty.core.exception import *

class ResourceActionEntry(object):
    def __init__(self, proxy, source, name=u'', docstring=u'Undocumented', annotations=Annotations([]), resource_name=u'system', module_name=u'builtin', profiles=None, invoker=None):
        self.profiles = profiles if profiles else ActionProfiles([ActionProfile(None, None, None, None, [],  [], [])])
        self.instance = proxy
        self.source = source
        self.name = name
        self.docstring = docstring
        self.annotations = annotations
        self.resource_name = resource_name
        self.module_name = module_name
        self.invoker = invoker
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

    def usage(self, with_doc=True, indent=0):
        from caty.core.action.selector import verb_parser
        buff = []
        buff.append((('  '*indent) + u'アクション名: ', self.name))
        v, m, p = verb_parser.run(self.invoker)
        buff.append((('  '*indent) + u'メソッド: ', m))
        if v:
            buff.append((('  '*indent) + u'動詞: ', v))
        if self.profiles:
            buff.append((('  '*indent) + u'入力型: ', self.profiles.input_type.name if self.profiles.input_type else u'入力なし'))
        m = justify_messages(buff)
        if with_doc:
            m = self.docstring.strip() + '\n\n' + m
        return m

    def make_graph(self, module):
        try:
            G = {
                u'name': u'%s:%s.%s' % (self.module_name, self.resource_name, self.name), 
                u'subgraphs': [], 
                u'nodes': [], 
                u'edges': []
            }
            G['subgraphs'].append(self.profiles.make_relay_graph())


            for profile in self.profiles:
                if profile.input_type != u'_':
                    G['nodes'].append({u'name': profile.input_type.name, u'type': 'type'})
                    G['edges'].append({u'from': profile.input_type.name, u'to': profile.name, u'type': u'link'})
                else:
                    G['edges'].append({u'from': None, u'to': profile.name, u'type': u'relay'})
                if profile.output_type != u'_':
                    if profile.output_type.name != u'never':
                        G['nodes'].append({u'name': profile.output_type.name, u'type': 'type'})
                        G['edges'].append({u'to': profile.output_type.name, u'from': profile.name, u'type': u'action-to-type'})
                else:
                    G['edges'].append({u'to': None, u'from': profile.name, u'type': u'relay'})
                for state in module.states:
                    if profile.connects_to(state):
                        G['nodes'].append({u'name': state.name, u'type': 'state'})
                        G['edges'].append({u'from': profile.output_type.name, u'to': state.name, u'type': u'action'})
                    for link in self.related_link(state):
                        t, c = profile.connected_from(link)
                        if link.type == 'additional-link':
                            t = u'+ ' + t
                        if c:
                            G['nodes'].append({u'name': state.name, u'type': 'state'})
                            G['edges'].append({u'to': profile.input_type.name, u'from': state.name, u'trigger': t, u'type': u'link-to-type'})
                for red in profile.redirects:
                    G['nodes'].append({u'name': red, u'type': u'action'})
                    G['edges'].append({u'to': red, u'from': profile.name, u'type': u'redirect'})
            for edge in G['edges']:
                if edge['to'] == None:
                    for _edge in G['edges']:
                        if _edge['from'] == None:
                            _edge['from'] = edge['from']
                    G['edges'].remove(edge)
            return G
        except InternalError, e:
            throw_caty_exception(
                e.key,
                e.msg,
                actionName=self.name,
                resourceName=self.resource_name,
                moduleName=self.module_name,
                **e.placeholder
            )

    def related_link(self, state):
        for link in state.links:
            for name, _ in link.link_to_list:
                if name == self.resource_name + '.' + self.name:
                    yield link

class InternalError(Exception):
    def __init__(self, key, msg, **placeholder):
        self.key = key
        self.msg = msg
        self.placeholder = placeholder

class ActionProfiles(object):
    def __init__(self, profiles):
        self._profiles = profiles
        self._next_states = []
        self._input_type = None
        self._redirects = []
        for p in profiles:
            if p.io_type != 'in':
                self._next_states.extend(p.next_states)
            if p.io_type in ('in', 'io') and self._input_type is None:
                self._input_type = p.input_type
            self._redirects.extend(p.redirects)

    def to_str(self):
        return ',\n'.join([p.to_str() for p in self._profiles])

    @property
    def input_type(self):
        return self._input_type

    @property
    def next_states(self):
        return self._next_states

    @property
    def redirects(self):
        return self._redirects

    def make_relay_graph(self):
        G = {u'name': u'cluster_relay', u'label': u'', u'nodes': [], u'edges': [], u'subgraphs': []}
        for p in self._profiles:
            G['nodes'].append({u'name': p.name, u'type': u'fragment'})
            if p.io_type == 'in':
                for e in self._make_in_to_out_edges(p):
                    G['edges'].append(e)
        return G

    def _make_in_to_out_edges(self, p):
        if not p.relay_list:
            found = False
            for _p in self._profiles:
                if _p.io_type == 'out':
                    found = True
                    yield {u'from': p.name, u'to': _p.name, u'type': u'relay'}
            if not found:
                raise InternalError(u'MISSING_SCRIPT_FRAGMENT', 
                                    u'Script fragment relays to nothing: $moduleName:$resourceName.$actionName')
        else:
            for rel in p.relay_list:
                for _p in self._profiles:
                    if _p.io_type == 'out' and _p.name == rel:
                        yield {u'from': p.name, u'to': _p.name, u'type': u'relay'}
                        break
                else:
                    raise InternalError(u'MISSING_SCRIPT_FRAGMENT', 
                                        u'Script fragment $name not exists: $moduleName:$resourceName.$actionName', 
                                        name=rel)

    def list_input_types(self):
        for p in self._profiles:
            if p.io_type in ('in', 'io'):
                yield p.input_type.name, p.name

    def list_output_types(self):
        for p in self._profiles:
            if p.io_type in ('out', 'io'):
                if p.output_type.name != 'never':
                    yield p.output_type.name, p.name

    def list_redirects(self):
        for p in self._profiles:
            for r in p.redirects:
                yield r, p.name


    def __iter__(self):
        return iter(self._profiles)

class ActionProfile(object):
    def __init__(self, io_type, name, input_type, output_type, relay_list, next_states, redirects):
        self._name = name
        self._io_type = io_type
        self._input_type = input_type
        self._output_type = output_type
        self._relay_list = relay_list
        self._next_states = next_states
        self._redirects = redirects

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
    
    @property
    def redirects(self):
        return self._redirects

    def connects_to(self, state):
        if self.io_type in (u'io', u'out'):
            return state.name in self.next_states
        return False

    def connected_from(self, link):
        for _, fragment in link.link_to_list:
            if fragment == self.name:
                return link.trigger, True
            if fragment == None:
                return link.trigger, self.io_type in (u'io', u'in')
        return u'', False


