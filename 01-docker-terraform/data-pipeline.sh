#!/usr/bin/env bash

set -euo pipefail

n_days=unset

usage(){
>&2 cat << EOF
Usage: $0
   [ -d | --n_days input ]
EOF
exit 1
}

args=$(getopt -a -o hd: -l help,n_days: -- "$@")
if [[ $? -gt 0 ]]; then
    echo "Hi there!"
    usage
fi

eval set -- ${args}
while [[ $# -gt 0 ]]; do
  case $1 in
    '-h' | '--help')
        usage
        shift
        continue
    ;;
    '-d' | '--n_days')
        n_days=$2
        shift 2
        continue
    ;;
    '--')
        shift
        break
    ;;
    *)
        >&2 echo "Unsupported option: $1"
        usage
        exit 1
    ;;
  esac
done

pip install --user -r requirements.txt

if [ -z $n_days ]; then
    python random_series.py
else
    python random_series.py --n_days=$n_days
fi
