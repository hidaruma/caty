#!python
# -*- coding: utf-8 -*-
#
#= Catyのプロジェクトの作成と更新
import os
from shutil import copy2

try:
    import json
except ImportError:
    import simplejson as json

class ImplBug(Exception):
    def __init__(self, message):
        super(ImplBug, self).__init__(message)

class PathNotSpecified(Exception):
    def __init__(self, message):
        super(PathNotSpecified, self).__init__(message)

#== 一般的な補助関数

_DEBUG = False;

def debug_print(message):
    if _DEBUG:
        print "** " + message

#== ファイル操作のライブラリ的関数群

def load_json(fname, encoding = 'utf-8'):
    with open(fname) as f:
        return json.load(f, encoding)

def cant_copy(src, dst, why):
    print u"cannot copy '%s' to '%s': %s" % (src, dst, unicode(why))

def do_copy(srcname, dstname, quiet, no_exec):
    if not quiet:
        print u"copy file: %s --> %s" % (srcname, dstname)        
    if no_exec:
        return 1 # やったつもり
    else:
        try:
            copy2(srcname, dstname)
            return 1
        except (IOError, os.error), why:
            cant_copy(srcname, dstname, why)
            return 0

def dir_exists(path):
    return os.path.exists(path) and os.path.isdir(path)

def file_exists(path):
    return os.path.exists(path) and os.path.isfile(path)

def _update_file(srcname, dstname, quiet, no_exec):
    cnt = 0
    if os.path.exists(dstname):
        srctime = long(os.path.getmtime(srcname) * 100)
        dsttime = long(os.path.getmtime(dstname) * 100)
        if srctime > dsttime:
            cnt += do_copy(srcname, dstname, quiet, no_exec)
        else:
            return cnt
    else:
        cnt += do_copy(srcname, dstname, quiet, no_exec)
    return cnt

def update_thing(src, dst, quiet, no_exec):
    # dstのチェック
    if os.path.exists(dst):
        if os.path.isdir(dst):
            pass
        else:
            print "%s is not a directory" % dst
            return 0
    else:
        if not no_exec:
            os.makedirs(dst)

    # srcのチェックと実行
    if os.path.exists(src):
        if os.path.isfile(src):
            dstname = os.path.join(dst, src)
            return _update_file(src, dstname, quiet, no_exec)
        if os.path.isdir(src):
            if not quiet:
                debug_print(u"check dir: %s/ --> %s/" % (src, dst))
            cnt = 0;
            for name in os.listdir(src):
                srcname = os.path.join(src, name)
                dstname = os.path.join(dst, name)
                if os.path.isdir(srcname):
                    cnt += update_thing(srcname, dstname, quiet, no_exec)
                else:
                    cnt += _update_file(srcname, dstname, quiet, no_exec)
            return cnt
        else:
            print "%s is not a file/directory in %s" % (src, os.getcwd())
            return 0
    else:
        print "%s not exist" % src
        return 0


import filecmp

SEP = os.path.sep;

def do_right_only(left, right):
    if left == "":
        left = "." # work-around
    if not dir_exists(left) or not dir_exists(right):
        return
    dcmp = filecmp.dircmp(left, right)
    _do_right_only(left, right, dcmp)

def _do_right_only(left, right, dcmp):
    debug_print("compare with '" + left + "' and '" + right + "'")
    def make_path(parent, name):
        path = os.path.join(parent, name)
        if os.path.isdir(path):
            return path + os.path.sep
        else:
            return path
        
    path_list = map(lambda name: make_path(right, name), dcmp.right_only)
    for p in path_list:
        print p
    for k in dcmp.subdirs.keys():
        new_left  = os.path.join(left, k)
        new_right = os.path.join(right, k)
        new_dcmp  = dcmp.subdirs.get(k)
        _do_right_only(new_left, new_right, new_dcmp)


#== ProjectクラスとConfigクラス

import datetime

class Project(object):
    import datetime

    LOG_FILENAME = '.caty_project.log'
    def __init__(self, config_path, name, data):
        self.config_path = config_path
        self.name = name
        self.data = data
        

    @property
    def path(self):
        return self.data.get("path")
    @property
    def description(self):
        return self.data.get("description")
    @property
    def disabled(self):
        return self.data.get("disabled")

    def stuffs_to_handle(self, when, which):
        if when == 'create':
            key = 'createStuff'
        elif when == 'update':
            key = 'updateStuff'
        elif when == 'renew':
            key = 'createStuff'
        elif when == 'compare':
            key = 'compareStuff'
        else:
            raise ImplBug('case mismatch')
        stuff = self.data.get(key)
        r = None
        if stuff:
            r = stuff.get(which)
        return r if r else []

    def files_to_handle(self, when):
        return self.stuffs_to_handle(when, "files")

    def dirs_to_handle(self, when):
        return self.stuffs_to_handle(when, "dirs")

    def project_exists(self, path=None):
        path = path if path else self.path
        if not path:
            raise PathNotSpecifed("")
        return 

    def log(self, task, dir, cnt, console=False):
        abspath = os.path.abspath(".") # ホームディレクトリーがカレントと仮定
        now = (datetime.datetime.now().isoformat())[0:19]
        message = '|' + now + '|' + task + '|' + self.name + '|' + self.config_path + '|' \
            + abspath + '|' + str(cnt) + '|\n'
        if console:
            print '\n' + message
        else:
            f = open(os.path.join(dir, self.LOG_FILENAME), 'a')
            f.write(message)
            f.close()

    def do_task(self, task, opts, path=None):
        debug_print("task: " + task)
        if self.disabled: 
            print "project %s is disabled" % self.name
            return
        path = path if path else self.path
        if not path: 
            print "path not specified for %s" % self.name
            return
        is_proj = file_exists(os.path.join(path, self.LOG_FILENAME))


        if task == 'update' or task == 'renew':
            if not is_proj:
                print "not a project"
                return
        elif task == 'create':
            if is_proj:
                print "already a project %s" % path
                return
        elif task == 'compare' or task == 'showlog':
            pass
        else:
            raise ImplBug('unknown task')

        files = self.files_to_handle(task)
        dirs = self.dirs_to_handle(task)
        quiet = opts.get('quiet')
        no_exec = opts.get('no_exec')
        cnt = 0
        #
        # ここから下が汚い
        #
        if task == 'compare':
            for dir in dirs:
                left = dir
                right = os.path.join(path, dir)
                do_right_only(left, right)
            return 
            
        if task == 'showlog':
            log_file = os.path.join(path, self.LOG_FILENAME)
            f = open(log_file)
            s = f.read()
            print s
            f.close()
            return 
            
        for srcf in files:
            cnt += update_thing(srcf, path, quiet, no_exec)
        for srcd in dirs:
            cnt += update_thing(srcd, os.path.join(path, srcd), quiet, no_exec)
        self.log(task, path, cnt, "console")
        if no_exec:
            pass
        else:
            self.log(task, path, cnt)

    def update(self, opts, path=None):
        self.do_task('update', opts, path)

    def create(self, opts, path=None):
        self.do_task('create', opts, path)

    def renew(self, opts, path=None):
        self.do_task('renew', opts, path)

    def compare(self, opts, path):
        debug_print("compare arg:path:" + str(path))
        self.do_task('compare', opts, path)

    def showlog(self, opts, path):
        debug_print("task: " + "showlog")
        if self.disabled: 
            print "project %s is disabled" % self.name
            return
        path = path if path else self.path
        if not path: 
            print "path not specified for %s" % self.name
            return
        is_proj = file_exists(os.path.join(path, self.LOG_FILENAME))


        log_file = os.path.join(path, self.LOG_FILENAME)
        f = open(log_file)
        s = f.read()
        print s
        f.close()



class Config(object):
    def __init__(self, path, data):
        self.path = path
        self.data = data

    def __iter__(self):
        self.keys = self.data.keys()
        self.index = 0;
        return self

    def next(self):
        if self.index >= len(self.keys):
            raise StopIteration
        name = self.keys[self.index]
        proj = Project(self.path, name, self.data[name])
        self.index += 1
        return proj

    def get(self, name):
        proj_data = self.data.get(name)
        if proj_data:
            return Project(self.path, name, proj_data)
        else:
            return None

    # subcommands (tasks)
    def list(self, opts, project_name, target_path):
        for proj in self:
            disabled = " (disabled)" if proj.disabled else ""
            print u"%s\t%s%s" % (proj.name, proj.description, disabled)

    def do_task(self, task, opts, project_name, target_path):
        proj = self.get(project_name)
        if not proj:
            print "project %s not found" % project_name
            return
        getattr(proj, task)(opts, target_path)

    def create(self, opts, project_name, target_path):
        self.do_task("create", opts, project_name, target_path)
        
    def update(self, opts, project_name, target_path):
        self.do_task("update", opts, project_name, target_path)

    def renew(self, opts,  project_name, target_path):
        self.do_task("renew", opts, project_name, target_path)

    def compare(self, opts,  project_name, target_path):
        debug_print("compare arg:target_path:" + str(target_path))
        self.do_task("compare", opts, project_name, target_path)

    def showlog(self, opts,  project_name, target_path):
        self.do_task("showlog", opts, project_name, target_path)

#== メイン

import sys

def location_specified(path):
    if path.startswith('/'):
        return True
    if path.startswith(('./', '.\\', '../', '..\\')):
        return True
    if sys.platform.startswith('win'):
        if path.startswith('\\') or (len(path) >= 2 and path[1] == ':'):
            return True
    return False

config_sample = """WARNING! JSON file cannot contain comments (/* ... */).
Those comments are used only for explanation.

{
 /* property name represents a project */
 "sample" : {
   "description" : "short description", /* optional */
   "disabled" : false, /* optional */
   "path" : "path/to/project", /* optional, you can specify via commandline */
   "createStuff" : { 
       /* files and directories 
        * that shuold be copyed when create the project 
        */
       "files" : ["file1", "file2"],
       "dirs" : ["dir1", "dir2", "dir2"]
   },

   "updateStuff" : {
     /* files and directories 
      * that shuold be copyed when update the project 
      */
     "files" : ["file1"],
     "dirs"  : ["dir1", "dir2"]
   }
 },

 /* ...
  * ...
  */
}"""

from optparse import OptionParser

def main():
    usage = u"""usage: %prog [options] subcommand [project_name [target_path]]
Subcommands:
  list                  print projects in cofiguration
  create                create new project
  update                update existing project
  renew                 renew existing project
  compare               print files exist only within project
  showlog               show log"""

    version = "%prog 0.1.0"
    parser = OptionParser(usage=usage, version=version)
    parser.add_option("--show-config-sample", 
                      action="store_true", dest="show_config_sample",
                      help="show configuration sample and exit")
    parser.add_option("--home", dest="home",
                      help="Caty home (installed directory)")
    parser.add_option("--origin", dest="origin",
                      help="same as --home")
    parser.add_option("--config", dest="config",
                      help="pojects configuration file (json format)")
    parser.add_option("-q", "--quiet",
                      action="store_true", dest="quiet",
                      help="suppress messages")
    parser.add_option("-n", "--no-exec",
                      action="store_true", dest="no_exec",
                      help="do not execute, message only")
    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug",
                      help="print debug message")

    (options, args) = parser.parse_args()
    if options.show_config_sample:
        print config_sample
        exit(0)
    if len(args) < 1:
        parser.print_help()
        exit(0)
    global _DEBUG
    _DEBUG = options.debug
    subcommand   = args[0]
    project_name = args[1] if len(args) >= 2 else None
    target_path  = os.path.abspath(args[2]) if len(args) >= 3 else None
    
    opts = {'quiet' : options.quiet, 'no_exec' : options.no_exec}    

    home = os.getenv('CATY_HOME') 
    debug_print(u"CATY_HOME: " + unicode(home))
    home = home if home else '.'
    home = options.home if options.home else home
    home = options.origin if options.origin else home
    home = os.path.abspath(home)

    config_file = options.config if options.config else 'projects.json'
    if location_specified(config_file):
        pass
    else:
        config_file = os.path.join(home, config_file)
    config_file = os.path.abspath(config_file)

    debug_print("home / origin: " + home)
    debug_print("config file: " + config_file)

    config = Config(config_file, load_json(config_file))

#  File "c:\Installed\Python26\lib\json\decoder.py", line 198, in JSONObject
#    raise ValueError(errmsg("Expecting property name", s, end - 1))
# ValueError: Expecting property name: line 59 column 4 (char 1155)


    os.chdir(home)

    # dispatch

    for task, require_name in (
        ('list',    False),
        ('create',  True),
        ('update',  True),
        ('renew',   True),
        ('compare', True),
        ('showlog', True)):

        if subcommand == task:
            if require_name and not project_name:
                print "%s subcommand requires project name" % subcommand
                exit(1)
            debug_print("target_path:" + unicode(target_path))
            getattr(config, task)(opts, project_name, target_path)
            exit(0)
    print 'unknown subcommand %s' % subcommand


if __name__ == "__main__":
    main()
