#!/usr/bin/env bash

# Git cannot manage files owned by other users (e.g., 5050:root and 70:70).
# However, TLS private key certificates and pgAdmin password file must be
# owned by those users for security reasons. Therefore, we tell git to stop
# monitoring changes to those files using the `--skip-worktree`. However,
# we need to revert this action before checking out to other git branch.

set -euo pipefail

unset mode

ignored=(
    "01-docker-terraform/01-docker-sql/pg-server/certs/server/server.key"
    "01-docker-terraform/01-docker-sql/pgadmin/certs/client/reader/fmerinocasallo_reader.key"
    "01-docker-terraform/01-docker-sql/pgadmin/certs/client/superuser/postgres.key"
    "01-docker-terraform/01-docker-sql/pgadmin/certs/client/writer/fmerinocasallo_writer.key"
    "01-docker-terraform/01-docker-sql/pgadmin/certs/server/server.key"
    "01-docker-terraform/01-docker-sql/pgadmin/passwds/.pgpass"
)

ownership=(
    "70:70"
    "5050:root"
    "5050:root"
    "5050:root"
    "5050:root"
    "5050:root"
)

usage(){
>&2 cat << EOF
Usage: $0
    [ --mode pre|post ]
EOF
exit 1
}

args=$(getopt -a -o h -l \
help,mode: \
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
        '--mode')
            mode=$2
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

ready=1
if [[ ! -v mode ]]; then
    echo "Missing mode"
    ready=0
fi

case $mode in
    'pre')
        echo -n "Updating git indices and files ownership..."
        for file in "${ignored[@]}"; do
            git update-index --no-skip-worktree -- "${file}"
            sudo chown `id -u`:`id -g` "${file}"
        done
        echo "done"
        echo "You are ready to change to another branch!"
    ;;
    'post')
        echo -n "Updating git indices and files ownership..."
        for idx in "${!ignored[@]}"; do
            git update-index --skip-worktree -- "${ignored[${idx}]}"
            sudo chown "${ownership[${idx}]}" "${ignored[${idx}]}"
        done
        echo "done"
        echo "You are ready to run Docker containers from module-1!"
    ;;
    *)
        echo "Unsupported mode: $mode. Valid modes are pre and post."
        usage
esac