#coding: utf-8
from caty.core.command import Builtin
from caty.core.facility import Facility, AccessManager
from caty.util.path import join
from caty.jsontools import tagged
from Cookie import Morsel
from caty.core.std.command.authutil import CATY_USER_INFO_KEY

name = 'user'

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

class Login(Builtin):

    def execute(self, input):
        userid = input['userid']
        password = input['password']
        storage = self.storage('user')
        try:
            user = storage.select1({'userid': userid})
            succ = authenticate(password, user['password'])
        except:
            succ = False
        if succ:
            session = self.session.storage.create().dual_mode
            self.session = session
            del user['password']
            self.user.set_user_info(user)
            session.put(CATY_USER_INFO_KEY, user)
            redirect_path = u'/' if not 'succ' in input else input['succ']
            redirect = {
            'header': {
                'Location': unicode(join(self.env.get('HOST_URL'), redirect_path)),
                'Set-Cookie': unicode(self._mk_cookie(session.key)),
            },
            'status': 302}
            return tagged(u'OK', redirect)
        else:
            msg = self.i18n.get(u'User id or password is incorrect')
            return tagged(u'NG', msg)

    def _mk_cookie(self, sessionid):
        m = Morsel()
        m.set('sessionid', sessionid, sessionid)
        m['expires'] = self.session.storage.expire
        m['path'] = '/'
        return m.OutputString()

class Loggedin(Builtin):

    def setup(self, opts):
        self.opts = opts

    def execute(self, input):
        if self.user.loggedin:
            if self.opts['userid']:
                if self.opts['userid'] == self.user.userid:
                    return tagged(u'OK', input)
            else:
                return tagged(u'OK', input)
        return tagged(u'NG', input)


class Logout(Builtin):

    def execute(self, input):
        key = self.session.key
        if self.user.loggedin:
            self.session.clear()
            self.user.clear()
        return {
            'header': {
                'Location': unicode(join(self.env.get('HOST_URL'), input)),
                'Set-Cookie': unicode(self._mk_cookie(key)),
            },
            'status': 302}

    def _mk_cookie(self, sessionid):
        m = Morsel()
        m.set('sessionid', sessionid, sessionid)
        m['expires'] = -1
        m['path'] = '/'
        return m.OutputString()


