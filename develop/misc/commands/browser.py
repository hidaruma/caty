# -*- coding: utf-8 -*- 
# 
#
from caty.command import Command
import webbrowser

class Open(Command):
    def setup(self, url):
        self.url = url

    def execute(self):
        webbrowser.open (self.url)
        return None

