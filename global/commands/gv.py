# coding: utf-8
from caty.core.command import Builtin
from caty.core.exception import *
import caty.jsontools as json
try:
    from pygraphviz import AGraph
except:
    print '[Warning] graphviz is not install, viva module does not work.'

class Draw(Builtin):
    def setup(self, opts):
        self._out_file = opts['out']
        self._format = opts['format']
        self._font = opts.get('font', None)
        self._strip_xml_decl = False
        self._time = opts.get('time', None)
        self._time_file = opts.get('timefile', None)
        if self._format == 'svge':
            self._format = 'svg'
            self._strip_xml_decl = True
        if self._out_file:
            self._format = self._out_file.split('.')[-1]
            if self._out_file.endswith('.svge'):
                self._strip_xml_decl = True
                self._format = u'svg'
        self._if_modified = opts['if-modified']
        self._engine = opts['engine']

    def execute(self, graph):
        if (self._time_file or self._time_file) and self._out_file and self._if_modified:
            if not self._modified():
                return
        G = self.transform(self._escape_lf(graph))
        G.layout(prog=self._engine)
        if self._out_file:
            o = G.draw(prog=self._engine, format=self._format)
            o = self._strip(o)
            with self.pub.open(self._out_file, 'wb') as f:
                f.write(o)
        else:
            o = G.draw(prog=self._engine, format=self._format)
            o = self._strip(o)
            if self._format in ('svg', 'dot'):
                return unicode(o, 'utf-8')
            else:
                return o

    def _escape_lf(self, obj):
        if isinstance(obj, dict):
            r = {}
            for k, v in obj.items():
                r[k] = self._escape_lf(v)
            return r
        elif isinstance(obj, list):
            r = []
            for v in obj:
                r.append(self._escape_lf(v))
            return r
        elif isinstance(obj, json.TaggedValue):
            t, v = json.split_tag(obj)
            return json.tagged(t, self._escape_lf(v))
        elif isinstance(obj, unicode):
            return obj.replace('\n', '\\n')
        else:
            return obj

    def transform(self, graph, cluster=False):
        type, graph = json.split_tag(graph)
        if cluster:
            name = 'cluster_' + graph['id']
        else:
            name = graph['id']
        if type == 'digraph':
            d = True
        else:
            d = False
        s = True
        G = AGraph(name=name, directed=d, strict=s)
        if self._font:
            G.graph_attr.update(fontname=self._font)
        G.graph_attr.update(graph.get('graph', {}))
        G.node_attr.update(graph.get('node', {}))
        G.edge_attr.update(graph.get('edge', {}))
        for e in graph['elements']:
            type, elem = json.split_tag(e)
            if type == 'node':
                self._add_node(G, elem)
        for e in graph['elements']:
            type, elem = json.split_tag(e)
            if type == 'edge':
                self._add_edge(G, elem)
        for e in graph['elements']:
            type, elem = json.split_tag(e)
            if type == 'cluster':
                self._add_cluster(G, elem)
        return G

    def _add_node(self, graph, node):
        if isinstance(node, basestring):
            graph.add_node(node)
        else:
            i = node.pop('id')
            graph.add_node(i, **node)

    def _add_edge(self, graph, edge, attr={}):
        if isinstance(edge, list):
            s, d = edge
            if isinstance(d, basestring):
                d = [d]
            for i in d:
                graph.add_edge(s, i, **attr)
        else:
            e = edge.pop('nodes')
            self._add_edge(graph, e, edge)

    def _add_cluster(self, graph, cluster):
        c = self.transform(cluster, True)
        sg = graph.add_subgraph(c.iternodes(), c.name, **c.graph_attr)
        for n in c.iternodes():
            a = {}
            a.update(**c.node_attr)
            a.update(n.attr)
            sg.add_node(n.name, **a)
        sg.add_edges_from(c.iteredges())

    def _modified(self):
        with self.pub.open(self._out_file) as out:
            if not out.exists:
                return True
            if self._time:
                return out.last_modified < self._time
            else:
                with self.pub.open(self._time_file) as tf:
                    if not tf.exists:
                        return True
                    else:
                        return out.last_modified < tf.last_modified

    def _strip(self, o):
        if not self._strip_xml_decl: return o
        import xml.dom.minidom as dom
        doc = dom.parseString(o)
        for c in doc.childNodes:
            if c.nodeType == dom.Element.ELEMENT_NODE:
                return c.toxml().replace('<?xml version="1.0" encoding="utf-8"?>', '')

