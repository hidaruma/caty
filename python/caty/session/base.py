from caty.session.value import *
import sys
import uuid
import random
class SessionStorageBase(object):
    def create_session(self, key):
        return SessionInfoWrapper(SessionInfo(key, self))

    def create_id(self):
        return uuid.uuid4().hex
