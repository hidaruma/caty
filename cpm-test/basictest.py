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

ARCHIVER = os.path.join('..', 'tools', 'caty-archiver.py')
INSTALLER = os.path.join('..', 'tools', 'caty-installer.py')
UNINSTALLER = os.path.join('..', 'tools', 'caty-uninstaller.py')

def test01():
    """
    基本的なインストーラーのテスト

    * minimum-catyのアーカイブを作る。
    * minimum-catyをインストールする。
    * minimum-catyをアンインストールする。
    """
    arcfile = 'minimum-caty_0.7.0.zip'
    if os.path.exists(arcfile):
        os.remove(arcfile)
    fset = os.path.join('..', 'products', 'minimum-caty_0.7.0.fset')
    rmtree('tmp-project')
    os.mkdir('tmp-project')
    os.mkdir('tmp-project/backup')
    os.mkdir('tmp-project/features')
    ret = os.system('python %s --origin=.. --fset=%s %s' % (ARCHIVER, fset, arcfile))
    if not ret == 0:
        sys.exit(ret)
    if not os.path.exists(arcfile):
        print 'archiver error'
        sys.exit(1)
    log_dir = os.path.join('tmp-project', 'features')
    bk_dir = os.path.join('tmp-project', 'backup')
    os.system('python %s --project=tmp-project --log-dir=%s --backup-dir=%s %s' % (INSTALLER, log_dir, bk_dir, arcfile))
    if not ret == 0:
        sys.exit(ret)
    
    if not os.path.exists(os.path.join('tmp-project', 'python', 'caty', '__init__.py')):
        print 'installer error'
        sys.exit(1)

    log = glob(os.path.join('tmp-project', 'features', '*.install.log'))[-1]
    os.system('python %s %s --project=tmp-project' % (UNINSTALLER, log))

    if not ret == 0:
        sys.exit(ret)

    if os.path.exists(os.path.join('tmp-project', 'python', 'caty', '__init__.py')):
        print 'uninstaller error'
        sys.exit(1)



if __name__ == '__main__':
    test01()

