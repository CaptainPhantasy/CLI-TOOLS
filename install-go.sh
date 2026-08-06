#!/bin/bash
# install-go.sh — install the Go toolchain machine-wide.
#
# /usr/local/go is Go's own documented install location, and /usr/local
# is already where this machine's shared tooling lives. Installing here
# (rather than under one user's home) means every account can build, and
# it survives the /Volumes/Storage drive being unmounted.
#
# The tarball is verified against the SHA256 published in go.dev's
# release manifest BEFORE this script runs; it is re-verified here so the
# check is part of the install rather than a separate manual step.
set -euo pipefail

TARBALL=/tmp/go1.26.5.darwin-arm64.tar.gz
WANT_SHA=efb87ff28af9a188d0536ef5d42e63dd52ba8263cd7344a993cc48dd11dedb6a
DEST=/usr/local

[ "$(id -u)" -eq 0 ] || { echo "must run as root" >&2; exit 1; }
[ -f "$TARBALL" ] || { echo "missing $TARBALL" >&2; exit 1; }

echo "==> verifying checksum"
GOT_SHA=$(shasum -a 256 "$TARBALL" | awk '{print $1}')
if [ "$GOT_SHA" != "$WANT_SHA" ]; then
  echo "CHECKSUM MISMATCH" >&2
  echo "  want $WANT_SHA" >&2
  echo "  got  $GOT_SHA" >&2
  exit 1
fi
echo "    ok  $GOT_SHA"

# Refuse to clobber an existing toolchain we didn't put there.
if [ -e "$DEST/go" ]; then
  echo "==> $DEST/go already exists; leaving it alone" >&2
  echo "    remove it manually if you intend to replace it" >&2
  exit 1
fi

echo "==> extracting to $DEST/go"
tar -C "$DEST" -xzf "$TARBALL"
chown -R root:wheel "$DEST/go"

echo "==> linking into /usr/local/bin"
for t in go gofmt; do
  ln -sfn "$DEST/go/bin/$t" "/usr/local/bin/$t"
  echo "    /usr/local/bin/$t -> $DEST/go/bin/$t"
done

echo "==> verifying"
/usr/local/bin/go version
echo "done"
