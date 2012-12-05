#coding: utf-8
from __future__ import with_statement
from caty.core.command import Builtin
from caty.core.exception import *
import caty.jsontools as json

import smtplib
from email.MIMEText import MIMEText

class Send(Builtin):
    def setup(self, opts, *addrs):
        self._to_addrs = addrs
        self._from_addr = opts['from']
        if ':' in opts['server']:
            self._host, self._port = opts['server'].rsplit(':', 1)
        else:
            self._host = opts['server']
            self._port = u'25'

    def execute(self, message):
        enc = self.env.get('APP_ENCODING')
        msg = MIMEText(message['body'].encode(enc))
        to_addrs = list(self._to_addrs)
        for k, v in message['header'].items():
            if k == 'body': 
                continue
            else:
                if not self._to_addrs and k.lower() == 'to':
                    to_addrs.append(v.encode(enc))
                msg[k] = v.encode(enc)
        sender = smtplib.SMTP(self._host, int(self._port))
        sender.sendmail(self._from_addr.encode(enc), to_addrs, msg.as_string())
        sender.close()

