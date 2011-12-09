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
        o = self._facilities.app._system.to_name_tree()
        if self._out_file:
            if self._format == 'json':
                o = json.dumps(o)
            with self._facilities['pub'].open(self._out_file, 'wb') as f:
                f.write(o)
        else:
            return o
