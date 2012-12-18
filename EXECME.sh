#!/bin/sh

python -c "print 'hello'" > _pythonCheck_.tmp 

if test -s _pythonCheck_.tmp; then
    rm _pythonCheck_.tmp

    python tools/execme.py
    if [ $? -ne 0 ]; then
	exit 1 
    fi
    sh tools/setup-readme.sh -q
    echo ""
    echo "Invoking Caty server ..."
    echo "Please Access http://localhost:8000/readme/"
    echo -n "HIT ENTER (RETURN) KEY "
    read Any
    echo ""
    python ./stdcaty.py server
	
else
    rm _pythonCheck_.tmp 

    echo ""
    echo "python command not found."
    echo "Please install the Python version 2.5, 2.6 or 2.7"
    echo ""
fi
