#!/bin/sh
set -eu
SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PREFIX=${CLITOOLS_PREFIX:-"$HOME/.local"}
if [ "${1:-}" = "--prefix" ]; then
  [ "$#" -eq 2 ] || { echo "Usage: $0 [--prefix DIR]" >&2; exit 2; }
  PREFIX=$2
elif [ "$#" -ne 0 ]; then
  echo "Usage: $0 [--prefix DIR]" >&2; exit 2
fi
case "$PREFIX" in /*) ;; *) echo "Prefix must be an absolute path" >&2; exit 2;; esac
DEST="$PREFIX/share/floyd-cli-tools"
mkdir -p "$DEST" "$PREFIX/bin"
for dir in SKILLER PROMPTER SALVAGER KEYRING RECALLER lib; do
  cp -R "$SOURCE_DIR/$dir" "$DEST/"
done
for pair in SKILLER:skiller PROMPTER:prompter SALVAGER:salvager KEYRING:keyring RECALLER:recaller KEYRING:keyring-app SALVAGER:salvager-app RECALLER:recaller-app; do
  dir=${pair%%:*}; name=${pair#*:}
  chmod 755 "$DEST/$dir/$name"
  if [ -e "$PREFIX/bin/$name" ] && [ ! -L "$PREFIX/bin/$name" ]; then
    echo "Existing executable $PREFIX/bin/$name: refusing to replace it" >&2; exit 1
  fi
  ln -sfn "$DEST/$dir/$name" "$PREFIX/bin/$name"
done
echo "Installed five tools and three MCP servers to $PREFIX/bin"
echo "Add that directory to PATH. Personal credentials and indexes stay with their owner."
