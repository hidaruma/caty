
from topdown import *
from caty.jsontools.selector.stm import *
from caty.jsontools import stdjson

class JSONPathSelectorParser(Parser):
    def __init__(self, empty_when_error=False, ignore_rest=False):
        Parser.__init__(self)
        self.empty_when_error = empty_when_error
        self.ignore_rest = ignore_rest

    def __call__(self, seq):
        o = chainl([self.all, 
                    self.tag,
                    self.exp_tag,
                    self.untagged,
                    self.length,
                    self.name, 
                    self.index, 
                    self.namewildcard, 
                    self.itemwildcard, 
                    try_(self.oldtag),
                    ], self.dot)(seq)
        if not seq.eof and not self.ignore_rest:
            raise ParseFailed(seq, self)
        return o

    def apply_option(self, stm):
        stm.empty_when_error = self.empty_when_error
        return stm

    def dot(self, seq):
        seq.parse('.')
        def _(a, b):
            self.apply_option(a)
            self.apply_option(b)
            return a.chain(b)
        return _

    def all(self, seq):
        seq.parse('$')
        return AllSelector()

    def name(self, seq):
        key = seq.parse([self.namestr, lambda s:self.quoted(s, '"'), lambda s: self.quoted(s, "'")])
        optional = option(u'?')(seq)
        return PropertySelector(key, optional)

    def namestr(self, seq):
        return seq.parse(Regex(r'[a-z_A-Z][-a-zA-Z_0-9]*'))

    def quoted(self, seq, qc):
        def series_of_escape(s):
            import itertools
            return len(list(itertools.takewhile(lambda c: c=='\\', reversed(s))))
        try:
            seq.ignore_hook = True
            st = [seq.parse(qc)]
            s = seq.parse(until(qc))
            while True:
                if series_of_escape(s) % 2 == 0:
                    st.append(s)
                    break
                else:
                    st.append(s)
                    s = seq.parse(Regex(r'%s[^%s]*' % (qc, qc)))
            st.append(seq.parse(qc))
            return stdjson.loads('"%s"'%''.join(st[1:-1]))
        except EndOfBuffer, e:
            raise ParseFailed(seq, string)
        finally:
            seq.ignore_hook = False

    def index(self, seq):
        idx = int(seq.parse(Regex(r'([0-9]|[1-9][0-9]+)')))
        optional = option(u'?')(seq)
        return ItemSelector(idx, optional)

    def namewildcard(self, seq):
        seq.parse('*')
        return NameWildcardSelector()

    def itemwildcard(self, seq):
        seq.parse('#')
        return ItemWildcardSelector()

    def oldtag(self, seq):
        seq.parse('^')
        name = seq.parse(option([self.namestr, lambda s:self.quoted(s, '"'), lambda s: self.quoted(s, "'")], None))
        if name is not None:
            return TagSelector(name, False)
        t = seq.parse(['*', '^'])
        if t == '*':
            e = seq.parse(option('!', None))
            return TagSelector(None, bool(e))
        else:
            e = seq.parse(option('!', None))
            return TagReplacer(None, bool(e))

    def tag(self, seq):
        seq.parse('tag()')
        return TagNameSelector(False)

    def exp_tag(self, seq):
        seq.parse('exp-tag()')
        return TagNameSelector(True)

    def untagged(self, seq):
        v = seq.parse(choice('untagged()', 'content()'))
        return TagContentSelector(v)

    def length(self, seq):
        seq.parse('length()')
        return LengthSelector()
