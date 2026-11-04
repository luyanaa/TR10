#!/usr/bin/env bash
# TR10 release gate: run every check in flow/checks and report an aggregate
# pass/fail.  Exit 0 only when every check passes; 1 on any failure.
#
# Individual scripts print their own detail.  This wrapper only sequences
# them and ORs the verdicts -- it is the single entry point CI / a release
# reviewer can invoke.
#
# Usage:  bash flow/checks/run_all.sh [check ...]
#   With no args, runs all checks.  Pass a subset to run a few.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

checks=(
  "check_pdk_env.py|preflight: manifest + file/env sanity|python3"
  "test_mdp_parity.sh|MDP Drawing<->Mask device parity|bash"
  "test_bulk_tie.sh|bulk/well-tie LVS regression|bash"
  "test_liberty_spice.sh|Liberty<->SPICE INV_X1|bash"
  "test_pex_crosscheck.sh|Magic<->OpenRCX PEX|bash"
)

# Optional subset selection by script basename.
wanted=("$@")
run_it() {
  local script="$1"
  if [[ ${#wanted[@]} -eq 0 ]]; then return 0; fi
  for w in "${wanted[@]}"; do [[ "$w" == "$script" ]] && return 0; done
  return 1
}

fail=0
for entry in "${checks[@]}"; do
  IFS='|' read -r script desc runner <<<"$entry"
  run_it "$script" || continue
  printf '\n================ %s\n' "$desc"
  if [[ ! -f "$HERE/$script" ]]; then
    echo "MISSING: $script"; fail=1; continue
  fi
  if "$runner" "$HERE/$script"; then
    echo "-> PASS $script"
  else
    echo "-> FAIL $script (exit $?)"; fail=1
  fi
done

printf '\n================ RESULT: %s ================\n' \
  "$([ $fail -eq 0 ] && echo PASS || echo FAIL)"
exit "$fail"
