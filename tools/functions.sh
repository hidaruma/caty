# -*- coding: utf-8 -*-

#== 変数名
# prj_dir -- プロジェクトのルートディレクトリ
# app -- アプリケーション名
# app_dir -- アプリケーションのディレクトリ
# origin -- オリジン名
# origin_dir -- オリジンのディレクトリ
# origins -- オリジン名のリスト
# semver -- SemVer文字列 X.Y.Z 
# version -- バージョンのフル文字列（semverを含む）
# prod -- プロダクト名
# proddef_dir -- プロダクト定義のディレクトリ
# prods_dir -- products/ （プロダクト定義集）のディレクトリパス
# install_target_short -- prj, glb, app のどれか


function debug { # (msg) => STDERR
    local msg=$1

    if [ -z "$DEBUG" -o -z "$msg" ]; then
	: # dot nothing
    else
	echo "DEBUG:" $msg >&2
    fi
}

function debug_exit { # () => NEVER
 if [ -z "$DEBUG" ]; then
     : # dot nothing
 else
     echo "DEBUG: exit" >&2
     exit 0
 fi
}

function error_exit { # (msg) => VOID
    local msg=$1

    echo "ERROR:" $msg >&2
    exit 1
}

function warn { # (msg) => VOID
    local msg=$1

    echo "WARNING:" $msg >&2
}


## プロジェクト内でアプリケーションを探す
# プロジェクトディレクトリを基点としたアプリケーションディレクトリパスを返す。
# アプリケーションが存在しないときは空文字列を返す。
#
function find_app { # (prj_dir, app) => *STDOUT*
    local prj_dir=$1
    local app=$2

    local app_dir=""
    local groups=$(echo $prj_dir/*.group)
    debug "app='$app'"
    debug "groups='$groups'"
    for grp in $groups; do
	debug "group=$grp/$app"
	if [ -d $grp/$app ]; then
	    app_dir=$grp/$app
	    echo $app_dir
	    return 0
	fi
    done
    echo ""
    return 1
}

function get_semver { # (proddef_dir) => *STDOUT*
    local proddef_dir=$1

    if [ ! -f $proddef_dir/SemVer.txt ]; then
	echo 0.0.0> $proddef_dir/SemVer.txt
    fi
    local semver=$(cat $proddef_dir/SemVer.txt)
    echo $semver
}

function confirm_version { # (proddef_dir) => *STDOUT*
    local proddef_dir=$1

    if [ ! -f $proddef_dir/SemVer.txt ]; then
	echo 0.0.0> $proddef_dir/SemVer.txt
    fi
    local semver=$(cat $proddef_dir/SemVer.txt)

    if [ ! -f $proddef_dir/Version.txt -o -n "$semver" ]; then
	debug "confirm_version: making Version.txt"
	make_version $semver > $proddef_dir/Version.txt
    fi
    local version=$(cat $proddef_dir/Version.txt)
    debug "confirm_version: version=$version"
    echo "$version"
}

function expand_template { # (proddef_dir) => *STDOUT*
    local proddef_dir=$1

    local version=$(cat $proddef_dir/Version.txt)
    debug "expand_template: version=$version"

    cat $proddef_dir/package.template.json | sed -e 's/\$\$/\$/g' -e "s/\\\$version/$version/g" > $proddef_dir/package.json
}

function make_version { # ($proddef_dir) => *STDOUT*
    local semver=$(get_semver $proddef_dir)
    local Suffix=r$(hg parent $File | grep ^changeset | cut -d: -f2,3 | sed -e 's/ //g' -e 's/:/./' )
    local d=$(date +%Y%m%d)
    
    echo "$semver+$Suffix$d"
}


function make_archive_name { # (proddef_dir, install_target_suffix) => *STDOUT*
    local proddef_dir=$1
    local install_target_suffix=$2

    if [ ! -f $proddef_dir/SemVer.txt ]; then
	echo 0.0.0> $proddef_dir/SemVer.txt
    fi
    local version=$(make_version $proddef_dir)
    debug "make_archive_name: version=$version"

    prod=$(echo $proddef_dir | sed -e 's@/$@@' -e 's@^.*/@@')
    debug "make_archive_name: proddef_dir=$proddef_dir"
    debug "make_archive_name: prod=$prod"

    echo ${prod}_$version.$install_target_suffix.zip
}


function list_origins { # (prj_dir) => *STDOUT*

  local prj_dir=$1

  if [ -d $prj_dir/products ]; then
      echo project
  fi
  if [ -d $prj_dir/global/products ]; then
      echo global
  fi

  local groups=$(echo $prj_dir/*.group)
  for grp in $groups; do
      if [ -d $grp ]; then
	  local list=`/bin/ls -F $grp | grep '/$' | sed -e 's@/@@'`
	  for app in $list; do
	      if [ -d $grp/$app/products ]; then
		  echo $app
	      fi
	  done
      fi
  done
}

function list_prods { # (prj_dir, origin) => *STDOUT*
  local prj_dir=$1
  local origin=$2
  local origin_dir

  case "$origin" in
      project)
	  origin_dir=$prj_dir
	  ;;
      global)
	  origin_dir=$prj_dir/global
	  ;;
      *)
	  origin_dir=$(find_app $prj_dir $origin)
	  ;;
  esac
  debug "origin_dir=$origin_dir"

  local prods_dir=$origin_dir/products
  debug "prods_dir=$prods_dir"
  local list=$(/bin/ls -F $prods_dir 2>/dev/null | grep '^[^.]*/$' | sed -e 's@/@@')
  debug "list=$list"
  for f in $list; do
      echo $f
  done
}

function list_all_prods {
  local prj_dir=$1
  local origins=$(list_origins $prj_dir)
  debug "origins=$origins"
  local prods

  for ori in $origins; do
      prods=$(list_prods $prj_dir $ori)
      debug "prods=$prods @ $ori"
      for prod in $prods; do
	  echo ::$ori:$prod
      done
  done
}

function list_all_proddef_dirs {
  local prj_dir=$1
  local origins=$(list_origins $prj_dir)
  debug "origins=$origins"
  local prods

  for ori in $origins; do
      prods=$(list_prods $prj_dir $ori)
      debug "prods=$prods @ $ori"
      for prod in $prods; do
	  echo $prj_dir/$ori/prods/$prod
      done
  done
}

