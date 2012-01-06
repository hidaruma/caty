# coding: utf-8
from caty.core.command import Builtin
from caty.core.exception import *
try:
    import pygraphviz as gv
except:
    print '[Warning] graphviz is not install, viva module does not work.'

class DrawingMixin(object):
    def _modified(self, path, modname):
        import os
        app_info = self.env.get('CATY_APP')
        src = os.path.join(self.env.get('CATY_HOME'), app_info['group'], app_info['name'], 'actions', modname + '.cara')
        dest = self.pub.open('/'+path.lstrip('/'))
        if not dest.exists:
            return True
        src_mod = os.stat(src).st_mtime
        return not dest.is_modifed_since(src_mod)


    def _strip(self, o):
        if not self._strip_xml_decl: return o
        import xml.dom.minidom as dom
        doc = dom.parseString(o)
        for c in doc.childNodes:
            if c.nodeType == dom.Element.ELEMENT_NODE:
                return c.toxml().replace('<?xml version="1.0" encoding="utf-8"?>', '')

    def format_graph(self, graph):
        self._fill_subgraph(graph)
        return graph

    def _fill_subgraph(self, graph):
        for sg in graph['subgraphs']:
            if not sg['nodes']:
                sg['nodes'].append({'name': 'x', 'type': 'middle-point', 'label': ''})

class DrawModule(Builtin, DrawingMixin):
    _graph_config = {
        'graph': {
            'bgcolor': 'gainsboro',
            'fontsize': 20.0,
            'labelloc': 't',
        },
        'resource_subgraph': {
            'bgcolor': 'darkolivegreen4',
            'color': 'black',
            'fontsize': 14.0,
        },
        'state_subgraph': {
            'fillcolor': '#ffff99',
            'color': 'black',
            'style': 'rounded,filled',
            'fontsize': 14.0,
        },
        'edge': {
            'action': {
                'fontsize': 14.0,
                'color': 'crimson'
            },
            'link': {
                'fontsize': 14.0,
                'color': 'darkorchid3',
            },
            'redirect': {
                'fontsize': 14.0,
                'color': 'blue3',
            },
            'usecase': {
                'fontsize': 14.0,
                'color': 'black',
                'arrowhead': 'none',
            },
            'scenario': {
                'fontsize': 14.0,
                'color': 'black',
                'arrowhead': 'none',
            },
            'missing': {
                'fontsize': 14.0,
                'color': '#333333',
                'style': 'dotted',
            },
            'missing-usecase': {
                'fontsize': 14.0,
                'color': '#333333',
                'style': 'dotted',
                'arrowhead': 'none',
            },
        },
        'action': {
            'fontsize': 14.0,
            'shape': u'ellipse',
            'style': u'filled',
            'color': u'black',
            'fillcolor': u'darkseagreen2'
        }, 
        'port': {
            'fontsize': 14.0,
            'shape': u'ellipse',
            'style': u'filled,dotted',
            'color': u'black',
            'fillcolor': u'darkseagreen2'
        },
        'dyn-port': {
            'fontsize': 14.0,
            'shape': u'ellipse',
            'style': u'filled,dotted',
            'color': u'black',
            'fillcolor': u'olivedrab1',
        },
        'state': {
            'fontsize': 14.0,
            'shape': u'note',
            'style': u'filled',
            'color': u'black',
            'fillcolor': u'gold'
        },
        'abstract-state': {
            'fontsize': 14.0,
            'shape': u'note',
            'style': u'filled',
            'color': u'black',
            'fillcolor': u'#ffe7a0'
        },
        'userrole': {
            'fontsize': 14.0,
            'shape': u'octagon',
            'style': u'filled',
            'color': u'black',
            'fillcolor': u'white'
        },
        'missing-action': {
            'fontsize': 14.0,
            'shape': u'ellipse',
            'style': u'filled',
            'color': u'black',
            'fillcolor': u'gainsboro'
        },
        'missing-state': {
            'fontsize': 14.0,
            'shape': u'note',
            'style': u'filled',
            'color': u'black',
            'fillcolor': u'gainsboro'
        },
        'missing-userrole': {
            'fontsize': 14.0,
            'shape': u'octagon',
            'color': u'black',
            'fillcolor': u'gainsboro'
        },
        'missing-port': {
            'fontsize': 14.0,
            'shape': u'ellipse',
            'style': u'filled,dotted',
            'color': u'black',
            'fillcolor': u'gainsboro'
        },
        'external': {
            'fontsize': 14.0,
            'shape': u'ellipse',
            'style': u'filled',
            'color': u'black',
            'fillcolor': u'azure'
        },
        'middle-point': {
            'shape': 'none',
            'height': '0.0',
            'width': '0.0',
            'label': ''
        },
    }
    def setup(self, opts, module_name):
        self._module_name = module_name
        self._out_file = opts.get('out', '')
        self._format = opts['format']
        self._font = opts.get('font', '')
        self._strip_xml_decl = False
        if self._format == 'svge':
            self._format = 'svg'
            self._strip_xml_decl = True
        if self._out_file:
            self._format = self._out_file.split('.')[-1]
            if self._out_file.endswith('.svge'):
                self._strip_xml_decl = True
                self._format = u'svg'
        self._node = opts['node']
        self._if_modified = opts['if-modified']

    def execute(self):
        if self._out_file and self._if_modified:
            if not self._modified(self._out_file, self._module_name):
                return
        src = self.format_graph(self.make_graph())
        G = self.transform(src)
        G.layout(prog='dot')
        if self._out_file:
            o = G.draw(prog='dot', format=self._format)
            o = self._strip(self.apply_class(o, src))
            with self.pub.open('/'+self._out_file, 'wb') as f:
                f.write(o)
        else:
            o = G.draw(prog='dot', format=self._format)
            o = self._strip(self.apply_class(o, src))
            if self._format == 'dot':
                return unicode(o, 'utf-8')
            else:
                return o

    def apply_class(self, obj, graph):
        import xml.dom.minidom as dom
        if self._format != 'svg':
            return obj
        x = dom.parseString(obj)
        for g in x.getElementsByTagName('g'):
            cls = g.getAttribute('class')
            if cls != 'node':
                continue
            node = self.__get_node(g.getAttribute('id'), graph)
            if node is None:
                continue
            if node['type'] in ('state', 'abstract-state', 'missing-state'):
                cls = 'node state'
            elif node['type'] in ('port', 'dyn-port', 'missing-port'):
                cls = 'node port'
            elif node['type'] in ('action', 'missing-action'):
                cls = 'node action'
            if 'missing' in node['type']:
                cls += ' unknown'
            g.setAttribute('class', cls)
        return x.toxml(encoding='utf-8')
    
    def __get_node(self, name, graph):
        for node in graph['nodes']:
            if node['name'] == name:
                return node
        for sg in graph['subgraphs']:
            n = self.__get_node(name, sg)
            if n:
                return n
        return 

    def make_graph(self):
        app = self.current_app
        rmc = app.resource_module_container
        rm = rmc.get_module(self._module_name)
        if self._node == 'userrole':
            return rm.make_userrole_graph()
        else:
            return rm.make_graph()

    def transform(self, graph_struct, root=True):
        cfg = {
            'strict': True,
            'directed': True
        }
        if root:
            cfg['name'] = graph_struct['name']
            cfg.update(self._graph_config['graph'])
        else:
            cfg.update(self._graph_config[graph_struct['type']])
            cfg['name'] = 'cluster_' + graph_struct['name']
        RG = gv.AGraph(**cfg)
        if root:
            RG.graph_attr['label'] = 'Module: ' + graph_struct['name']
            if self._font:
                RG.graph_attr.update(fontname=self._font)
                RG.node_attr.update(fontname=self._font)
                RG.edge_attr.update(fontname=self._font)

        else:
            if self._node != 'userrole':
                RG.graph_attr['label'] = graph_struct['name']
            else:
                RG.graph_attr['label'] = u''
        if self._font:
            RG.graph_attr.update(fontname=self._font)
        for sg in graph_struct['subgraphs']:
            G = self.transform(sg, False)
            if self._node == 'state':
                for n in G.iternodes():
                    RG.add_node(n.name, **n.attr)
            else:
                _G = RG.add_subgraph(G.iternodes(), G.name, **G.graph_attr)
                for n in G.iternodes():
                    _G.add_node(n.name, **n.attr)
                _G.add_edges_from(G.iteredges())
        for node in graph_struct['nodes']:
            name = node['name']
            RG.add_node(name)
            N = RG.get_node(name)
            attr = {}
            attr.update(self._graph_config[node['type']])
            if node['type'] == 'middle-point':
                pass
            elif (self._node == 'state' and node['type'] not in ('state', 'abstract-state')):
                if node['type'] == 'missing-state':
                    attr['shape'] = 'note'
                    #attr['height'] = '0.2'
                else:
                    attr['label'] = ''
                    attr['width'] = '0.2'
                    attr['shape'] = 'circle'
            elif (self._node == 'action' and node['type'] not in('action', 'port', 'dyn-port')):
                if node['type'] in ('external', 'missing-action', 'missing-port'):
                    pass
                    #attr['shape'] = 'circle'
                else:
                    attr['label'] = ''
                    attr['width'] = '0.2'
                    attr['shape'] = 'box'
                    attr['height'] = '0.2'
            else:
               attr['label'] = node['label']
            attr['id'] = node['name']
            N.attr.update(attr)
        for edge in graph_struct['edges']:
            conf = {}
            conf.update(self._graph_config['edge'][edge['type']])
            if edge.get('is-middle-point', False):
                conf['arrowhead'] = 'none'
            if 'trigger' not in edge or self._node == 'action':
                RG.add_edge(edge['from'], 
                            edge['to'], 
                            **conf)
            else:
                RG.add_edge(edge['from'], 
                            edge['to'], 
                            label=edge['trigger'],
                            **conf)
        return RG


class DrawAction(Builtin, DrawingMixin):
    _graph_config = {
        'graph': {
            'bgcolor': 'gainsboro',
            'fontsize': 20.0,
            'labelloc': 't',
        },
        'subgraph': {
            'fillcolor': 'darkseagreen2',
            'color': 'black',
            'style': 'rounded,filled',
            'fontsize': 14.0,
        },
        'edge': {
            'action': {
                'fontsize': 14.0,
                'color': 'crimson'
            },
            'relay': {
                'fontsize': 14.0,
                'color': 'brown4',
                'style': 'dotted',
            },
            'link': {
                'fontsize': 14.0,
                'color': 'darkorchid3',
            }, 
            'redirect': {
                'fontsize': 14.0,
                'color': 'blue3',
            },
            'action-to-type': {
                'fontsize': 14.0,
                'arrowhead': 'none',
                'color': 'crimson'
            },
            'link-to-type': {
                'fontsize': 14.0,
                'arrowhead': 'none',
                'color': 'darkorchid3',
            }, 
            'missing': {
                'fontsize': 14.0,
                'color': '#333333',
                'style': 'dotted',
            },
        },
        'fragment': {
            'fontsize': 14.0,
            'shape': u'ellipse',
            'style': u'filled',
            'color': u'black',
            'fillcolor': u'greenyellow'
        },
        'type': {
            'fontsize': 14.0,
            'shape': u'plaintext',
            'height': '0.1',
            'style': u'filled',
            'color': u'gainsboro',
            'fillcolor': u'gainsboro'
        },
        'state': {
            'fontsize': 14.0,
            'shape': u'note',
            'style': u'filled',
            'color': u'black',
            'fillcolor': u'gold'
        },
        'abstract-state': {
            'fontsize': 14.0,
            'shape': u'note',
            'style': u'filled',
            'color': u'black',
            'fillcolor': u'#ffe7a0'
        },
        'action': {
            'fontsize': 14.0,
            'shape': u'ellipse',
            'style': u'filled',
            'color': u'black',
            'fillcolor': u'darkseagreen2'
        }, 
        'port': {
            'fontsize': 14.0,
            'shape': u'ellipse',
            'style': u'filled,dotted',
            'color': u'black',
            'fillcolor': u'darkseagreen2'
        },
        'dyn-port': {
            'fontsize': 14.0,
            'shape': u'ellipse',
            'style': u'filled,dotted',
            'color': u'black',
            'fillcolor': u'olivedrab1'
        },
        'missing-action': {
            'fontsize': 14.0,
            'shape': u'ellipse',
            'style': u'filled',
            'color': u'black',
            'fillcolor': u'gainsboro'
        },
        'missing-state': {
            'fontsize': 14.0,
            'shape': u'note',
            'style': u'filled',
            'color': u'black',
            'fillcolor': u'gainsboro'
        },  
        'missing-port': {
            'fontsize': 14.0,
            'shape': u'ellipse',
            'style': u'filled,dotted',
            'color': u'black',
            'fillcolor': u'gainsboro'
        },
        'middle-point': {
            'shape': 'none',
            'height': '0.0',
            'width': '0.0',
            'label': ''
        },
    }
    def setup(self, opts, action_name):
        self._action_name = action_name
        self._out_file = opts.get('out', '')
        self._lone = opts['lone']
        self._format = opts['format']
        self._font = opts.get('font', '')
        self._strip_xml_decl = False
        if self._format == 'svge':
            self._format = 'svg'
            self._strip_xml_decl = True
        if self._out_file:
            self._format = self._out_file.split('.')[-1]
            if self._out_file.endswith('.svge'):
                self._strip_xml_decl = True
                self._format = u'svg'
        self._if_modified = opts['if-modified']

    def execute(self):
        if self._out_file and self._if_modified:
            mname, rname, aname = self._split_name()
            if not self._modified(self._out_file, mname):
                return
        src = self.format_graph(self.make_graph())
        G = self.transform(src)
        G.layout(prog='dot')
        if self._out_file:
            o = G.draw(prog='dot', format=self._format)
            o = self._strip(o)
            with self.pub.open('/'+self._out_file, 'wb') as f:
                f.write(o)
        else:
            o = G.draw(prog='dot', format=self._format)
            o = self._strip(o)
            if self._format == 'dot':
                return unicode(o, 'utf-8')
            else:
                return o

    def make_graph(self):
        app = self.current_app
        rmc = app.resource_module_container
        mname, rname, aname = self._split_name()
        rm = rmc.get_module(mname)
        res = rm.get_resource(rname)
        act = res.get_action(aname)
        return act.make_graph(rm, self._lone)

    def _split_name(self):
        mod, rest = self._action_name.split(':')
        res, act = rest.split('.')
        return mod, res, act

    def transform(self, graph_struct, root=True):
        cfg = {
            'strict': True,
            'directed': True
        }
        if root:
            cfg['name'] = graph_struct['name']
            cfg.update(self._graph_config['graph'])
        else:
            cfg.update(self._graph_config['subgraph'])
            cfg['name'] = 'cluster_' + graph_struct['name']
        RG = gv.AGraph(**cfg)
        if root:
            RG.graph_attr['label'] = 'Action: ' + graph_struct['name']
            if self._font:
                RG.graph_attr.update(fontname=self._font)
                RG.node_attr.update(fontname=self._font)
                RG.edge_attr.update(fontname=self._font)
        else:
            RG.graph_attr['label'] = graph_struct['label']
        for sg in graph_struct['subgraphs']:
            G = self.transform(sg, False)
            _G = RG.add_subgraph(G.iternodes(), G.name, **G.graph_attr)
            for n in G.iternodes():
                _G.add_node(n.name, **n.attr)
            for e in G.iteredges():
                _G.add_edge(e[0], e[1], **e.attr)
        names = []
        for node in graph_struct['nodes']:
            name = node['name']
            names.append(name)
            RG.add_node(name)
            N = RG.get_node(name)
            attr = {'label': node.get('label', node['name'])}
            attr.update(self._graph_config[node['type']])
            attr['id'] = node['name']
            if node['type'] in ('state', 'abstract-state', 'missing-state'):
                attr['class'] = 'node state'
            elif node['type'] in ('port', 'dyn-port', 'missing-port'):
                attr['class'] = 'node port'
            elif node['type'] in ('action', 'missing-action'):
                attr['class'] = 'node action'
            elif node['type'] == 'fragment':
                attr['class'] = 'node fragment'
            elif node['type'] == 'type':
                attr['class'] = 'node type'
            N.attr.update(attr)
        for edge in graph_struct['edges']:
            if u'trigger' in edge:
                RG.add_edge(edge['from'], 
                            edge['to'], 
                            label=edge['trigger'],
                            **self._graph_config['edge'][edge['type']])
            else:
                RG.add_edge(edge['from'], 
                            edge['to'], 
                            **self._graph_config['edge'][edge['type']])
        return RG

class Scenarios(DrawModule, DrawAction):
    def setup(self, opts, state_name, userrole, mod):
        self._max_length = opts['max-length']
        self._userrole = userrole
        self._state = state
        DrawModule.setup(self, opts, state)
        self._node = u'any'


    def make_graph(self):
        app = self.current_app
        rmc = app.resource_module_container
        rm = rmc.get_module(self._module_name)
        user_node, state_node = self._get_target_node(rm)
        graph_struct = self._compress_action(rm.make_graph())
        graph_struct['nodes'].append(user_node, state_node)
        graph_struct['edges'].append({'from': user_node['name'], 'to': self._state, 'type': 'scenario'})

    def _get_user_node(self, rm):
        userrole_struct = rm.make_userrole_graph()
        self.__check_start(userrole_struct)
        for n in userrole_struct['nodes']:
            if n['type'] in ('userrole', 'missing-userrole') and n['name'] == self._userrole:
                user_node = n
            elif n['type'] == state and n['name'] == self._state:
                state_node = n
        return user_node, state_node

    def _compress_action(self, graph_struct, start_state):
        new_graph = {
            'name': graph_struct['name'],
            'nodes': [],
            'edges': [],
        }
        for s in self._find_next_state(graph_struct, start_state['name']):
            pass


    def _find_next_state(self, graph_struct, name, length=0):
        for e in graph_struct['edges']:
            if e['from'] == name:
                pass

    def __check_start(self):
        for n in graph_struct['edges']:
            if n['from'] == self._userrole and n['to'] == self._target_action:
                break
        else:
            for n in userrole_struct['nodes']:
                if n['type'] in ('userrole', 'missing-userrole') and n['name'] == self._userrole:
                    break
            else:
                raise throw_caty_exception(
                    'UserroleNotFound',
                    u'Userrole `$userrole` is not defined at $moduleName',
                    userrole = self._userrole,
                    moduleName = self._module_name
                )
            for n in userrole_struct['nodes']:
                if n['type'] == 'state' and n['name'] == self._target_action:
                    break
            else:
                raise throw_caty_exception(
                    'StateNotFound',
                    u'State `$stateName` is not defined at $moduleName',
                    stateName = self._state,
                    moduleName = self._module_name,
                )

    def transform(self, graph_struct, root=True):
        self._node = 'any'
        self._graph_config = {}
        self._graph_config.update(DrawModule._graph_config)
        self._graph_config['userrole'] = DrawAction._graph_config['userrole']
        self._graph_config['edge']['usecase'] = DrawAction._graph_config['edge']['usecase']
        return DrawModule.transform(graph_struct)

