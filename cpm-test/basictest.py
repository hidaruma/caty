#coding: utf-8

import sys
import os
from glob import glob
os.chdir('cpm-test')
def rmtree(top):
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    if os.path.exists(top):
        os.rmdir(top)

def call(line):
    print '[exec]', line
    return os.system(line) % 256

ARCHIVER = os.path.join('..', 'tools', 'caty-archiver.py')
INSTALLER = os.path.join('..', 'tools', 'caty-installer.py')
UNINSTALLER = os.path.join('..', 'tools', 'caty-uninstaller.py')

def test01_caty_core():
    """
    基本的なインストーラーのテスト

    * minimum-catyのアーカイブを作る。
    * minimum-catyをインストールする。
    * minimum-catyをアンインストールする。
    """
    arcfile = 'minimum-caty_0.7.0.zip'
    if os.path.exists(arcfile):
        os.remove(arcfile)
    fset = os.path.join('..', 'products', 'caty-core', 'files.fset')
    rmtree('tmp-project')
    os.mkdir('tmp-project')
    os.mkdir('tmp-project/backup')
    os.mkdir('tmp-project/features')
    ret = call('python %s --origin=.. --fset=%s %s' % (ARCHIVER, fset, arcfile))
    if not ret == 0:
        sys.exit(ret)
    if not os.path.exists(arcfile):
        print 'archiver error'
        sys.exit(1)
    log_dir = os.path.join('tmp-project', 'features')
    bk_dir = os.path.join('tmp-project', 'backup')
    ret = call('python %s --project=tmp-project --log-dir=%s --backup-dir=%s %s' % (INSTALLER, log_dir, bk_dir, arcfile))
    if not ret == 0:
        sys.exit(ret)
    
    if not os.path.exists(os.path.join('tmp-project', 'python', 'caty', '__init__.py')):
        print 'installer error'
        sys.exit(1)

    log = glob(os.path.join('tmp-project', 'features', 'minimum-caty_*.install.log'))[-1]
    ret = call('python %s %s --project=tmp-project' % (UNINSTALLER, log))

    if not ret == 0:
        sys.exit(ret)

    if os.path.exists(os.path.join('tmp-project', 'python', 'caty', '__init__.py')):
        print 'uninstaller error'
        sys.exit(1)

def test02_app():
    arcfile = 'wiki_0.0.0.zip'
    if os.path.exists(arcfile):
        os.remove(arcfile)
    fset = os.path.join('..', 'products', 'std-app.fset')
    rmtree(os.path.join('tmp-project', 'extra.group'))
    os.mkdir(os.path.join('tmp-project', 'extra.group'))
    os.mkdir(os.path.join('tmp-project', 'extra.group', 'wiki'))
    ret = call('python %s --project=.. --origin=wiki --fset=%s %s' % (ARCHIVER, fset, arcfile))
    if not ret == 0:
        sys.exit(ret)
    if not os.path.exists(arcfile):
        print 'archiver error'
        sys.exit(1)
    log_dir = os.path.join('tmp-project', 'features')
    bk_dir = os.path.join('tmp-project', 'backup')
    ret = call('python %s --project=tmp-project --dest=wiki --log-dir=%s --backup-dir=%s %s' % (INSTALLER, log_dir, bk_dir, arcfile))
    if not ret == 0:
        sys.exit(ret)
    
    if not os.path.exists(os.path.join('tmp-project', 'extra.group', 'wiki', 'app-manifest.xjson')):
        print 'installer error'
        sys.exit(1)

    log = glob(os.path.join('tmp-project', 'features', 'wiki_*.install.log'))[-1]
    ret = call('python %s %s --project=tmp-project' % (UNINSTALLER, log))

    if not ret == 0:
        sys.exit(ret)

    if os.path.exists(os.path.join('tmp-project', 'extra.group', 'wiki', 'app-manifest.xjson')):
        print 'uninstaller error'
        sys.exit(1)

def test03_modify():
    arcfile = 'wiki_0.0.0.zip'
    if os.path.exists(arcfile):
        os.remove(arcfile)
    fset = os.path.join('..', 'products', 'std-app.fset')
    rmtree(os.path.join('tmp-project', 'extra.group'))
    os.mkdir(os.path.join('tmp-project', 'extra.group'))
    os.mkdir(os.path.join('tmp-project', 'extra.group', 'wiki'))
    ret = call('python %s --project=.. --origin=wiki --fset=%s %s' % (ARCHIVER, fset, arcfile))
    if not ret == 0:
        sys.exit(ret)
    if not os.path.exists(arcfile):
        print 'archiver error'
        sys.exit(1)
    log_dir = os.path.join('tmp-project', 'features')
    bk_dir = os.path.join('tmp-project', 'backup')
    ret = call('python %s --project=tmp-project --dest=wiki --log-dir=%s --backup-dir=%s %s' % (INSTALLER, log_dir, bk_dir, arcfile))
    if not ret == 0:
        sys.exit(ret)
    
    if not os.path.exists(os.path.join('tmp-project', 'extra.group', 'wiki', 'app-manifest.xjson')):
        print 'installer error'
        sys.exit(1)


    os.unlink(os.path.join('tmp-project', 'extra.group', 'wiki', 'app-manifest.xjson'))
    open(os.path.join('tmp-project', 'extra.group', 'wiki', 'actions', 'wiki.cara'), 'wb').write('a')

    log = glob(os.path.join('tmp-project', 'features', 'wiki_*.install.log'))[-1]
    ret = call('python %s %s --project=tmp-project' % (UNINSTALLER, log))
    if not ret == 0:
        sys.exit(ret)

    if os.path.exists(os.path.join('tmp-project', 'extra.group', 'wiki', 'app-manifest.xjson')):
        print 'uninstaller error'
        sys.exit(1)



if __name__ == '__main__':
    test01_caty_core()
    test02_app()
    test03_modify()

