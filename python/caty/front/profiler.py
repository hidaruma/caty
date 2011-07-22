#coding:utf-8
from caty.front.console import CatyShell, setup_shell
import hotshot, hotshot.stats

class Profiler(CatyShell):
    def profile(self, f):
        prof = hotshot.Profile("caty.prof")
        m = lambda : self.exec_files([f])
        print u'%sのプロファイルを開始します' % f
        result = prof.runcall(m)
        prof.close()
        stats = hotshot.stats.load("caty.prof")
        #stats.strip_dirs()
        stats.sort_stats('cumulative', 'time', 'calls')
        stats.print_stats('python/caty', 20)

def get_profiler(site, file):
    site, wildcat, debug, args, sites = setup_shell(['-s', site])
    return lambda : Profiler(site, wildcat, debug, sites).profile(file)

def main(args):
    shell, files, script = setup_shell(args, Profiler)
    shell.profile(files[0])
    shell.cleanup()
    return 0
