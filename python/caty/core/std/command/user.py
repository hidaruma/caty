#coding: utf-8
from caty.core.command import Builtin
from caty.core.facility import Facility, AccessManager
from caty.util.path import join
from caty.jsontools import tagged
from Cookie import Morsel
from caty.core.std.command.authutil import CATY_USER_INFO_KEY

name = 'user'

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
        user = self.session.get(CATY_USER_INFO_KEY)
        return user

class UpdateInfo(Builtin):

    def execute(self):
        user = self.session.get(CATY_USER_INFO_KEY)
        info = self.storage('user').select1({'userid':user['userid']})
        


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
            session = self.session.storage.create().create(u'uses')
            self.session = session
            del user['password']
            session.put(CATY_USER_INFO_KEY, user)
            redirect_path = u'/' if not 'succ' in input else input['succ']
            redirect = {
            'header': {
                'Location': unicode(join(self.env.get('HOST_URL'), redirect_path)),
            },
            'status': 302}
            return tagged(u'OK', redirect)
        else:
            msg = self.i18n.get(u'User id or password is incorrect')
            return tagged(u'NG', msg)

class Loggedin(Builtin):

    def setup(self, opts):
        self.opts = opts

    def execute(self, input):
        user = self.session.get(CATY_USER_INFO_KEY)
        if user:
            if self.opts['userid']:
                if self.opts['userid'] == user['userid']:
                    return tagged(u'OK', input)
            else:
                return tagged(u'OK', input)
        return tagged(u'NG', input)


class Logout(Builtin):

    def execute(self, input):
        key = self.session.id
        user = self.session.get(CATY_USER_INFO_KEY)
        if user:
            self.session.clear()
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


