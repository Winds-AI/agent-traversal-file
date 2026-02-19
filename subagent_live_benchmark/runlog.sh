#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <logfile> <command...>" >&2
  exit 2
fi

logfile="$1"
shift
cmd="$*"

out_file="$(mktemp)"
err_file="$(mktemp)"

set +e
bash -lc "$cmd" >"$out_file" 2>"$err_file"
status=$?
set -e

{
  echo "-----"
  echo "CMD: $cmd"
  echo "EXIT: $status"
  echo "STDOUT<<EOF"
  cat "$out_file"
  echo "EOF"
  echo "STDERR<<EOF"
  cat "$err_file"
  echo "EOF"
} >> "$logfile"

cat "$out_file"
cat "$err_file" >&2

rm -f "$out_file" "$err_file"
exit "$status"
