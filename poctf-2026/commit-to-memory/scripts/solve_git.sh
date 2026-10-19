#!/bin/bash
# Commit to Memory (POCTF 2026, ID=100) - Git bundle forensics
# "Not everything git remembers is in your working tree."
# "the tree is a lie; the log is a river"
#
# Strategy: clone the bundle, then search ALL git objects including:
# - git notes
# - dangling/unreachable objects
# - reflogs
# - tree vs blob differences
# - commit message encoding
# - author/committer name encoding

BUNDLE="${1:?Usage: $0 <commits.bundle>}"
WORKDIR=$(mktemp -d)
echo "[*] Cloning bundle to $WORKDIR/repo"

git clone "$BUNDLE" "$WORKDIR/repo" 2>/dev/null
cd "$WORKDIR/repo" || exit 1

echo "[*] Git log (last 10):"
git log --oneline -10

echo ""
echo "[*] Total commits: $(git log --oneline | wc -l)"

echo ""
echo "[*] Files in working tree:"
find . -not -path './.git/*' -type f

echo ""
echo "[*] Checking git notes..."
git notes list 2>/dev/null
git log --format='%H %N' --notes 2>/dev/null | grep -v '^$' | head -20

echo ""
echo "[*] Checking for POCTF in any git object..."
git rev-list --all --objects | while read hash rest; do
  content=$(git cat-file -p "$hash" 2>/dev/null)
  if echo "$content" | grep -q "POCTF"; then
    echo "FOUND in $hash ($rest): $(echo "$content" | grep POCTF)"
  fi
done

echo ""
echo "[*] Checking dangling objects..."
git fsck --unreachable --no-reflogs 2>/dev/null | while read line; do
  hash=$(echo "$line" | awk '{print $3}')
  type=$(echo "$line" | awk '{print $2}')
  echo "  $type $hash"
  content=$(git cat-file -p "$hash" 2>/dev/null)
  if echo "$content" | grep -q "POCTF"; then
    echo "  ** FOUND FLAG: $(echo "$content" | grep POCTF)"
  fi
  echo "$content" | head -5
done

echo ""
echo "[*] Checking reflogs..."
git reflog 2>/dev/null | head -20

echo ""
echo "[*] Checking all blob content for hidden data..."
git rev-list --all --objects | awk '{print $1}' | while read hash; do
  type=$(git cat-file -t "$hash" 2>/dev/null)
  if [ "$type" = "blob" ]; then
    content=$(git cat-file -p "$hash" 2>/dev/null)
    # Check for high bytes, unusual chars, encoded data
    if echo "$content" | grep -qE '[A-Z0-9]{16,}'; then
      echo "  Blob $hash has long uppercase string: $(echo "$content" | grep -oE '[A-Z0-9]{16,}' | head -3)"
    fi
  fi
done

echo ""
echo "[*] Checking commit messages for hidden data..."
git log --format='%H|%s|%an|%ae' | while IFS='|' read hash subject author email; do
  # Check if first letters of commit messages spell something
  echo "$subject"
done | head -60

echo ""
echo "[*] Acrostic from commit messages (first char)..."
git log --reverse --format='%s' | while read msg; do
  printf '%s' "${msg:0:1}"
done
echo ""

echo ""
echo "[*] Acrostic from commit messages (first word first char)..."
git log --reverse --format='%s' | while read msg; do
  word=$(echo "$msg" | awk '{print $1}')
  printf '%s' "${word:0:1}"
done
echo ""

echo ""
echo "[*] Checking CHANGELOG content..."
cat CHANGELOG 2>/dev/null | head -60

echo ""
echo "[*] First char of each CHANGELOG line..."
cat CHANGELOG 2>/dev/null | while read line; do
  [ -n "$line" ] && printf '%s' "${line:0:1}"
done
echo ""

echo ""
echo "[*] Checking git diff between consecutive commits for hidden changes..."
commits=($(git log --reverse --format='%H'))
for ((i=0; i<${#commits[@]}-1; i++)); do
  diff=$(git diff "${commits[i]}" "${commits[i+1]}" -- CHANGELOG 2>/dev/null)
  added=$(echo "$diff" | grep '^+[^+]' | sed 's/^+//')
  if [ -n "$added" ]; then
    printf '%s' "${added:0:1}"
  fi
done
echo ""

echo ""
echo "[*] Done. Workdir: $WORKDIR/repo"
