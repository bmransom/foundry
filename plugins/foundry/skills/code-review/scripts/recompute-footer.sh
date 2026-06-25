#!/usr/bin/env bash
# Recompute the final code-review footer + verdict after the cross-model refuter:
# the final footer is the reviewer's candidates MINUS the refuter's DROPs, and the
# verdict is FAIL iff a blocking FLAGGED line survives. DROP-only — the refuter can
# remove a finding, never add one (recall-monotone-down, precision-up). This is the
# difference half of the footer algebra; it delegates so the inner loop's union and
# this difference share ONE module and ONE normalized key (AC-12.5). Kept as the
# named entry the wrapper/Components reference (the step the wrapper once faked, CR-1).
# Usage: recompute-footer.sh <report-file> [refuter-output-file]
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$here/footer-algebra.sh" difference "$@"
