# -*- coding: utf-8 -*- 
from caty.command import Command

VAL = 123

# 001 引数なし、オプションなし
class T001(Command):
    def execute(self):
        return VAL

# 002 int引数ありかも、オプションなし
class T002(Command):
    def setup(self, arg=None):
        self.arg = arg

    def execute(self):
        if self.arg != None:
            return self.arg
        else:
            return VAL

# 003 int引数あり、オプションなし
class T003(Command):
    def setup(self, arg):
        self.arg = arg

    def execute(self):
        if self.arg != None:
            return self.arg
        else:
            return VAL # NOT REACHED

# 004 int, int? 引数、オプションなし */
class T004(Command):
    def setup(self, arg1, arg2=None):
        self.arg1 = arg1
        self.arg2 = arg2

    def execute(self):
        if self.arg2 != None:
            return self.arg2
        elif self.arg1 != None:
            return self.arg1
        else:
            return VAL # NOT REACHED

# 005 int, int?, int? 引数、オプションなし
class T005(Command):
    def setup(self, arg1, arg2=None, arg3 = None):
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3

    def execute(self):
        if self.arg3 != None:
            return self.arg3
        elif self.arg2 != None:
            return self.arg2
        elif self.arg1 != None:
            return self.arg1
        else:
            return VAL # NOT REACHED

# 006 int?, int? 引数、オプションなし
class T006(Command):
    def setup(self, arg1=None, arg2=None):
        self.arg1 = arg1
        self.arg2 = arg2

    def execute(self):
        if self.arg2 != None:
            return self.arg2
        elif self.arg1 != None:
            return self.arg1
        else:
            return VAL


# 007 int, int* 引数、オプションなし
# 引数の総和
class T007(Command):
    def setup(self, arg1, *rest_args):
        self.arg1 = arg1
        self.rest_sum = sum(rest_args)

    def execute(self):
        return self.arg1 + self.rest_sum

# 以下、番号は20から

# 20 引数なし、intオプションoptありかも
class T020(Command):
    def setup(self, opts):
        self.n = opts.opt
    
    def execute(self):
        if self.n != None:
            return self.n
        else:
            return VAL

# 021 int引数あり、intオプションoptありかも # オプション優先
class T021(Command):
    def setup(self, opts, arg):
        self.n = opts.opt
        self.m = arg
    
    def execute(self):
        if self.n != None:
            return self.n # オプション優先
        elif self.m != None:
            return self.m
        else:
            return VAL

# 022 int引数ありかも、intオプションoptありかも # オプション優先
class T022(Command):
    def setup(self, opts, arg):
        self.n = opts.opt
        self.m = arg
    
    def execute(self):
        if self.n != None:
            return self.n # オプション優先
        elif self.m != None:
            return self.m
        else:
            return VAL

# 023 int引数あり、intオプションoptあり 総和
class T023(Command):
    def setup(self, opts, arg):
        self.n = opts.opt
        self.m = arg
    
    def execute(self):
        return self.n + self.m

# 024 int引数ありかも、intオプションoptあり # 引数優先
class T024(Command):
    def setup(self, opts, arg):
        self.n = opts.opt
        self.m = arg
    
    def execute(self):
        if self.m != None:
            return self.m # 引数優先
        elif self.n != None:
            return self.n
        else:
            return VAL

