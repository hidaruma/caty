#!/bin/sh
# -*- coding: utf-8 -*-
# cdt -- Caty Deploy Tool

DEFAULT_CATY_HOME=../caty
function find_caty_home { # () => caty_home
    if [ -n "$CATY_HOME" ]; then
	caty_home=$CATY_HOME
    elif [ -d $DEFAULT_CATY_HOME ]; then
	caty_home=$DEFAULT_CATY_HOME
    else
	caty_home=.
    fi
}
find_caty_home
source $caty_home/tools/functions.sh

# You can use functions in $caty_home/tools/functions.sh

# ==== main ====


# アプリケーションフィーチャのインストールが出来ない??



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
#	basename $f .$SUBEXT.zip
	echo $f
    done
}

function check_dist {
    dist_file=$1

    if [ -f $dist_file ]; then
	return 0
    else
	return 1
    fi
}
    

function do_install { # dist_file, project_dir => 
    if [ -z "$2" ]; then
	echo Usage: $0 install dist_file project_dir [target]
	exit 1
    fi

    target=$1
    dist_file=$2
    project_dir=$3
    dest=$4

    echo "DEBUG: target=$target, dist_file=$dist_file, project_dir=$project_dir, dest=$dest"


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
       dest=$dest
       ;;
     *)
       echo "*** ERROR ***"
       exit 1
       ;;
    esac

#    archive=$caty_home/dists/$dist_file.$SUBEXT.zip
    archive=$dist_file
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

    echo "python $caty_home/tools/caty-installer.py --compare=digest"
    echo	"--project=$project_dir "
    echo        "--log-dir=$project_dir/features/ --backup-dir=$project_dir/backup/ "
    echo	"--dest=$dest "
    echo	"$archive"


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

if [ ! -f $caty_home/tools/caty-installer.py ]; then
    echo "cannot find installer"
    exit 1
fi

if [ -z "$1" ]; then
    echo "** Usage: $0 targetType distPackageFile projectDir destination"
    echo ""
    echo "** targetType:"
    echo "project | prj"
    echo "global | glb"
    echo "application | app"

    exit 1
fi
target=$1

if [ -z "$2" ]; then
    echo "** Usage: $0 targetType distPackageFile projectDir destination"
    echo ""
    echo "** distPackageFile:"
    do_list $target

    exit 1
fi
dist_file=$2


if [ -z "$3" ]; then
    check_dist $dist_file
    if [ $? == 0 ]; then
	echo "** Usage: $0 targetType distPackageFile projectDir destination"
    else
	echo "distPackageFile '$dist_file' NOT found"
    fi
    exit 1
fi
project_dir=$3

if [ -z "$4" ]; then
    echo "** Usage: $0 targetType distPackageFile projectDir destination"
    exit 1
else
    dest=$4
fi

do_install $target $dist_file $project_dir $dest


