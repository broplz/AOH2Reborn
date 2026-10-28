#!/usr/bin/env bash
# Link this repo's addon folders into the Dota 2 install so the Workshop Tools open `attackcopy`.
#
#   bash scripts/agents/link_addon.sh [--dota-dir <path>] [--help]
#
# Links  <dota>/game/dota_addons/attackcopy    -> <repo>/game/dota_addons/attackcopy
#        <dota>/content/dota_addons/attackcopy -> <repo>/content/dota_addons/attackcopy
# <dota> defaults to the Steam install of the OS (macOS, Windows/Git Bash). macOS uses symlinks,
# Windows uses junctions (no admin rights). Idempotent; never deletes or overwrites anything.
# Exit 0 OK (linked or already linked) · 1 conflict (something else is at a link path) ·
#      2 bad usage (dota dir not found, unsupported OS, unknown argument).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ADDON="attackcopy"
SUBDIRS=(game content)

DOTA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --help|-h) head -n 11 "$0" | tail -n +2; exit 0 ;;
    --dota-dir) [ $# -ge 2 ] || { echo "missing value for --dota-dir" >&2; exit 2; }; DOTA="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

UNAME="$(uname -s)"
if [ -z "$DOTA" ]; then
  case "$UNAME" in
    Darwin) DOTA="$HOME/Library/Application Support/Steam/steamapps/common/dota 2 beta" ;;
    MINGW*|MSYS*|CYGWIN*) DOTA="/c/Program Files (x86)/Steam/steamapps/common/dota 2 beta" ;;
    *) echo "unsupported OS: $UNAME; pass --dota-dir" >&2; exit 2 ;;
  esac
fi
case "$DOTA" in /*) ;; *) DOTA="$PWD/$DOTA" ;; esac
[ -d "$DOTA" ] || { echo "dota dir not found: $DOTA" >&2; exit 2; }

make_link() { # <link> <target>
  case "$UNAME" in
    MINGW*|MSYS*|CYGWIN*) cmd //c mklink /J "$(cygpath -w "$1")" "$(cygpath -w "$2")" >/dev/null ;;
    *) ln -s "$2" "$1" ;;
  esac
}

rc=0
for sub in "${SUBDIRS[@]}"; do
  target="$ROOT/$sub/dota_addons/$ADDON"
  link="$DOTA/$sub/dota_addons/$ADDON"
  if [ -e "$link" ] || [ -L "$link" ]; then
    if [ "$(cd "$link" 2>/dev/null && pwd -P)" = "$(cd "$target" && pwd -P)" ]; then
      echo "ok: already linked: $link"
    else
      echo "conflict: $link exists and is not a link to $target"
      rc=1
    fi
    continue
  fi
  mkdir -p "$(dirname "$link")"
  make_link "$link" "$target"
  echo "linked: $link -> $target"
done
exit "$rc"
