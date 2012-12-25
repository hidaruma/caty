from topdown import *
import unittest

class TestCharSeq(unittest.TestCase):
    def test_string(self):
        cs = CharSeq('abcd\nef')
        ae = self.assertEquals
        ae(cs.parse('a'), 'a')
        ae(cs.parse('bc'), 'bc')
        ae(cs.parse('d\n'), 'd\n')
        ae(cs.rest, 'ef')

    def test_regex(self):
        cs = CharSeq('abcd\nef')
        ae = self.assertEquals
        ae(cs.parse(Regex(r'(a|b)*')), 'ab')
        ae(cs.parse(Regex(r'(c|d|e|\s)*')), 'cd\ne')
        ae(cs.rest, 'f')

    def test_list(self):
        cs = CharSeq('abcd\nef')
        ae = self.assertEquals
        ae(cs.parse(['a', 'b', 'c', Regex(r'd|\s')]), 'a')
        ae(cs.parse(['a', 'b', 'c', Regex(r'd|\s')]), 'b')
        ae(cs.parse(['a', 'b', 'c', Regex(r'd|\s')]), 'c')
        ae(cs.parse(['a', 'b', 'c', Regex(r'd|\s')]), 'd')
        ae(cs.parse(['a', 'b', 'c', Regex(r'd|\s')]), '\n')
        ae(cs.rest, 'ef')

    def test_function(self):
        cs = CharSeq('abcd\nef')
        ae = self.assertEquals
        ae(cs.parse(lambda seq: seq.parse('abc')), 'abc')
        ae(cs.rest, 'd\nef')

    def test_parse_class(self):
        class P(Parser):
            def __call__(self, seq):
                a = seq.parse('a')
                b = seq.parse('b')
                c = seq.parse('c')
                return a, b, c

        cs = CharSeq('abcd\nef')
        ae = self.assertEquals
        ae(cs.parse(P()), ('a', 'b', 'c'))
        ae(cs.rest, 'd\nef')

        cs = CharSeq('abcd\nef')
        ae = self.assertEquals
        ae(P()(cs), ('a', 'b', 'c'))
        ae(cs.rest, 'd\nef')

    def test_eof(self):
        cs = CharSeq('a')
        ae = self.assertEquals
        ar = self.assertRaises
        ae(cs.parse('a'), 'a')
        ar(EndOfBuffer, cs.parse, 'a')

    def test_fail(self):
        cs = CharSeq(' a')
        ae = self.assertEquals
        ar = self.assertRaises
        ar(ParseFailed, cs.parse, 'a')

    def test_skip(self):
        cs = CharSeq(' a\rb\nc\t ', auto_remove_ws=True)
        ae = self.assertEquals
        ae(cs.parse('a'), 'a')
        ae(cs.parse('b'), 'b')
        ae(cs.parse('c'), 'c')
        ae(cs.rest, '')

    def test_peek(self):
        cs = CharSeq('abc')
        ae = self.assertEquals
        ae(cs.peek('a'), 'a')
        ae(cs.current, 'a')
        ae(cs.peek('a'), 'a')
        ae(cs.current, 'a')
        ae(cs.rest, 'abc')

    def test_back(self):
        cs = CharSeq('abc')
        ae = self.assertEquals
        ae(cs.back(), 'a')
        ae(cs.current, 'a')
        ae(cs.parse('a'), 'a')
        ae(cs.parse('b'), 'b')
        ae(cs.back(), 'b')
        ae(cs.current, 'b')
        ae(cs.back(), 'a')
        ae(cs.current, 'a')

    def test_fail(self):
        cs = CharSeq('abc')
        ar = self.assertRaises
        ar(ParseFailed, cs.parse, 'b')
        ar(ParseFailed, cs.parse, ['b', 'c'])
        ar(ParseFailed, cs.parse, Regex(r'x|y|z'))
        ar(ParseFailed, cs.parse, lambda seq: seq.parse('1'))


