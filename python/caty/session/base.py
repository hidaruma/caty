from caty.session.value import *
from hashlib import sha1
import sys
import random
class SessionStorage(object):
    def create_session(self, key):
        return SessionInfoWrapper(SessionInfo(key, self))

    def create_id(self):
        return sha1(reduce(lambda a, b: a + b,
                        [str(random.randint(0, sys.maxint - 1)),
                        str(random.randint(0, sys.maxint - 1)),
                        self.secret_key])).hexdigest()

