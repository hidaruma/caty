#coding:utf-8
import creole
import types
import caty.jsontools as json

def creole2html(text, language='jp'):
    processor = creole.Processor(language=language)
    return processor.process(text)

def creole2xjx(text, language='jp'):
    processor = creole.Processor(element_handler=XJXHandler(), language=language)
    return processor.process(text)

class XJXHandler(creole.BasicHandler):
    def feed(self, root):
        r = []
        for n in root:
            r.append(self.handle(n))
        return r

    def handle(self, element):
        r = {}
        if element.attrs:
            for k, v in element.attrs:
                r[k] = v
        node = self._mk_node(element.childnode)
        r[''] = node
        return json.tagged(element.tag, r)

    def _mk_node(self, node):
        if isinstance(node, list) or isinstance(node, types.GeneratorType):
            l = []
            for n in node:
                l.append(self._mk_node(n))
            return [i for i in l if i != []]
        else:
            if isinstance(node, basestring):
                return node
            else:
                if node:
                    return self.handle(node)
                else:
                    return []



