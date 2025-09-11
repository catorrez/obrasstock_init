#!/usr/bin/env bash
set -euo pipefail
VER="${1:?Uso: ./release.sh vX.Y.Z}"
echo "${VER#v}" > VERSION
git add -A
git commit -m "chore(release): ${VER}"
git push
git tag -a "${VER}" -m "Release ${VER}"
git push --follow-tags
echo "Listo: ${VER}"
