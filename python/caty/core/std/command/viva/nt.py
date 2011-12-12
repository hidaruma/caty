# coding: utf-8
from caty.core.command import Internal
from caty.core.exception import *
import caty.jsontools.stdjson as json
try:
    import pygraphviz as gv
except:
    print '[Warning] graphviz is not install, viva module does not work.'

class DrawNT(Internal):
    def setup(self, opts):
        self._out_file = opts['out']
        self._format = opts['format']
        self._font = opts['font']
        if self._out_file:
            self._format = self._out_file.split('.')[-1]
            if self._out_file.endswith('.svge'):
                self._strip_xml_decl = True
                self._format = u'svg'

    def execute(self):
        G = self._transform(self._facilities.app.to_name_tree())
        if self._out_file:
            if self._format == 'json':
                o = json.dumps(G)
            else:
                o = G.draw(prog='dot', format=self._format)
            with self._facilities['pub'].open(self._out_file, 'wb') as f:
                f.write(o)
        else:
            if self._format == 'json':
                return G
            elif self._format == 'dot':
                return unicode(o, 'utf-8')
            else:
                return o

    def _transform(self, obj):
        if self._format == 'json':
            return obj
        cfg = {
            'strict': True,
            'directed': True,
            'label': self._facilities.app.name,
        }
        G = gv.AGraph(**cfg)
        if self._font:
            G.graph_attr.update(fontname=self._font)
        self._make_graph(obj, G)
        G.layout(prog='dot')
        return G


    def _make_graph(self, obj, G):
        G.add_node(self.__get_id(obj))
        N = G.get_node(self.__get_id(obj))
        if obj['kind'].startswith('i:'):
            N.attr['shape'] = 'triangle'
        elif obj['kind'].startswith('c:'):
            N.attr['shape'] = 'box'
        elif obj['kind'].startswith('ns:'):
            N.attr['shape'] = 'ellipse'
        N.attr['label'] = obj['kind']
        for k, v in obj['childNodes'].items():
            assert isinstance(v, dict), obj
            self._make_graph(v, G)
            G.add_edge(self.__get_id(obj), self.__get_id(v), label=k)
        return G

    def __get_id(self, o):
        try:
            return o.get('id', o['kind'])
        except:
            print o
            raise
