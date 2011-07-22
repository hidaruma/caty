from topdown import *
try:
    import json
except:
    try:
        import simplejson as json
    except:
        print 'Python 2.6 or simplejson library is required.'
        raise
__all__ = ['quoted_string', 'boolean', 'integer', 'number', 'null']
import itertools
@try_
def quoted_string(seq):
    def series_of_escape(s):
        import itertools
        return len(list(itertools.takewhile(lambda c: c=='\\', reversed(s))))
    try:
        seq.ignore_hook = True
        st = [seq.parse('"')]
        s = seq.parse(until('"'))
        while True:
            if series_of_escape(s) % 2 == 0:
                st.append(s)
                break
            else:
                st.append(s)
                s = seq.parse(Regex(r'"[^"]*'))
        st.append(seq.parse('"'))
        return json.loads(''.join(st))
    except EndOfBuffer, e:
        raise ParseFailed(seq, string)
    finally:
        seq.ignore_hook = False

def boolean(seq):
    b = seq.parse(['true', 'false'])
    return True if b == 'true' else False

def integer(seq):
    i = seq.parse([
                   Regex(r'-?[1-9][0-9]+'),
                   Regex(r'-?[0-9]'),
                 ])
    return int(i)

def number(seq):
    n = seq.parse([
                   Regex(r'-?[1-9][0-9]+\.[0-9]+([eE][-+]?[0-9]+)?'), 
                   Regex(r'-?[0-9]\.[0-9]+([eE][-+]?[0-9]+)?'), 
                   Regex(r'-?[1-9][0-9]+[eE][-+]?[0-9]+'),
                   Regex(r'-?[0-9][eE][-+]?[0-9]+'),
                   ])
    return float(n)

def null(seq):
    n = seq.parse('null')
    return None


