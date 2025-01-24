#!/usr/bin/env bash

set -euo pipefail

unset url
unset fname
unset user
unset password
unset host
unset port
unset db
unset schema
unset table

usage(){
>&2 cat << EOF
Usage: $0
   [ --url-trips input ]
   [ --url-zones input ]
   [ --fname-trips input ]
   [ --fname-zones input ]
   [ --user input ]
   [ --password input ]
   [ --host input ]
   [ --port input ]
   [ --db input ]
   [ --schema input ]
   [ --table-trips input ]
   [ --table-zones input ]
EOF
exit 1
}

args=$(getopt -a -o h -l \
help,url-trips:,url-zones:,fname-trips:,fname-zones:,user:,password:,host:,port:,db:,schema:,table-trips:,table-zones: \
-- "$@")

if [[ $? -gt 0 ]]; then
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
    '--url-trips')
        url_trips=$2
        shift 2
        continue
    ;;
    '--url-zones')
        url_zones=$2
        shift 2
        continue
    ;;
    '--fname-trips')
        fname_trips=$2
        shift 2
        continue
    ;;
    '--fname-zones')
        fname_zones=$2
        shift 2
        continue
    ;;
    '--user')
        user=$2
        shift 2
        continue
    ;;
    '--password')
        password=$2
        shift 2
        continue
    ;;
    '--host')
        host=$2
        shift 2
        continue
    ;;
    '--port')
        port=$2
        shift 2
        continue
    ;;
    '--db')
        db=$2
        shift 2
        continue
    ;;
    '--schema')
        schema=$2
        shift 2
        continue
    ;;
    '--table-trips')
        table_trips=$2
        shift 2
        continue
    ;;
    '--table-zones')
        table_zones=$2
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
    ;;
  esac
done

pip install --upgrade pip
pip install --user -r requirements.txt

ready=1
if [[ ! -v url_trips ]]; then
    echo "Missing url_trips"
    ready=0
fi

if [[ ! -v url_zones ]]; then
    echo "Missing url_zones"
    ready=0
fi

if [[ ! -v fname_trips ]]; then    
    echo "Missing fname_trips"
    ready=0
fi

if [[ ! -v fname_zones ]]; then    
    echo "Missing fname_zones"
    ready=0
fi

if [[ ! -v user ]]; then
    echo "Missing username"
    ready=0
fi

if [[ ! -v password ]]; then
    echo "Missing password"
    ready=0
fi

if [[ ! -v host ]]; then
    echo "Missing host"
    ready=0
fi

if [[ ! -v port ]]; then
    echo "Missing port"
    ready=0
fi

if [[ ! -v db ]]; then
    echo "Missing db"
    ready=0
fi

if [[ ! -v schema ]]; then
    echo "Missing schema"
    ready=0
fi

if [[ ! -v table_trips ]]; then
    echo "Missing table_trips"
    ready=0
fi

if [[ ! -v table_zones ]]; then
    echo "Missing table_zones"
    ready=0
fi

if [[ ready -eq 0 ]]; then
    usage
fi

python data_manager.py \
    --url-trips=$url_trips \
    --url-zones=$url_zones \
    --fname-trips=$fname_trips \
    --fname-zones=$fname_zones \
    --username=$user \
    --password=$password \
    --host=$host \
    --port=$port \
    --db=$db \
    --schema=$schema \
    --table-trips=$table_trips \
    --table-zones=$table_zones

echo "Data ingestion completed!"
