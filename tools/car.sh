#!/bin/sh

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

function find_app { # => app_path

  app_path=""

  prj_dir=$1
  app=$2
  for grp in main develop common extra examples; do
      if [ -d $prj_dir/$grp/$app ]; then
	  app_path=$prj_dir/$grp/$app
	  return 
      fi
  done
}

function list_apps { # => apps

  prj_dir=$1

  if [ -d $prj_dir/archiving ]; then
      echo project
  fi
  if [ -d $prj_dir/global/archiving ]; then
      echo global
  fi

  for grp in main develop common extra examples; do
      if [ -d $prj_dir/$grp/ ]; then
	  list=`/bin/ls -F $prj_dir/$grp/ | grep '/$' | sed -e 's@/@@'`
	  for app in $list; do
	      if [ -d $prj_dir/$grp/$app/archiving ]; then
		  echo $app
	      fi
	  done
      fi
  done
}


function list_dists {
  project_dir=$1
  origin=$2

  case "$origin" in
      project)
	  origin_dir=$project_dir
	  ;;
      global)
	  origin_dir=$project_dir/global
	  ;;
      *)
	  find_app $project_dir $origin
	  origin_dir=$app_path
	  ;;
  esac

  archiving=$origin_dir/archiving
  echo $archiving
  list=`/bin/ls $archiving/*.package.json 2>/dev/null`
  for f in $list; do
      basename $f .package.json
  done
}

# ==== main ====

if [ -z "$1" ]; then
    echo Usage: $0 project_dir [origin [dist_name]]
    exit 1
fi

project_dir=$1
origin=$2
dist_name=$3

if [ -z "$origin" ]; then
    list_apps $project_dir
    exit 0
fi


if [ -z "$dist_name" ]; then
    list_dists $project_dir $origin
    exit 0
fi


find_caty_home
if [ ! -f $caty_home/tools/caty-archiver.py ]; then
    echo "cannot find archiver"
    exit 1
fi


case "$origin" in
 project)
  origin_dir=$project_dir
  SUBEXT=caty-prj
  ;;
 global)
  origin_dir=$project_dir/global
  SUBEXT=caty-glb
  ;;
 *)
  find_app $project_dir $origin
  origin_dir=$app_path
  SUBEXT=caty-app
  ;;
esac

echo $origin_dir

if [ -z "$origin_dir" ]; then
    echo "Cannot find origin dir"
    exit 1
fi

fset=$origin_dir/archiving/$dist_name.fset

if [ ! -f "$fset" ]; then
    echo "Cannot find fset file: $fset"
    exit 1
fi

package_json=$origin_dir/archiving/$dist_name.package.json
meta_inf=$origin_dir/archiving/$dist_name.META-INF

if [ ! -f "$package_json" ]; then
    echo "Cannot find package.json file: $package_json"
    exit 1
fi

echo  $caty_home/dists/$dist_name.$SUBEXT.zip

python $caty_home/tools/caty-archiver.py \
 --project=$project_dir --origin=$origin \
 --fset=$fset --package-json=$package_json --meta-inf=$meta_inf \
 $caty_home/dists/$dist_name.$SUBEXT.zip
