#!/bin/bash

# Git cannot manage files owned by other users (e.g., 5050:root and 70:70).
# However, TLS private key certificates and pgAdmin password file must be
# owned by those users for security reasons. Therefore, we tell git to stop
# monitoring changes to those files using the `--skip-worktree`. However,
# we need to revert this action before checking out to other git branch.

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

for file in "${ignored[@]}"; do
  git update-index --no-skip-worktree -- "${file}"
  echo "git update-index --no-skip-worktree -- \"${file}\""
  sudo chown `id -u`:`id -g` "${file}"
  echo "sudo chown `id -u`:`id -g` \"${file}\""
done

echo -e "Stashing changes..."
git stash save "Ownership changes for security reasons."
echo "done"
git checkout -m $@
git stash pop

for idx in "${!ignored[@]}"; do
  git update-index --skip-worktree -- "${ignored[${idx}]}}"
  echo "git update-index --skip-worktree -- \"${ignored[${idx}]}\""
  sudo chown {ownership[${idx}]} "${ignored[${idx}]}"
  echo "sudo chown ${ownership[${idx}]} \"${ignored[${idx}]}\""
done