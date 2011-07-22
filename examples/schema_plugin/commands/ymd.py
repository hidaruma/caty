# -*- coding: utf-8 -*-
import re
class YMDValidator(object):
    def validate(self, value):
        p = re.compile('[0-9]{4}-[0-9]{2}-[0-9]{2}')
        if not p.match(value):
            return u'譁�ｭ怜�縺刑YYY-MM-DD縺ｮ繝代ち繝ｼ繝ｳ縺ｧ縺ｯ縺ゅｊ縺ｾ縺帙ｓ: %s' % value

