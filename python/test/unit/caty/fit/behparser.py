#coding: utf-8
from caty.testutil import TestCase
from caty.fit.behparser import *


class ParserTest(TestCase):
    def test_case1(self):
        text = u"""
= Heading1

paragraph1.


== Heading2 ==

paragraph2.
paragraph2, too.
"""
        expected = [
            Heading('Heading1', 1, 0),
            Paragraph('paragraph1.', 0),
            Heading('Heading2', 2, 0),
            Paragraph('paragraph2.\nparagraph2, too.', 0),
        ]
        self.assertTrue(zip_eq(expected, parser.run(text)))

    def test_case2(self):
        text = u"""
|= head1 |= head2 |= head3|
|  data1 |  data2 |  data3|
|  data4 |  data5 |  data6|
"""
        expected = [
            Table(
                [
                    Row([HeaderCell('head1', 0), HeaderCell('head2', 0), HeaderCell('head3', 0)], 0),
                    Row([DataCell('data1', 0), DataCell('data2', 0), DataCell('data3', 0)], 0),
                    Row([DataCell('data4', 0), DataCell('data5', 0), DataCell('data6', 0)], 0),
                ], 0
            )
        ]
        self.assertTrue(zip_eq(expected, parser.run(text)))

    def test_case3(self):
        text = u"""
{{{
=== aaa
    bbb
        ccc
}}}
"""
        expected = [
            Code('=== aaa\n    bbb\n        ccc', 0)
        ]
        self.assertTrue(zip_eq(expected, parser.run(text)))


def zip_eq(a, b):
    return len(a) == len(b) and all(map(lambda x:x[0] == x[1], zip(a, b)))

def dump(x):
    for a in x:
        print a
        print

