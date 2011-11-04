#coding:utf-8
import creole
import types
import caty.jsontools as json

def creole2html(text, language='jp'):
    processor = CreoleExProcessor(element_handler=creole.BasicHandler(), 
                                  language=language,
                                  plugins=creole.plugin.PluginContainer([CommentPlugin()]))
    return processor.process(text)

def creole2xjx(text, language='jp'):
    processor = CreoleExProcessor(element_handler=XJXHandler(), 
                                  language=language,
                                  plugins=creole.plugin.PluginContainer([CommentPlugin()]))
    return processor.process(text)

class CreoleExProcessor(creole.Processor):
    def __init__(self, wiki_url='', 
                       element_handler=None, 
                       language='en',
                       plugins=None):
        self.parser = CreoleExSyntax(wiki_url, language, plugins=plugins)
        self.element_handler = element_handler if element_handler else creole.BasicHandler()

from creole.syntax.heading import Heading
from creole.syntax.blockquote import BlockQuote
from creole.syntax.horizonal import Horizonal
from creole.syntax.lists import OrderedList, UnorderedList
from creole.syntax.deflist import DefList
from creole.syntax.preformat import Preformat
from creole.syntax.table import Table
from creole.syntax.section import Section
from creole.syntax.paragraph import Paragraph
from creole.syntax.plugin import BlockPlugin
class CreoleExSyntax(creole.syntax.Syntax):
    def _block_parser(self):
        return combine(*self._remove_line_feed(
                        Heading(self), 
                        try_(Horizonal(self)),
                        try_(DefList(self)),
                        try_(OrderedList(self)),
                        try_(UnorderedList(self)),
                        BlockQuote(self),
                        Literate(self),
                        Preformat(self),
                        Table(self),
                        Section(self),
                        try_(BlockPlugin(self)),
                        Paragraph(self)))

from topdown import *
from topdown.util import line_by_itself
from creole.syntax.base import BlockParser

class Literate(BlockParser):

    def __call__(self, seq):
        _ = seq.parse(line_by_itself('<<{'))
        t = u'\n'
        while not seq.eof:
            t += until('}>>')(seq)
            if not t.endswith('\n'):
                if t.endswith(' '):
                    t = t[:-1]
                t += seq.parse('}>>')
            else:
                seq.parse(option(line_by_itself('}>>'), u''))
                break
        return self.create_element('pre', [('class', 'sh_caty')], [t])


from creole.plugin import Plugin
class CommentPlugin(Plugin):
    def __init__(self):
        self.name = u'ignore'

    def execute(self, arg):
        return creole.tree.Comment(arg)

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



