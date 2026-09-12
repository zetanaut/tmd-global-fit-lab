#!/usr/bin/env bash
set -euo pipefail
repo='zetanaut/tmd-global-fit-lab'
gh_bin="${TMD_GH:-gh}"
if [[ "$($gh_bin api user --jq .login)" != 'zetanaut' ]]; then
  echo 'Authenticate GitHub CLI as zetanaut before publishing.' >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'Commit and review repository contents before publishing.' >&2
  exit 2
fi
if "$gh_bin" repo view "$repo" >/dev/null 2>&1; then
  echo 'Repository already exists; inspect it and configure origin explicitly. Nothing overwritten.' >&2
  exit 2
fi
# Private is deliberate. Public redistribution requires a separate rights review.
"$gh_bin" repo create "$repo" --private --description 'Portable fixed-physics DY/SIDIS architecture experiments, cluster execution and immutable results' --source . --remote origin
git -c "credential.https://github.com.helper=!$gh_bin auth git-credential" push -u origin main
"$gh_bin" repo view "$repo" --json nameWithOwner,url,visibility
