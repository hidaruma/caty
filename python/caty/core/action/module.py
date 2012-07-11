#coding :utf-8
from caty.core.action.selector import *
from caty.core.action.resource import *
from caty.core.exception import *
from caty.core.casm.language.ast import CommandNode, ClassNode, ScalarNode, CommandURI
from caty.core.casm.language.commandparser import call_pattern
from caty.core.casm.module import Module, ClassModule
from topdown import CharSeq, many1

class ResourceModuleContainer(object):
    def __init__(self, app):
        self._app = app
        self._selectors = [ResourceSelector(app),
                           ResourceSelector(app),
                           ResourceSelector(app),
                          ]
        self._modules = {}

    def get_modules(self):
        return self._modules.itervalues()

    def add_module(self, resource_module):
        if resource_module.name in self._modules:
            raise Exception(self._app.i18n.get(u'Module $name is already defined', 
                                               name=resource_module.name))
        for r in resource_module.resources:
            self.add_resource(r)
        self._modules[resource_module.name] = resource_module
    
    def add_resource(self, r):
        self._selectors[r.type].add(r)

    def get(self, fs, path, verb, method, no_check=False):
        v = self._verify(fs, path)
        if v:
            return v
        for s in self._selectors:
            matched = s.get(fs, path, verb, method, no_check)
            if matched:
                return matched.resource_class_entry
        throw_caty_exception(
            u'HTTP_403',
            u'Not matched to verb dispatch: path=$path, verb=$verb, method=$method',
            path=path,
            verb=verb,
            method=method)

    def _verify(self, fs, path):
        if not path.endswith('/') and fs.open(path + '/').exists:
            if self._app.web_config['missingSlash'] == 'dont-care':
                if fs.application.name != 'root':
                    return ResourceActionEntry(None, u'http:not-found /%s%s' % (fs.application.name, path), u'not-found')
                return ResourceActionEntry(None, u'http:not-found %s' % (path), u'not-found')
            if fs.application.name != 'root':
                return ResourceActionEntry(None, u'http:found /%s%s/' % (fs.application.name, path), u'not-found')
            return ResourceActionEntry(None, u'http:found %s/' % (path), u'not-found')
        return None

    def _get_trace(self, fs, path, verb, method, no_check=False):
        trace = []
        v = self._verify(fs, path)
        if v:
            for s in self._selectors[:-1]:
                trace.append(None)
            trace.append(u'system:missingSlash._')
            return trace
        matched = None
        for s in self._selectors:
            if matched:
                trace.append(None)
            else:
                _matched = s.get(fs, path, verb, method, no_check)
                if _matched:
                    matched = _matched
                    trace.append(u'%s:%s.%s' % (matched.module_name, matched.resource_name, matched.name))
                else:
                    trace.append(False)
        return trace

    def __repr__(self):
        return repr(self._ftd)

    def get_resource(self, name):
        for s in self._selectors:
            r = s.get_resource(name)
            if r:
                return r
        return None

    def get_module(self, name):
        r = self._modules.get(name)
        if not r:
            throw_caty_exception(
                u'ModuleNotFound',
                u'$moduleName.$moduleType is not defined in $appName',
                moduleName=name,
                moduleType=u'cara',
                appName=self._app.name
            )
        else:
            return r

class ResourceModule(Module):
    type = u'cara'
    def __init__(self, name, docstring, app):
        Module.__init__(self, app)
        self._name = name
        self.docstring = docstring
        self._resources = {}
        self._states = {}
        self._userroles = {}
        self._ports = {}
        self._type = u'cara'

    @property
    def resources(self):
        return self._resources.values()

    def add_resource(self, res):
        from caty.core.script.proxy import EnvelopeProxy as ActionEnvelope
        if res.name in self.resources:
            throw_caty_exception(
                u'CARA_COMPILE_ERROR',
                u'Duplicated resource name: $name module: $module', 
                name=res.name, module=self._name)


        self._resources[res.name] = res
        member = []
        for act in res.actions:
            script = act.instance
            ptn = many1(call_pattern)(CharSeq(u'{*: any} [string*]:: WebInput | void -> Response | Redirect', auto_remove_ws=True))
            c = CommandNode(act.name, 
                            map(lambda p:p([], []), ptn), 
                            ActionEnvelope(script), 
                            act.docstring, 
                            act.annotations, 
                            [],
                            u'action')
            member.append(c)
        clsnode = ClassNode(res.name, member, ScalarNode(u'univ'), CommandURI([(u'python', u'')]), res.docstring, res.annotations)
        clsnode.declare(self)

    def add_state(self, st):
        if st.name in self._states:
            throw_caty_exception(
                u'CARA_COMPILE_ERROR',
                u'Duplicated state name: $name module: $module', 
                name=st.name, module=self._name)
        self._states[st.name] = st

    def add_userrole(self, ur):
        if ur.name in self._userroles:
            throw_caty_exception(
                u'CARA_COMPILE_ERROR',
                u'Duplicated userrole name: $name module: $module', 
                name=ur.name, module=self._name)
        self._userroles[ur.name] = ur

    def add_port(self, port):
        if p.name in self._ports:
            throw_caty_exception(
                u'CARA_COMPILE_ERROR',
                u'Duplicated port name: $name module: $module', 
                name=port.name, module=self._name)
        self._ports[port.name]

    def get_resource(self, name):
        if name in self._resources:
            return self._resources[name]
        throw_caty_exception(
            u'ResourNotFound',
            u'$resourceName is not defined in $moduleName',
            resourceName=name,
            moduleName=self.name
        )

    def reify(self):
        import caty.jsontools as json
        r = Module.reify(self)
        o = json.untagged(r)
        o['resources'] = {}
        o['states'] = {}
        o['userroles'] = {}
        o['ports'] = {}
        for rc in self.resources:
            o['resources'][rc.name] = rc.reify()
            if rc.name in o['classes']:
                del o['classes'][rc.name]
        for st in self.states:
            o['states'][st.name] = st.reify()
        for ur in self.userroles:
            o['userroles'][ur.name] = ur.reify()
        for p in self.ports:
            o['ports'][p.name] = p.reify()
        return json.tagged(u'cara', o)

    def get_state(self, name):
        if name not in self._states:
            throw_caty_exception('StateNotFound', '$name', name)
        return self._states[name]

    
    @property
    def states(self):
        return self._states.values()

    @property
    def userroles(self):
        return self._userroles.values()

    @property
    def ports(self):
        return self._ports.values()

    def make_graph(self):
        root = {
            u'name': self.name,
        }
        subgraphs = self._make_subgraphs()
        edges = []
        nodes = []
        appered_dest = set([])
        for s in self.states:
            for f in self._find_links_to(s.name):
                edges.append({u'from': f, u'to': s.name, u'type': u'action'})
            for i, link in enumerate(s.links):
                if len(link.link_to_list) > 1:
                    from_name = u'__middle_point_{0}_{1}'.format(link.trigger, s.name)
                    nodes.append({'name': from_name, 'type': 'middle-point', 'label': ''})
                    edges.append({u'from': s.name, 
                                  u'to': from_name, 
                                  u'trigger': link.trigger, 
                                  u'type': u'link', 
                                  u'is-middle-point': True})
                    if link.type == 'additional-link':
                        edges[-1][u'trigger'] = ' '.join(['+', edges[-1][u'trigger']])
                    elif link.type == 'no-care-link':
                        edges[-1][u'trigger'] = ' '.join(['-', edges[-1][u'trigger']])
                else:
                    from_name = s.name
                for link_to in link.link_to_list:
                    act, fragment = link_to
                    to_node_name = self._find_linked_action(act)
                    if not to_node_name:
                        if not '.' in act:
                            nodes.append({u'label': act, u'name': act, u'type': u'missing-port'})
                        else:
                            nodes.append({u'label': act, u'name': act, u'type': u'missing-action'})
                        e = {u'from': from_name, u'to': act, u'type': u'missing'}
                    else:
                        if not '.' in to_node_name:
                            to_node_name = 'port#'+to_node_name
                        appered_dest.add(to_node_name)
                        e = {u'from': from_name, u'to': to_node_name, u'type': u'link'}
                    if len(link.link_to_list) == 1:
                        if link.trigger:
                            e[u'trigger'] = link.trigger
                        else:
                            e[u'trigger'] = u''
                        if link.type == 'additional-link':
                            e[u'trigger'] = ' '.join(['+', e[u'trigger']])
                        elif link.type == 'no-care-link':
                            e[u'trigger'] = ' '.join(['-', e[u'trigger']])
                    edges.append(e)
            nodes.append({u'name': s.name, 
                          u'label': s.make_label(self), 
                          u'type': u'state' if 'abstract' not in s.annotations else u'abstract-state'
                          })
        for rc in self.resources:
            for act in rc.entries.values():
                for red in act.profiles.redirects:
                    to_name = self._find_linked_action(red)
                    if not to_name:
                        if not '.' in red:
                            nodes.append({u'label': red, u'name': red, u'type': u'missing-port'})
                        else:
                            nodes.append({u'label': red, u'name': red, u'type': u'missing-action'})
                        e = {u'from': act.resource_name + '.' + act.name, u'to': red, u'type': u'missing'}
                    else:
                        if not '.' in to_name:
                            to_name = 'port#' + to_name
                        e = {u'from': act.resource_name + '.' + act.name, u'to': to_name, u'type': u'redirect'}
                    edges.append(e)
                for st in act.profiles.next_states:
                    if s.name in self._states:
                        break
                    else:
                        nodes.append({u'name': st, u'label': st, u'type': u'missing-state'})
                        e = {u'to': st, u'from': act.resource_name+'.'+act.name, u'type': u'missing'}
                        edges.append(e)
        for port in self.ports:
            if 'dynamic' in port.annotations:
                nodes.append({u'name': u'port#'+port.name, u'label': port.name, u'type': u'dyn-port'})
            else:
                nodes.append({u'name': u'port#'+port.name, u'label': port.name, u'type': u'port'})
        for d in appered_dest:
            found = False
            for s in subgraphs:
                for n in s['nodes']:
                    if n['name'] == d:
                        found = True
                        break
                if found:
                    break
            for n in nodes:
                if n['name'] == d:
                    found = True
                    break
            if not found:
                nodes.append({u'name': d, u'label': d, u'type': u'external'})
        root['nodes'] = nodes
        root['edges'] = edges
        root['subgraphs'] = subgraphs
        return root

    def _make_subgraphs(self):
        resources = {}
        for rc in self.resources:
            if rc.name not in resources:
                resources[rc.name] = []
            for act in rc.entries.values():
                resources[act.resource_name].append({u'label': act.name, u'name': act.resource_name+'.'+act.name,u'type': u'action'})
        r = []
        for k, v in resources.items():
            r.append({u'name':k, u'nodes': v, u'edges': [], u'subgraphs': [], u'type': u'resource_subgraph'})
        return r

    def _find_links_to(self, state_name):
        for r in self.resources:
            for act in r.entries.values():
                if state_name in act.profiles.next_states:
                    yield act.resource_name+'.'+act.name

    def _find_linked_action(self, action_id):
        if ':' in action_id:
            return action_id
        if not '.' in action_id:
            for p in self.ports:
                if p.name == action_id:
                    return action_id
            else:
                return None
        rcname, aname = action_id.split('.', 1)
        for r in self.resources:
            if r.name == rcname:
                res = r
                break
        else:
            return None
        for a in res.entries.values():
            if a.name == aname:
                return action_id
        else:
            return None

    def make_userrole_graph(self):
        root = {
            u'name': self.name,
        }
        nodes = []
        edges = []
        states = []
        subgraphs = [{u'name': u'states', u'nodes': states, u'edges': [], u'subgraphs': [], u'type': u'state_subgraph'}]
        for u in self.userroles:
            nodes.append({u'name': u.name, u'label': u.name, u'type': u'userrole'})
        
        for s in self.states:
            states.append({u'name': s.name, 
                          u'label': s.name, 
                          u'type': u'state' if 'abstract' not in s.annotations else u'abstract-state'
                         })
            e = None
            for n in s.actor_names:
                for u in self.userroles:
                    if u.name == n:
                        e = {u'to': s.name, u'from':u.name , u'type': u'usecase'}
                        break
                else:
                    if n:
                        e = {u'to': s.name, u'from': n, u'type': 'missing-usecase'}
                        nodes.append({u'name': n, u'label': n, u'type': u'missing-userrole'})
                if e:
                    edges.append(e)

        root['nodes'] = nodes
        root['edges'] = edges
        root['subgraphs'] = subgraphs
        return root

