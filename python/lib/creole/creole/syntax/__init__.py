from topdown import *
from creole.syntax.base import escape_tilda
from creole.syntax.heading import Heading
from creole.syntax.blockquote import BlockQuote
from creole.syntax.horizonal import Horizonal
from creole.syntax.lists import OrderedList, UnorderedList
from creole.syntax.deflist import DefList
from creole.syntax.preformat import Preformat
from creole.syntax.table import Table
from creole.syntax.section import Section
from creole.syntax.paragraph import Paragraph
from creole.syntax.anchor import Anchor
from creole.syntax.url import URL
from creole.syntax.em import Em
from creole.syntax.strong import Strong
from creole.syntax.tt import TypeWriter
from creole.syntax.nowiki import NoWiki
from creole.syntax.image import Image
from creole.syntax.sub import SubScript
from creole.syntax.sup import SuperScript
from creole.syntax.br import Break
from creole.syntax.plugin import BlockPlugin
from creole.syntax.comment import InlineComment
from creole.tree import Root
from creole.plugin import PluginContainer
import types

class Syntax(object):
    def __init__(self, wiki_url='', language='en', plugins=None):
        self.wiki_url = wiki_url
        self.language = language
        self.inline = self._inline_parser(plugins)
        self.block = self._block_parser()
        self.plugins = plugins or PluginContainer([])

    def process(self, text):
        html = self.block.run(self._normalize_lf(text) + '\n\n')
        return self.create_root(html)

    def create_root(self, html):
        return Root(html)

    def _normalize_lf(self, text):
        return text.replace('\r\n', '\n').replace('\r', '\n')

    def _block_parser(self):
        return combine(*self._remove_line_feed(
                        Heading(self), 
                        try_(Horizonal(self)),
                        try_(DefList(self)),
                        try_(OrderedList(self)),
                        try_(UnorderedList(self)),
                        BlockQuote(self),
                        Preformat(self),
                        Table(self),
                        Section(self),
                        try_(BlockPlugin(self)),
                        Paragraph(self)))

    def _remove_line_feed(self, *components):
        def _remove_lf(f):
            def _wrapped(seq):
                r = f(seq)
                while seq.current == '\n':
                    seq.next()
                return r
            _wrapped.__name__ = f.__class__.__name__
            _wrapped.__doc__ = f.__doc__
            _wrapped.__repr__ = lambda self:repr(f)
            return _wrapped
        return map(_remove_lf, components)

    def _inline_parser(self, plugins):
        return InlineParser(self.wiki_url, plugins)
    
    def call_plugin(self, name, arg=None):
        return self.plugins.get(name).execute(arg)

class InlineParser(Parser):
    def __init__(self, wiki_url, plugins=None):
        self.wiki_url = wiki_url
        #self.plugins = PluginContainer(plugins)
        self._init_parser(wiki_url)

    def _init_parser(self, wiki_url):
        self.wiki_url = wiki_url
        self._parsers = [
            InlineComment(),
            NoWiki(),
            Anchor(self),
            Image(),
            URL(),
            Break(),
            SubScript(self),
            SuperScript(self),
            TypeWriter(self),
            Em(self),
            Strong(self),
        ]
        self._parser_map = {}
        self._start = []
        for p in self._parsers:
            if isinstance(p.start, list):
                for _p in p.start:
                    self._parser_map[_p] = p
                    self._start.append(_p)
            else:
                self._parser_map[p.start] = p
                self._start.append(p.start)

    def call_plugin(self, name, arg=None):
        return self.plugins.get(name).execute(arg)

    def run(self, text, reject=[], contain=[]):
        cs = CharSeq(text)
        return self(cs, reject, contain)

    def __call__(self, seq, reject=[], contain=[]):
        r = []
        _start = [u'~']
        for token in self._start:
            if reject and token in reject:
                continue
            elif contain and token not in contain:
                continue
            _start.append(token)
            
        while not seq.eof:
            p = seq.parse(until(_start))
            if p:
                r.append(p)
            if seq.eof:
                break
            s = seq.parse(_start)
            if s == u'~':
                r.append(seq.current)
                if seq.eof:
                    break
                seq.next()
                continue
            if s in self._parser_map:
                try:
                    v = self._parser_map[s](seq, s)
                except ParseFailed, e:
                    v = s#escape_tilda(s)
                r.append(v)
            else:
                r.append(s)
                #r.append(escape_tilda(s))
        return r



