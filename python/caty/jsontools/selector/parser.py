
from topdown import *
from caty.jsontools import stdjson
from caty.jsontools import xjson
from caty.jsontools.selector import stm as default_factory
from caty.core.spectypes import UNDEFINED
from caty.core.language import name_token

class JSONPathSelectorParser(Parser):
    def __init__(self, empty_when_error=False, ignore_rest=False, factory=None):
        Parser.__init__(self)
        self.empty_when_error = empty_when_error
        self.ignore_rest = ignore_rest
        self.factory = factory if factory else default_factory

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
        o = self.factory.SelectorWrapper(o)
        optional = option(u'?')(seq)
        if optional and option('=')(seq):
            d = xjson.parse(seq)
        else:
            d = UNDEFINED
        if not seq.eof and not self.ignore_rest:
            raise ParseFailed(seq, self)
        o.set_optional(optional)
        o.set_default(d)
        return o

    def apply_option(self, stm):
        stm.empty_when_error = self.empty_when_error
        return stm

    def dot(self, seq):
        seq.parse('.')
        def _(a, b):
            #self.apply_option(a)
            #self.apply_option(b)
            return a.chain(b)
        return _

    def all(self, seq):
        seq.parse('$')
        return self.factory.AllSelector()

    def name(self, seq):
        key = seq.parse([self.namestr, lambda s:self.quoted(s, '"'), lambda s: self.quoted(s, "'")])
        optional = False
        #optional = option(u'?')(seq)
        return self.factory.PropertySelector(key, optional)

    def namestr(self, seq):
        return seq.parse(name_token)

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
        idx = int(seq.parse(Regex(r'([0-9]+)')))
        optional = False
        #optional = option(u'?')(seq)
        return self.factory.ItemSelector(idx, optional)

    def namewildcard(self, seq):
        seq.parse('*')
        return self.factory.NameWildcardSelector()

    def itemwildcard(self, seq):
        seq.parse('#')
        return self.factory.ItemWildcardSelector()

    def oldtag(self, seq):
        seq.parse('^')
        name = seq.parse(option([self.namestr, lambda s:self.quoted(s, '"'), lambda s: self.quoted(s, "'")], None))
        if name is not None:
            return TagSelector(name, False)
        t = seq.parse(['*', '^'])
        if t == '*':
            e = seq.parse(option('!', None))
            return self.factory.TagSelector(None, bool(e))
        else:
            e = seq.parse(option('!', None))
            return self.factory.TagReplacer(None, bool(e))

    def tag(self, seq):
        seq.parse('tag()')
        return self.factory.TagNameSelector(False)

    def exp_tag(self, seq):
        seq.parse('exp-tag()')
        return self.factory.TagNameSelector(True)

    def untagged(self, seq):
        v = seq.parse(choice('untagged()', 'content()'))
        return self.factory.TagContentSelector(v)

    def length(self, seq):
        seq.parse('length()')
        return self.factory.LengthSelector()
