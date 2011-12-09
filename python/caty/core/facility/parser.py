from topdown import *
import codecs

class MonadParser(object):
    def __init__(self):
        pass

    def parse(self, path, encoding='utf-8'):
        cs = CharSeq(codecs.open(path, 'rb', encoding).read(), auto_remove_ws=True)
        return many([self.monad, self.comonad, self.bimonad])(cs)

    def monad(self, cs):
        pass

