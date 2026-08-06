#!/bin/bash
# finalize-global.sh — make the shared index directories actually usable.
#
# install-global.sh creates /usr/local/share/{skiller,recaller} owned by
# root:admin 0755. That is readable by everyone but writable by nobody
# except root, so `skiller index` and `recaller index` silently fall back
# to per-user indexes and the machine never gets one shared copy.
#
# This grants group-write to admin (0775) and setgid, so any admin user
# rebuilding an index updates the shared one and the group sticks. Then
# it seeds the shared indexes from the invoking user's existing ones.
set -euo pipefail

SHARE=/usr/local/share
[ "$(id -u)" -eq 0 ] || { echo "must run as root" >&2; exit 1; }

SEED_USER="${SUDO_USER:-$(stat -f '%Su' /dev/console 2>/dev/null || true)}"
SEED_HOME="${SEED_USER:+/Users/$SEED_USER}"
echo "==> seeding from: ${SEED_USER:-<none>}"

for d in skiller recaller qglm lgcy; do
  if [ -d "$SHARE/$d" ]; then
    chown -R root:admin "$SHARE/$d"
    # setgid so files created here stay group-admin
    chmod 2775 "$SHARE/$d"
    echo "    $SHARE/$d  root:admin 2775 (admin-writable)"
  fi
done
[ -d "$SHARE/skiller/skills" ] && chmod 2775 "$SHARE/skiller/skills"

# Seed shared indexes from the user's own, so the first shared read is
# warm instead of triggering a multi-minute rebuild.
seed() {
  local src="$1" dst="$2" name="$3"
  if [ -f "$src" ] && [ ! -f "$dst" ]; then
    install -o root -g admin -m 0664 "$src" "$dst"
    echo "    seeded $name ($(du -h "$dst" | cut -f1))"
  else
    echo "    $name: already present or no source"
  fi
}

if [ -n "$SEED_HOME" ]; then
  seed "$SEED_HOME/.skiller/index.json"  "$SHARE/skiller/index.json"  "skill index"
  seed "$SEED_HOME/.recaller/index.json" "$SHARE/recaller/index.json" "recall index"
  # Credentials stay 0640: readable by admin, never world.
  if [ -f "$SEED_HOME/.qglm.yaml" ] && [ ! -f "$SHARE/qglm/.qglm.yaml" ]; then
    install -o root -g admin -m 0640 "$SEED_HOME/.qglm.yaml" \
      "$SHARE/qglm/.qglm.yaml"
    echo "    seeded shared credentials (0640, not world-readable)"
  fi
fi

echo "==> result"
ls -ld "$SHARE"/skiller "$SHARE"/recaller "$SHARE"/qglm 2>/dev/null || true
[ -f "$SHARE/qglm/.qglm.yaml" ] && ls -l "$SHARE/qglm/.qglm.yaml"
echo "done"
