import sys
import subprocess

def check_pip():
    try:
        p = subprocess.Popen(['pip'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        return True
    except:
        return False

def main() :
    major = sys.version_info[0]
    minor = sys.version_info[1]
    if major != 2 or minor < 5 :
        print "Sorry, Caty needs '2.5 <= Python version < 3.0'"
        sys.exit(1)
    else:
        print "OK, right Python version for Caty, \n%s." % sys.version
        print ""
        if check_pip():
            print "OK, pip is installed."
            sys.exit(0)            
        else:
            print "Sorry, pip is NOT installed."
            sys.exit(1)

if __name__ == "__main__":
    main()
