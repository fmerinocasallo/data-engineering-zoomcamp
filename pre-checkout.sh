#!/bin/bash

# Git cannot manage files owned by other users (e.g., 5050:root and 70:70).
# However, TLS private key certificates and pgAdmin password file must be
# owned by those users for security reasons. Therefore, we tell git to stop
# monitoring changes to those files using the `--skip-worktree`. However,
# we need to revert this action before checking out to other git branch.

ignored=( $(git ls-files -v | grep "^S " | cut -c3-) )

for x in "${ignored[@]}"; do
  git update-index --no-skip-worktree -- "$x"
done

git stash save "Ownership changes for security reasons."

git checkout -m $@

git stash pop

for x in "${ignored[@]}"; do
  git update-index --skip-worktree -- "$x"
done