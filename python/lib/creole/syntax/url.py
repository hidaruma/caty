from __future__ import absolute_import
from topdown import *
from creole.syntax.base import WikiParser

class URL(WikiParser):
    def __init__(self, factory=None):
        self.start = [u'https://', u'http://', u'ftp://']
        self.end = ''
        self.regex = Regex(r'[-\w!@#$%^&*()_=+~:;\',./?]+')
        WikiParser.__init__(self, factory)

    def __call__(self, seq, start):
        url = seq.parse(self.regex)
        return self.create_element('a', [('href', start+url)], [start+url])


