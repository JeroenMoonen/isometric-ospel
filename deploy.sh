#!/usr/bin/env bash
# Publish site/ to GitHub Pages: one fresh commit on the gh-pages branch, force-pushed,
# so the tile pyramid never piles up in the repository history.
set -euo pipefail
builtin cd "$(dirname "$0")"
[ -f site/index.html ] || { echo "site/ is empty: run ./build.sh first" >&2; exit 1; }
cp viewer/index.html site/index.html

remote=$(git remote get-url origin)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp -r site/. "$tmp"
git -C "$tmp" init -q -b gh-pages
git -C "$tmp" add -A
git -C "$tmp" -c user.name="$(git config user.name)" -c user.email="$(git config user.email)" \
  commit -q -m "Publish map ($(git rev-parse --short HEAD))"
git -C "$tmp" push -q -f "$remote" gh-pages
echo "Pushed $(find site -type f | wc -l) files to gh-pages"
