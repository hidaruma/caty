from caty.command import *
from rauth.service import OAuth1Service

class TwitterClient(object):
    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret, callback):
        self.auth = OAuth1Service(
            name='twitter',
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            request_token_url='https://api.twitter.com/oauth/request_token',
            access_token_url='https://api.twitter.com/oauth/access_token',
            authorize_url='https://api.twitter.com/oauth/authorize',
            header_auth=True)
        self.access_token = {
            'access_token': access_token,
            'access_token_secret': access_token_secret}
        self.callback = callback

    def get_authorize_url_and_token(self):
        request_token, request_token_secret = self.auth.get_request_token('GET', oauth_callback=self.callback)
        return unicode(self.auth.get_authorize_url(request_token)), request_token, request_token_secret


    def get_auth_info(self, session, oauth_token, oauth_verifier):
        if not (session.get('request_token') and oauth_token and oauth_verifier):
            return
        response = self.auth.get_access_token(
            'POST',
            request_token=session.get('request_token'),
            request_token_secret=session.get('request_token_secret'),
            data={'oauth_verifier': oauth_verifier}
        )
        data = response.content
        session.pop('request_token_secret', None)
        session.pop('request_token', None)
        session['access_token'] = data['oauth_token']
        session['access_token_secret'] = data['oauth_token_secret']
        account = self.auth.get('https://api.twitter.com/1/account/settings.json', access_token=session.get('access_token'), access_token_secret=session.get('access_token_secret')).content
        return account

class InitAPI(Command):
    def execute(self, oauth_info):
        self.memory[oauth_info['appName']] = TwitterClient(oauth_info['consumerKey'], oauth_info['consumerSecret'], oauth_info['accessToken'], oauth_info['accessTokenSecret'], oauth_info['callback'])

class Redirect(Command):
    def setup(self, app_name):
        self.app_name = app_name

    def execute(self):
        tc = self.memory[self.app_name]
        url, token, secret = tc.get_authorize_url_and_token()
        self.session[self.app_name] =  {
            'request_token': token,
            'request_secret': secret
        }
        return unicode(url)

class LoginCallBack(Command):
    def setup(self, opts, app_name):
        self.oauth_token = opts['oauth_token']
        self.oauth_verifier = opts['oauth_verifier']
        self.app_name = app_name

    def execute(self):
        tc = self.memory[self.app_name]
        session = self.session.get(self.app_name, {})
        account = tc.get_auth_info(session, self.oauth_token, self.oauth_verifier)
        print account
        session['$user_info'] = account
