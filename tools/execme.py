import sys
def main() :
    major = sys.version_info[0]
    minor = sys.version_info[1]
    if major != 2 or minor < 5 :
        print "Sorry, Caty needs '2.5 <= Python version < 3.0'"
        sys.exit(1)
    else:
        print "OK, right Python version for Caty, \n%s." % sys.version
        sys.exit(0)

if __name__ == "__main__":
    main()
