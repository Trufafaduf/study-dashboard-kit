#!/bin/sh
# Link this kit's .claude/commands and .claude/skills into a brain's .claude
# folder (macOS/Linux), so Claude Code discovers them from the outer repo.
#
#   scripts/link-kit.sh [brain-root]
#
# brain-root defaults to this kit's parent directory, i.e. the layout where
# the kit sits at <brain>/<kit-folder> (as a submodule or a plain clone).
#
# For each command file under .claude/commands and each skill folder under
# .claude/skills in this kit, creates a symlink at
# <brain-root>/.claude/<commands|skills>/<name> pointing back into the kit.
#
# Idempotent: a symlink that already points at the kit's copy is left alone
# and reported as already linked. A real file or folder, or a symlink to
# something else, is never touched - the script warns and skips it.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
KIT_ROOT="$(cd "$HERE/.." && pwd)"
BRAIN_ROOT="${1:-$(cd "$KIT_ROOT/.." && pwd)}"
BRAIN_ROOT="$(cd "$BRAIN_ROOT" && pwd)"

link_one() {
  rel="$1"
  target="$KIT_ROOT/$rel"
  dest="$BRAIN_ROOT/$rel"
  [ -e "$target" ] || return 0
  mkdir -p "$(dirname "$dest")"
  if [ -L "$dest" ]; then
    if [ "$(readlink "$dest")" = "$target" ]; then
      echo "ok (already linked): $rel"
      return 0
    fi
    echo "skip: $dest is a symlink to something else (leaving it alone)" >&2
    return 0
  fi
  if [ -e "$dest" ]; then
    echo "skip: $dest exists and is not a link (leaving it alone)" >&2
    return 0
  fi
  ln -s "$target" "$dest"
  echo "linked: $rel -> $target"
}

if [ -d "$KIT_ROOT/.claude/commands" ]; then
  for f in "$KIT_ROOT"/.claude/commands/*.md; do
    [ -e "$f" ] || continue
    link_one ".claude/commands/$(basename "$f")"
  done
fi

if [ -d "$KIT_ROOT/.claude/skills" ]; then
  for d in "$KIT_ROOT"/.claude/skills/*/; do
    [ -d "$d" ] || continue
    link_one ".claude/skills/$(basename "$d")"
  done
fi
