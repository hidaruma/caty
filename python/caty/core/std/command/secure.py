#coding: utf-8
from caty.core.command import Builtin
from caty.util.path import join
from caty.core.std.command.user import authenticate
from csslib.selector import select, Element
from Cookie import Morsel
import sys
from hashlib import sha1
import random

name = u'secure'
schema = u"""
type TokenProperty = {
    "$_catySecureToken": string,
};

type TokenEmbeded = any;

type TokenCheckResult = @OK T | @NG null;

type Token = string;

type TokenSet = [Token*];

type TargetForm = string | Response;

type LoginForm = {
    "userid": string, 
    "password": string, 
    "succ": string?,
    "fail": string?
};

"""
CATY_SECURE_TOKEN_KEY = '$_CATY_SECURE_TOKEN_KEY' # フォーム入力におけるリクエストトークンのキー
CATY_USER_INFO_KEY = '$_CATY_USER_INFO_KEY' # セッション中にユーザ情報を格納する時のキー

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
            redirect = '/' if not 'succ' in input else input['succ']
            return {
                'header': {
                    'Location': unicode(join(self.env.get('HOST_URL'), redirect)),
                    'Set-Cookie': unicode(self._mk_cookie(session.key)),
                },
                'status': 302}
        else:
            redirect = '/' if not 'fail' in input else input['fail']
            return {
                'header':{
                    'Location': unicode(join(self.env.get('HOST_URL'), redirect)),
                },
                'status': 302
            }

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
            if self.opts.userid:
                if self.opts.userid == self.user.userid:
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


from caty.core.facility import Facility, AccessManager
class RequestToken(Facility):
    def __init__(self, session):
        if session.exists(CATY_SECURE_TOKEN_KEY):
            self.__values = [i for i in session.get(CATY_SECURE_TOKEN_KEY)]
        else:
            self.__values = []

    am = AccessManager()
    @am.update
    def _add(self, token, session):
        assert token not in self.values
        assert token in session.get(CATY_SECURE_TOKEN_KEY)
        self.__values.append(token)

    @property
    def empty(self):
        return len(self.__values) == 0

    def __contains__(self, value):
        return value in self.__values 

    @property
    def values(self):
        return self.__values

    def clone(self):
        return self

class TokenGeneratorMixin(object):
    def _generate_and_set_token(self):
        key = self.session.key
        token = unicode(sha1(reduce(lambda a, b: a + b,
                        [str(random.randint(0, sys.maxint - 1)),
                        str(random.randint(0, sys.maxint - 1)),
                        key])).hexdigest())
        if self.session.exists(CATY_SECURE_TOKEN_KEY):
            self.session.get(CATY_SECURE_TOKEN_KEY).append(token)
        else:
            self.session.put(CATY_SECURE_TOKEN_KEY, [token])
        self.token._add(token, self.session)
        return token

class EmbedToken(Builtin, TokenGeneratorMixin):

    def execute(self, input):
        if isinstance(input, unicode):
            return self._embed(input)
        else:
            body = self._embed(input['body'])
            input['body'] = body
            if 'content-length' in input['header']:
                input['header']['content-length'] = self._recalc_size(input)
            return input
        
    def _embed(self, input):
        forms = select(input, 'form')
        token = self._generate_and_set_token()
        f = None
        for form in forms:
            if 'action' not in form.attrs or form.attrs['action'].strip().startswith('http://'):
                continue
            p = Element('p', [], form)
            hidden = Element('input', [('type', 'hidden'), ('name', '$_catySecureToken'), ('value', token)], p)
            p.add(hidden)
            form.add(p)
            f = form
        return f.to_html() if f else input

    def _recalc_size(self, data):
        e = data['encoding']
        return len(data['body'].encode(e))

class GenerateToken(Builtin, TokenGeneratorMixin):

    def execute(self):
        return self._generate_and_set_token()


from caty.jsontools import tag, tagged, untagged
class CheckToken(Builtin):

    def execute(self, input):
        input, tags = self._detach_tag(input)
        if '$_catySecureToken' not in input:
            return tagged(u'NG', None)
        if self.token.empty:
            return tagged(u'NG', None)
        form_token = input['$_catySecureToken']
        if form_token not in self.token:
            return tagged(u'NG', None)
        # 後続処理で token ファシリティを使うかもしれないので token には手を付けない
        self.session.get(CATY_SECURE_TOKEN_KEY).remove(form_token)
        del input['$_catySecureToken']
        return tagged(u'OK', self._attach_tag(input, tags))

    def _detach_tag(self, input):
        tags = []
        while 1:
            try:
                t = tag(input, explicit=True)
                tags.append(t)
                input = untagged(input)
            except:
                break
        return input, tags

    def _attach_tag(self, obj, tags):
        if tags:
            return self._attach_tag(tagged(tags.pop(-1), obj), tags)
        else:
            return obj


