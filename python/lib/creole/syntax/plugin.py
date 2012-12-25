from __future__ import absolute_import
from topdown import *
from topdown.util import *
from creole.syntax.base import WikiParser, BlockParser

class BlockPlugin(BlockParser):
    def __call__(self, seq):
        _ = seq.parse(Regex(' *<<'))
        skip_ws(seq)
        name = seq.parse(Regex('[a-zA-Z][a-zA-Z0-9_-]*'))
        skip_ws(seq)
        raw_arg = until(u'>>')(seq).strip()
        line_by_itself('>>')(seq)
        skip_ws(seq)
        return self.syntax.call_plugin(name, raw_arg)

