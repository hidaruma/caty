# -*- coding: utf-8 -*- 
# 
#
from __future__ import with_statement
from caty.command import Command
import webbrowser


class Open(Command):
    def setup(self, url):
        self.url = url

    def execute(self):
        webbrowser.open (self.url, new=2, autoraise=1)
        return None

import os
import tempfile


class Show(Command):
    def setup(self, opts):
        self.ext = opts.get('ext', 'html')

    def execute(self, input):
        dir_name = tempfile.mkdtemp()
        ext = self.ext[1:] if len(self.ext) and self.ext[0] == '.' else self.ext
        temp_name = os.path.join(dir_name, 'caty_tmp.' + ext)
        
        with open(temp_name, 'w') as temp:
            temp.write(input)
            temp.flush()
        file_url = "file:///" + temp_name
        webbrowser.open (file_url)
        return None

