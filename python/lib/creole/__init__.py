from creole.syntax import Syntax
import types

class Processor(object):
    def __init__(self, wiki_url='', element_handler=None, language='en'):
        self.parser = Syntax(wiki_url, language)
        self.element_handler = element_handler if element_handler else BasicHandler()

    def process(self, text):
        element_tree = self.parser.process(text)
        return self.element_handler.feed(element_tree)

class BasicHandler(object):
    def feed(self, root):
        return ''.join(map(self.handle, root.childnode))

    def handle(self, element):
        if element.attrs:
            attr = u' '.join(map(lambda s:u'%s="%s"' % (s[0], self.escape(self.join_attr(s[1]))), element.attrs))
        else:
            attr = u''
        node = self._mk_node(element.childnode)
        if node:
            if attr:
                r = u'<%s %s>%s</%s>' % (element.tag, attr, node, element.tag)
            else:
                r = u'<%s>%s</%s>' % (element.tag, node, element.tag)
        else:
            if attr:
                r = u'<%s %s/>' % (element.tag, attr)
            else:
                r = u'<%s/>' % (element.tag)
        if element.tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'li', 'table', 'tr', 'pre'):
            r = '\n%s\n' % r
        return r

    def _mk_node(self, node):
        if isinstance(node, list) or isinstance(node, types.GeneratorType):
            l = []
            for n in node:
                l.append(self._mk_node(n))
            return ''.join(l)
        else:
            if isinstance(node, basestring):
                return self.escape(node)
            else:
                if node:
                    return self.handle(node)
                else:
                    return None

    def escape(self, s):
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace('\\ ', '').replace('\'', '&#39;')

    def join_attr(self, attr):
        if isinstance(attr, basestring):
            return attr
        else:
            return ' '.join(attr)


