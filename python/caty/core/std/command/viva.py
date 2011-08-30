# coding: utf-8
from caty.core.command import Builtin
from caty.core.exception import *
import pygraphviz as gv

class Draw(Builtin):
    def setup(self, opts, module_name):
        self._module_name = module_name
        self._out_file = opts['out']
        self._format = opts['format']
        self._node = opts['node']
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
            },
            'action': {
                'fontsize': 14.0,
                'shape': u'box',
                'style': u'filled',
                'color': u'black',
                'fillcolor': u'darkseagreen2'
            },
            'state': {
                'fontsize': 14.0,
                'style': u'filled',
                'color': u'black',
                'fillcolor': u'gold'
            },
            'external': {
                'fontsize': 14.0,
                'style': u'filled',
                'color': u'black',
                'fillcolor': u'azure'
            },
        }

    def execute(self):
        src = self.make_graph()
        G = self.transform(src)
        G.layout()
        draw_param = {
            'format': self._format,
            'prog': 'dot'
        }
        o = G.draw(**draw_param)
        if self._out_file:
            with self.pub.open('/'+self._out_file, 'wb') as f:
                f.write(o)
        else:
            if self._format == 'dot':
                return unicode(o, 'utf-8')
            else:
                return o

    def make_graph(self):
        app = self.current_app
        rmc = app.resource_module_container
        rm = rmc.get_module(self._module_name)
        if not rm:
            throw_caty_exception(
                u'ModuleNotFound',
                u'$moduleName.$moduleType is not defined in $appName',
                moduleName=self._module_name,
                moduleType=u'cara',
                appName=app.name
            )
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
            if ((self._node == 'state' 
                and node['type'] != 'state')
               or (self._node == 'action' 
                and node['type'] != 'action')):
               attr['label'] = ''
               attr['shape'] = 'circle'
               attr['width'] = '0.2'
            else:
               attr['label'] = node['label']
            N.attr.update(attr)
        for edge in graph_struct['edges']:
            if 'trigger' not in edge or self._node == 'action':
                RG.add_edge(edge['from'], 
                            edge['to'], 
                            **self._graph_config['edge'][edge['type']])
            else:
                if edge['trigger'].startswith('+'):
                    cfg = {'arrowtail': 'ediamond', 'dir': 'both'}
                else:
                    cfg = {'arrowtail': 'diamond', 'dir': 'both'}
                cfg.update(self._graph_config['edge'][edge['type']])
                RG.add_edge(edge['from'], 
                            edge['to'], 
                            label=edge['trigger'],
                            **cfg)
        return RG


