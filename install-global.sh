#!/bin/bash
# install-global.sh — make the CLITOOLS suite truly machine-wide.
#
# Before: tools lived in ~douglas/.local/bin and read only ~douglas's
# config, so no other account on this Mac could run them.
#
# After:
#   /usr/local/bin/{skiller,qglm,prompter,lgcy,salvager,keyring,recaller}
#                                                on every account's PATH
#   /usr/local/share/skiller/                    shared skill index + catalog
#   /usr/local/share/recaller/                   shared transcript index
#   /usr/local/share/qglm/.qglm.yaml             shared API credentials
#   /usr/local/share/lgcy/config.json            shared default settings
#
# Per-user state (history, sessions, personal config) stays in each
# user's own home. Shared credentials are root:admin 0640, never
# world-readable.
#
# Run: sudo bash /Volumes/Storage/CLITOOLS/install-global.sh
set -euo pipefail

TOOLS=/Volumes/Storage/CLITOOLS
BIN=/usr/local/bin
SHARE=/usr/local/share

if [ "$(id -u)" -ne 0 ]; then
  echo "install-global: must run as root (use sudo)" >&2
  exit 1
fi

if [ ! -d "$TOOLS" ]; then
  echo "install-global: $TOOLS not mounted" >&2
  exit 1
fi

echo "==> creating shared directories"
install -d -o root -g admin -m 0755 "$BIN"
install -d -o root -g admin -m 0755 "$SHARE/skiller"
install -d -o root -g admin -m 0755 "$SHARE/skiller/skills"
install -d -o root -g admin -m 0755 "$SHARE/qglm"
install -d -o root -g admin -m 0755 "$SHARE/lgcy"
install -d -o root -g admin -m 0755 "$SHARE/recaller"

echo "==> linking executables into $BIN"
link_tool() {
  local name="$1" target="$2"
  if [ ! -e "$target" ]; then
    echo "    skip $name (missing $target)"
    return
  fi
  chmod a+rx "$target" 2>/dev/null || true
  ln -sfn "$target" "$BIN/$name"
  echo "    $BIN/$name -> $target"
}

link_tool skiller  "$TOOLS/SKILLER/skiller"
link_tool prompter "$TOOLS/PROMPTER/prompter"
link_tool qglm     "$TOOLS/QGLM/qglm"
link_tool lgcy     "$TOOLS/LGCY/dist/lgcy"
link_tool salvager "$TOOLS/SALVAGER/salvager"
link_tool keyring  "$TOOLS/KEYRING/keyring"
link_tool recaller "$TOOLS/RECALLER/recaller"

# The Python tools import the shared chrome from $TOOLS/lib, so it must
# be readable by every account too.
chmod -R a+rX "$TOOLS/lib" 2>/dev/null || true

echo "==> seeding shared credentials"
# Resolve the human who invoked us. SUDO_USER covers `sudo`, but under
# osascript's "with administrator privileges" it is unset, so fall back
# to the owner of the current console session.
SEED_USER="${SUDO_USER:-$(stat -f '%Su' /dev/console 2>/dev/null || true)}"
if [ -z "$SEED_USER" ] || [ "$SEED_USER" = "root" ]; then
  SEED_USER="${INSTALL_SEED_USER:-}"
fi
SEED_HOME="${SEED_USER:+/Users/$SEED_USER}"
echo "    seeding from user: ${SEED_USER:-<none>}"

# Copy the existing working config so other accounts inherit it.
# 0640 root:admin: readable by admin users, not by the world.
SRC_QGLM="$SEED_HOME/.qglm.yaml"
if [ -n "$SEED_HOME" ] && [ -f "$SRC_QGLM" ] && [ ! -f "$SHARE/qglm/.qglm.yaml" ]; then
  install -o root -g admin -m 0640 "$SRC_QGLM" "$SHARE/qglm/.qglm.yaml"
  echo "    seeded $SHARE/qglm/.qglm.yaml from $SRC_QGLM"
else
  echo "    $SHARE/qglm/.qglm.yaml already present or no source; leaving as-is"
fi

echo "==> migrating the skill index to shared storage"
SRC_INDEX="$SEED_HOME/.skiller/index.json"
if [ -n "$SEED_HOME" ] && [ -f "$SRC_INDEX" ] && [ ! -f "$SHARE/skiller/index.json" ]; then
  install -o root -g admin -m 0644 "$SRC_INDEX" "$SHARE/skiller/index.json"
  echo "    seeded $SHARE/skiller/index.json (rebuild with: skiller index)"
fi

echo "==> verifying"
for t in skiller prompter qglm lgcy salvager keyring recaller; do
  if [ -x "$BIN/$t" ]; then echo "    ok   $t"; else echo "    MISS $t"; fi
done

cat <<'EOF'

Done. Every account on this machine can now run:
    skiller · qglm · prompter · lgcy · salvager · keyring · recaller

/usr/local/bin is on the default macOS PATH, so no shell config needed.

Next (as an admin user):
    skiller index      # rebuild the skill index into shared storage
    recaller index     # index session transcripts for command recall
    keyring            # audit credentials (never prints a secret)
    salvager           # find unsaved work across every repo
EOF
