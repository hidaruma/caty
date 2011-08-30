# coding: utf-8
from caty.core.command import Builtin
from caty.core.exception import *
import pygraphviz as gv

class GraphCmdBase(object):
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
        return rm.make_graph(self._node)

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
            _G = RG.add_subgraph(G.iternodes(), G.name, **G.graph_attr)
            for n in G.iternodes():
                _G.add_node(n.name, **n.attr)
            _G.add_edges_from(G.iteredges())
        for node in graph_struct['nodes']:
            name = node['name']
            RG.add_node(name)
            N = RG.get_node(name)
            attrs = self._graph_config[node['type']]
            N.attr.update(attrs)
            if 'label' in node:
                N.attr['label'] = node['label']
        for edge in graph_struct['edges']:
            if 'trigger' not in edge:
                RG.add_edge(edge['from'], 
                            edge['to'], 
                            **self._graph_config['edge'][edge['type']])
            else:
                RG.add_edge(edge['from'], 
                            edge['to'], 
                            label=edge['trigger'],
                            **self._graph_config['edge'][edge['type']])
        return RG

class Draw(Builtin, GraphCmdBase):
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

import caty.jsontools as json
class GraphStruct(Builtin, GraphCmdBase):
    def setup(self, opts, module_name):
        self._module_name = module_name
        self._node = opts['node']
        self._format = opts['format']
        self._graph_config = {
            'graph': {
                'bgcolor': 'gainsboro',
            },
            'subgraph': {
                'bgcolor': 'gainsboro',
                'color': 'black'
            },
            'edge': {
                'arrowhead': 'open',
                'color': 'crimson'
            },
            'action': {
                'shape': u'box',
                'style': u'filled',
                'color': u'black',
                'fillcolor': u'gold'
            },
            'state': {
                'shape': u'',
                'style': u'filled',
                'color': u'black',
                'fillcolor': u'gold'
            },
        }

    def execute(self):
        src = self.make_graph()
        if self._format == 'internal':
            print json.pp(src)
        else:
            G = self.transform(src)
            G.write()
