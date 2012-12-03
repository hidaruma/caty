#!/bin/sh
# -*- coding: utf-8 -*-

DEFAULT_CATY_HOME=../caty


function find_caty_home { # => caty_home
    if [ -n "$CATY_HOME" ]; then
	caty_home=$CATY_HOME
    elif [ -d $DEFAULT_CATY_HOME ]; then
	caty_home=$DEFAULT_CATY_HOME
    else
	caty_home=.
    fi
}

function do_list {
    case "$1" in
     project|prj)
       SUBEXT=caty-prj
       ;;
     global|glb)
       SUBEXT=caty-glb
       ;;
     application|app)
       SUBEXT=caty-app
       ;;
     *)
       echo "list requires (project|prj|global|glb|application|app)"
       exit 1
       ;;
    esac

    list=`/bin/ls $caty_home/dists/*.$SUBEXT.zip 2>/dev/null`
    for f in $list; do
	basename $f .$SUBEXT.zip
    done
}

function check_dist {
    target=$1
    dist=$2
    case "$target" in
     project|prj)
       SUBEXT=caty-prj
       ;;
     global|glb)
       SUBEXT=caty-glb
       ;;
     application|app)
       SUBEXT=caty-app
       ;;
     *)
       echo "*** ERROR ***"
       exit 1
       ;;
    esac

    if [ -f $caty_home/dists/$dist.$SUBEXT.zip ]; then
	return 0
    else
	return 1
    fi
}
    

function do_install { # dist_package, project_dir => 
    if [ -z "$2" ]; then
	echo Usage: $0 install dist_package project_dir [target]
	exit 1
    fi

    target=$1
    dist_package=$2
    project_dir=$3


    if [ -z "$target" ]; then
	target=project
    fi

    case "$target" in
     project|prj)
       SUBEXT=caty-prj
       dest=project
       ;;
     global|glb)
       SUBEXT=caty-glb
       dest=global
       ;;
     *)
       SUBEXT=caty-app
       dest=$target
       ;;
     *)
       echo "*** ERROR ***"
       exit 1
       ;;
    esac

    archive=$caty_home/dists/$dist_package.$SUBEXT.zip
    if [ ! -f $archive ]; then
	echo "Cannot find archive: $archive"
	exit 1
    fi

    if [ ! -d $project_dir ]; then
	echo "Cannot find projct: $project_dir"
	echo "creat it"
	mkdir $project_dir
	if [ ! -d $project_dir ]; then
	    echo "Failed to create $new_projct"
	    exit 1
	fi
    fi

    if [ ! -d $project_dir/features/ ]; then
	mkdir $project_dir/features/
    fi
    if [ ! -d $project_dir/backup/ ]; then
	mkdir $project_dir/backup/
    fi
    if [ ! -d $project_dir/global/ ]; then
	mkdir $project_dir/global/
    fi

    python $caty_home/tools/caty-installer.py --compare=digest \
	--project=$project_dir \
        --log-dir=$project_dir/features/ --backup-dir=$project_dir/backup/ \
	--dest=$dest \
	$archive
}

function cmd_error {
    echo Usage: $0 command args ...
    echo command: list, install
    exit 1
}

# ==== main ====

caty_home=""
find_caty_home
#echo "caty_home=$caty_home"

if [ ! -f $caty_home/tools/caty-installer.py ]; then
    echo "cannot find installer"
    exit 1
fi

if [ -z "$1" ]; then
    echo Usage: "$0 (project|prj|global|glb|application|app) ARG ..."
    exit 1
fi

target=$1
if [ -z "$2" ]; then
    do_list $target
    echo ""
    echo Usage: "$0 $target DIST_PACKAGE PROJECT_DIR"
    exit 1
fi

dist=$2
if [ -z "$3" ]; then
    check_dist $target $dist
    if [ $? == 0 ]; then
	echo Usage: "$0 $target $dist PROJECT_DIR"
    else
	echo "dist-package '$dist' NOT found"
    fi
    exit 1
fi

project_dir=$3
do_install $target $dist $project_dir


