#coding :utf-8
from caty.core.action.selector import *
from caty.core.action.resource import *
from caty.core.exception import *
from caty.core.casm.language.ast import CommandNode
from caty.core.casm.language.commandparser import call_pattern
from caty.core.casm.module import Module
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
    type = u'.cara'
    def __init__(self, name, docstring, app):
        Module.__init__(self, app)
        self._name = name
        self.docstring = docstring
        self._resources = []
        self._states = []

    @property
    def resources(self):
        return self._resources

    def add_resource(self, res):
        self._resources.append(res)
        for act in res.actions:
            script = act.instance
            ptn = many1(call_pattern)(CharSeq(u'{*: any} [string*]:: WebInput -> Response | Redirect', auto_remove_ws=True))
            c = CommandNode(u'{0}.{1}'.format(res.name, act.name), 
                            map(lambda p:p([], []), ptn), 
                            script, 
                            act.docstring, 
                            act.annotations, 
                            [])
            c.declare(self)

    def get_resource(self, name):
        for r in self._resources:
            if r.name == name:
                return r
        throw_caty_exception(
            u'ResourNotFound',
            u'$resourceName is not defined in $moduleName',
            resourceName=name,
            moduleName=self.name
        )

    @property
    def states(self):
        return self._states

    def make_graph(self):
        root = {
            u'name': self.name,
        }
        subgraphs = self._make_subgraphs()
        edges = []
        nodes = []
        appered_dest = set([])
        for s in self._states:
            for f in self._find_links_to(s.name):
                edges.append({u'from': f, u'to': s.name, u'type': u'action'})
            for link in s.links:
                for link_to in link.link_to_list:
                    act, fragment = link_to
                    to_node_name = self._find_linked_action(act)
                    appered_dest.add(to_node_name)
                    e = {u'from': s.name, u'to': to_node_name, u'type': u'link'}
                if link.trigger:
                    e[u'trigger'] = link.trigger
                else:
                    e[u'trigger'] = u''
                if link.type == 'additional-link':
                    e[u'trigger'] = ' '.join(['+', e[u'trigger']])
                edges.append(e)
            nodes.append({u'name': s.name, u'label': s.name, u'type': u'state'})
        for rc in self._resources:
            for act in rc.entries.values():
                for red in act.profiles.redirects:
                    to_name = self._find_linked_action(red)
                    e = {u'from': act.resource_name + '.' + act.name, u'to': to_name, u'type': u'redirect'}
                    edges.append(e)
        for d in appered_dest:
            found = False
            for s in subgraphs:
                for n in s['nodes']:
                    if n['name'] == d:
                        found = True
                        break
                if found:
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
            r.append({u'name':k, u'nodes': v, u'edges': [], u'subgraphs': []})
        return r

    def _find_links_to(self, state_name):
        for r in self.resources:
            for act in r.entries.values():
                if state_name in act.profiles.next_states:
                    yield act.resource_name+'.'+act.name

    def _find_linked_action(self, action_id):
        if ':' in action_id:
            return action_id
        rcname, aname = action_id.split('.')
        for r in self.resources:
            if r.name == rcname:
                res = r
                break
        else:
            throw_caty_exception(
                u'ResourNotFound',
                u'$resourceName is not defined in $moduleName',
                resourceName=rcname,
                moduleName=self.name
            )
        for a in res.entries.values():
            if a.name == aname:
                return action_id
        else:
            throw_caty_exception(
                u'ActionNotFound',
                u'$actionName is not defined in $moduleName:$resourceName',
                actionName=aname,
                moduleName=self.name,
                resourceName=rcname
            )
