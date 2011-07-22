#coding: utf-8
from caty.testutil import TestCase
from caty.fit.behparser import *
from caty.fit.document import *

class DocumentTest(TestCase):
    def test1(self):
        text = u"""
= TestName1

paragraph.

== exec;

|= input |= command|= output|
|"foo"   | cmd1 | 0  |
|"bar"   | cmd2 | 1  |
|"buz"   | cmd3 | 2  |
"""
        document = make_document(parser.run(text))
        runner = FakeRunner()
        document.accept(runner)
        self.assertEquals(len(runner.setups), 0)
        self.assertEquals(len(runner.triples), 1)
        self.assertEquals(runner.title, 'TestName1')


    def test2(self):
        text = u"""
= TestName2

paragraph.

== setup;

セットアップセクション。

=== file: /foo.txt

{{{
aaa
}}}

=== file: /bar.txt

{{{
bbb
}}}

== exec;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |
"""
        document = make_document(parser.run(text))
        runner = FakeRunner()
        document.accept(runner)
        self.assertEquals(len(runner.setups), 1)
        self.assertEquals(len(runner.triples), 1)
        self.assertEquals(runner.title, 'TestName2')

    def test3(self):
        text = u"""
= TestName3

paragraph.

== setup;

セットアップセクション。

=== file: /foo.txt

{{{
aaa
}}}

=== file: /bar.txt

{{{
bbb
}}}

== precond;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |

== exec;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |
"""
        document = make_document(parser.run(text))
        runner = FakeRunner()
        document.accept(runner)
        self.assertEquals(len(runner.setups), 1)
        self.assertEquals(len(runner.triples), 1)
        self.assertEquals(runner.title, 'TestName3')

    def test4(self):
        text = u"""
= TestName4

paragraph.

== setup;

セットアップセクション。

=== file: /foo.txt

{{{
aaa
}}}

=== file: /bar.txt

{{{
bbb
}}}

== precond;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |

== exec;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |

== postcond;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |
"""
        document = make_document(parser.run(text))
        runner = FakeRunner()
        document.accept(runner)
        self.assertEquals(len(runner.setups), 1)
        self.assertEquals(len(runner.triples), 1)
        self.assertEquals(runner.title, 'TestName4')

    def test5(self):
        text = u"""
= TestName5

paragraph.

== setup;

セットアップセクション。

=== file: /foo.txt

{{{
aaa
}}}

=== file: /bar.txt

{{{
bbb
}}}

== precond;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |

== exec;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |

== postcond;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |

== precond;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |

== exec;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |

== postcond;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |


"""
        document = make_document(parser.run(text))
        runner = FakeRunner()
        document.accept(runner)
        self.assertEquals(len(runner.setups), 1)
        self.assertEquals(len(runner.triples), 2)
        self.assertEquals(runner.title, 'TestName5')


    def test6(self):
        text = u"""
= TestName6

paragraph.

== setup;

セットアップセクション。

=== file: /foo.txt

{{{
aaa
}}}

=== file: /bar.txt

{{{
bbb
}}}

== precond;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |

== exec;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |


== precond;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |

== exec;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |

== postcond;

|= command|= output|
| cmd1 | 0  |
| cmd2 | 1  |
| cmd3 | 2  |


"""
        document = make_document(parser.run(text))
        runner = FakeRunner()
        document.accept(runner)
        self.assertEquals(len(runner.setups), 1)
        self.assertEquals(len(runner.triples), 2)
        self.assertEquals(runner.title, 'TestName6')




class FakeRunner(object):
    def __init__(self):
        self.setups = []
        self.triples = []
        self.nodes = []
        self.title = u''

    def set_title(self, t):
        self.title = t

    def add(self, node):
        if node.type == 'setup':
            self.setups.append(node)
        elif node.type == 'triple':
            self.triples.append(node)
        self.nodes.append(node)
