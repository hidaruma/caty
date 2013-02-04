#!/bin/sh
# -*- coding: utf-8 -*-
# cdt -- Caty Deploy Tool

DEFAULT_CATY_HOME=../caty
function find_caty_home { # () => $caty_home
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

# You can use the functions in $caty_home/tools/functions.sh

# ==== script body ====

# ?? アプリケーションフィーチャのインストールが出来ない??


## 配布パッケージ種別ごとに、すべての配布パッケージをリスとする
function list_dists { # (dest_type) => *STDOUT*
    local dest_type=$1
    case "$dest_type" in
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
       error_exit "this function requires (project|prj|global|glb|application|app)"
       ;;
    esac

    list=`/bin/ls $caty_home/dists/*.$SUBEXT.zip 2>/dev/null`
    for f in $list; do
	echo $f
    done
}

function exists_dist_file { # (dist_file) => *STATUS*
    dist_file=$1

    if [ -f $dist_file ]; then
	return 0
    else
	return 1
    fi
}
    
function do_install { # (dest_type, dist_file, project_dir, dest) => 
    local dest_type=$1
    local dist_file=$2
    local project_dir=$3
    local dest=$4

    debug "dest_type=$dest_type, dist_file=$dist_file, project_dir=$project_dir, dest=$dest"

    if [ ! -f $dist_file ]; then
	error_exit "Cannot find archive: $dist_file"
    fi

    if [ ! -d $project_dir ]; then
	warn "Cannot find projct: $project_dir" $'\ncreat it'
	mkdir $project_dir
	if [ ! -d $project_dir ]; then
	    error_exit "Failed to create $new_projct"
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
    echo	"$dist_file"

    debug_exit

    python $caty_home/tools/caty-installer.py --compare=digest \
	--project=$project_dir \
        --log-dir=$project_dir/features/ --backup-dir=$project_dir/backup/ \
	--dest=$dest \
	$dist_file
}

function cmd_error {
    echo Usage: $0 command args ...
    echo command: list, install
    exit 1
}

function usage {
    echo "** Usage: $0 destinationType distPackageFile destinationProjectDir [destinationAppName]"
}

# ==== main ====

if [ ! -f $caty_home/tools/caty-installer.py ]; then
    error_exit "cannot find installer"
fi

if [ -z "$1" ]; then
    usage
    echo ""
    echo "** destinationType:"
    echo "project | prj"
    echo "global | glb"
    echo "application | app"

    exit 1
fi

case "$1" in
    project|prj)
	SUBEXT=caty-prj
	dest_type=prj
       ;;
    global|glb)
	SUBEXT=caty-glb
	dest_type=glb
	;;
    *)
	SUBEXT=caty-app
	dest_type=app
	;;
    *)
	error_exit "Illegal destinationType"
	;;
esac

if [ -z "$2" ]; then
    usage
    echo ""
    echo "** distPackageFile:"
    list_dists $dest_type

    exit 1
fi
dist_file=$2


if [ -z "$3" ]; then
    exists_dist_file $dist_file
    if [ $? == 0 ]; then
	usage
    else
	echo "distPackageFile '$dist_file' NOT found"
    fi
    exit 1
fi
project_dir=$3

debug "dest_type=$dest_type"
if [ "$dest_type" = "app" -a -z "$4" ]; then
    usage
    exit 1
fi
case $dest_type in
    prj)
	dest=project
	;;
    glb)
	dest=global
	;;
    *)
	dest=$4
	;;
esac

do_install $dest_type $dist_file $project_dir $dest

