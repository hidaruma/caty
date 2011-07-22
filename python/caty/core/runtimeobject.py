#coding: utf-8
u"""
Caty実行時にシステムからグローバルにアクセスされうるシングルトンオブジェクト。
"""
from caty.core.i18n import I18nMessage
i18n=I18nMessage({})
PID_FILE = 'server.pid'
