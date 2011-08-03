#coding: utf-8
from caty.core.command import Builtin
from caty.core.facility import Facility, AccessManager
from caty.util.path import join
from caty.jsontools import tagged

name = 'user'
schema = u"""
type UserInfo = {
    "userid": string,    // ID。この値は一意でなければならない。
    "username": string?, // 名前。必須ではない
    "role": [string(minLength=1)*]?, // 必要ないなら使わなくてよい
    *: any, // 他のオプショナルな項目は何でも良い
};

type RegistryInfo = UserInfo & {
    "password": string,
    *: any
};
"""

class User(Facility):
    def __init__(self, info=None):
        self._info = {} if not info else info
        self._loggedin = False if self._info == {} else True

    am = AccessManager()
    
    @am.update
    def set_user_info(self, info):
        self._info.update(info)
        self._loggedin = True

    @am.read
    def __getattr__(self, k):
        return self._info[k]

    @am.update
    def clear(self):
        self._info = {}

    @am.read
    def to_dict(self):
        if self._info != {}:
            return self._info
        else:
            return {
                'userid': u'',
            }

    @property
    @am.read
    def loggedin(self):
        return self._loggedin

    def clone(self):
        return self
    

class ExistsUser(Builtin):

    def execute(self, input):
        storage = self.storage('user')
        r = list(storage.select({'userid': input}, -1, 0))
        return len(r) == 1

from caty.util.collection import merge_dict
class AddUser(Builtin):

    def execute(self, input):
        storage = self.storage('user')
        userid = input['userid'].strip()
        password = unicode(generate_password(input['password'].strip()))
        grant = map(unicode.strip, input['grant']) if 'grant' in input else None
        if '' in (userid, password):
            return False
        if len(list(storage.select({'userid':userid}))) != 0:
            return False
        new = {'userid': userid,
               'password': password,}
        if grant is not None:
            new['grant'] = grant
        storage.insert(merge_dict(new, input, 'pre'))
        return True

class DelUser(Builtin):

    def execute(self, input):
        storage = self.storage('user')
        userid = input
        if len(list(storage.select({'userid':userid}))) == 0:
            return False
        storage.delete({'userid':userid})
        return True

class ChangePassword(Builtin):

    def execute(self, input):
        storage = self.storage('user')
        userid = input['userid'].strip()
        password = unicode(generate_password(input['password'].strip()))
        old = storage.select1({'userid':userid})
        storage.update(old, {'password': pasword})
        return True

class GetUserInfo(Builtin):

    def execute(self):
        return self.user.to_dict()

class UpdateInfo(Builtin):

    def execute(self):
        info = self.storage('user').select1({'userid':self.user.userid})
        self.user.set_user_info(info)
        


from hashlib import sha1
import sys
from time import time
from threading import RLock
import random
import caty.jsontools as json

def generate_password(s):
    salt = sha1(str(int(time()) + random.randint(0, sys.maxint - 1))).hexdigest()
    password = sha1(salt + s).hexdigest()
    return salt + password

def authenticate(incoming, password):
    salt = password[0:40]
    p = password[40:]
    a = sha1(salt + incoming).hexdigest()
    return a == p

