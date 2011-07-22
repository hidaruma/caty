from topdown import *
from creole.syntax.base import WikiParser
from creole.tree import Comment

class InlineComment(WikiParser):
    def __init__(self):
        self.start = '[[['
        self.end = ']]]'

    def __call__(self, seq, start):
        seq.parse(many(' '))
        seq.parse('Comment')
        c = seq.parse(until(self.end))
        _ = seq.parse(option(self.end))
        return Comment(c)
