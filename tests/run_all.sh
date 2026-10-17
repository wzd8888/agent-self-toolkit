#!/bin/sh
# Run every tool's built-in self-test. Exit 0 only if all pass.
# Usage: sh tests/run_all.sh
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
fail=0
total=0

for f in "$ROOT"/tools/*.py; do
    name=$(basename "$f")
    total=$((total + 1))
    out=$(cd /tmp && python3 "$f" --self-test 2>&1)
    rc=$?
    if [ $rc -eq 0 ]; then
        printf 'PASS  %-24s %s\n' "$name" "$(echo "$out" | tail -1 | cut -c1-60)"
    else
        fail=$((fail + 1))
        printf 'FAIL  %-24s exit=%s\n' "$name" "$rc"
        echo "$out" | tail -15
    fi
done

echo "----------------------------------------"
if [ $fail -eq 0 ]; then
    echo "ALL PASS ($total tools)"
    exit 0
fi
echo "FAILED: $fail/$total"
exit 3
