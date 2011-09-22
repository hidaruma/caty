# coding: utf-8
from caty.core.command import Builtin
from caty.core.exception import *
import pygraphviz as gv

class DrawModule(Builtin):
    def setup(self, opts, module_name):
        self._module_name = module_name
        self._out_file = opts['out']
        self._format = opts['format']
        self._node = opts['node']
        self._size = opts['size']
        self._graph_config = {
            'graph': {
                'bgcolor': 'gainsboro',
                'fontsize': 20.0,
                'labelloc': 't',
            },
            'subgraph': {
                'bgcolor': 'darkolivegreen4',
                'color': 'black',
                'fontsize': 14.0,
            },
            'edge': {
                'action': {
                    'fontsize': 14.0,
                    'arrowhead': 'open',
                    'color': 'crimson'
                },
                'link': {
                    'fontsize': 14.0,
                    'arrowhead': 'open',
                    'color': 'darkorchid3',
                }, 
                'redirect': {
                    'fontsize': 14.0,
                    'arrowhead': 'open',
                    'color': 'blue3',
                },
            },
            'action': {
                'fontsize': 14.0,
                'shape': u'ellipse',
                'style': u'filled',
                'color': u'black',
                'fillcolor': u'darkseagreen2'
            },
            'state': {
                'fontsize': 14.0,
                'shape': u'box',
                'style': u'filled',
                'color': u'black',
                'fillcolor': u'gold'
            },
            'external': {
                'fontsize': 14.0,
                'shape': u'ellipse',
                'style': u'filled',
                'color': u'black',
                'fillcolor': u'azure'
            },
        }

    def execute(self):
        src = self.make_graph()
        G = self.transform(src)
        G.layout(prog='dot')
        if self._out_file:
            o = G.draw(prog='dot', format=self._out_file.split('.')[-1])
            with self.pub.open('/'+self._out_file, 'wb') as f:
                f.write(o)
        else:
            o = G.draw(prog='dot', format=self._format)
            if self._format == 'dot':
                return unicode(o, 'utf-8')
            else:
                return o

    def make_graph(self):
        app = self.current_app
        rmc = app.resource_module_container
        rm = rmc.get_module(self._module_name)
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
            cfg.update(self._graph_config['subgraph'])
            cfg['name'] = 'cluster_' + graph_struct['name']
        if self._size != 'auto':
            cfg['size'] = self._size
        RG = gv.AGraph(**cfg)
        if root:
            RG.graph_attr['label'] = 'Module: ' + graph_struct['name']

        else:
            RG.graph_attr['label'] = graph_struct['name']
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
            if (self._node == 'state' 
                  and node['type'] != 'state'):
                attr['label'] = ''
                attr['shape'] = 'circle'
                attr['width'] = '0.2'
            elif (self._node == 'action' 
                and node['type'] != 'action'):
                attr['label'] = ''
                attr['width'] = '0.2'
                if node['type'] == 'external':
                    attr['shape'] = 'circle'
                else:
                    attr['shape'] = 'box'
                    attr['height'] = '0.2'
            else:
               attr['label'] = node['label']
            N.attr.update(attr)
        for edge in graph_struct['edges']:
            if 'trigger' not in edge or self._node == 'action':
                RG.add_edge(edge['from'], 
                            edge['to'], 
                            **self._graph_config['edge'][edge['type']])
            else:
                cfg.update(self._graph_config['edge'][edge['type']])
                RG.add_edge(edge['from'], 
                            edge['to'], 
                            taillabel=edge['trigger'],
                            **cfg)
        return RG


class DrawAction(Builtin):
    def setup(self, opts, action_name):
        self._action_name = action_name
        self._out_file = opts['out']
        self._format = opts['format']
        self._graph_config = {
            'graph': {
                'bgcolor': 'gainsboro',
                'fontsize': 20.0,
                'labelloc': 't',
            },
            'subgraph': {
                'bgcolor': 'darkseagreen2',
                'color': 'black',
                'fontsize': 14.0,
            },
            'edge': {
                'relay': {
                    'fontsize': 14.0,
                    'arrowhead': 'open',
                    'color': 'brown4',
                    'style': 'dotted',
                },
                'link': {
                    'fontsize': 14.0,
                    'arrowhead': 'open',
                    'color': 'darkorchid3',
                }, 
                'redirect': {
                    'fontsize': 14.0,
                    'arrowhead': 'open',
                    'color': 'blue3',
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
                'shape': u'ellipse',
                'style': u'filled',
                'color': u'black',
                'fillcolor': u'azure1'
            },
            'state': {
                'fontsize': 14.0,
                'shape': u'box',
                'style': u'filled',
                'color': u'black',
                'fillcolor': u'gold'
            },
            'action': {
                'fontsize': 14.0,
                'shape': u'box',
                'style': u'filled',
                'color': u'black',
                'fillcolor': u'darkseagreen2'
            },
        }

    def execute(self):
        src = self.make_graph()
        G = self.transform(src)
        G.layout(prog='dot')
        if self._out_file:
            o = G.draw(prog='dot', format=self._out_file.split('.')[-1])
            with self.pub.open('/'+self._out_file, 'wb') as f:
                f.write(o)
        else:
            o = G.draw(prog='dot', format=self._format)
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
        return act.make_graph(rm)

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
            attr = {}
            attr.update(self._graph_config[node['type']])
            N.attr.update(attr)
        for edge in graph_struct['edges']:
            if u'trigger' in edge:
                RG.add_edge(edge['from'], 
                            edge['to'], 
                            taillabel=edge['trigger'],
                            **self._graph_config['edge'][edge['type']])
            else:
                RG.add_edge(edge['from'], 
                            edge['to'], 
                            **self._graph_config['edge'][edge['type']])
        return RG


