from topdown import *
from creole.syntax.base import WikiParser

class Anchor(WikiParser):
    def __init__(self, syntax, factory=None):
        wiki_url = syntax.wiki_url
        self.wiki_url = wiki_url if (wiki_url.endswith('/') or wiki_url == '') else wiki_url + '/'
        self.start = '[['
        self.end = ']]'
        WikiParser.__init__(self, factory)
        self.syntax = syntax

    def __call__(self, seq, start):
        url = seq.parse(until([']]', '|']))
        if seq.current == '|':
            seq.parse('|')
            text = seq.parse(until(']]'))
            seq.parse(']]')
            if url.startswith('>'):
                url = url[1:]
                attr = [('href', url.replace('\n', '')), ('target', '_blank')]
            else:
                attr = [('href', url.replace('\n', ''))]
        else:
            seq.parse(']]')
            if url.startswith('>'):
                url = url[1:]
                attr = [('href', self.wiki_url + url.replace('\n', '')), ('target', '_blank')]
            else:
                attr = [('href', self.wiki_url + url.replace('\n', ''))]
            text = url.replace('\n', '')
        return self.create_element('a', attr, self.syntax.run(text, contain=['{{']))

