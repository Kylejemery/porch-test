"""Check every item file against the rules in RUBRIC_SPEC.md.

    python scripts/validate_items.py

Exits with an error if any item breaks a rule. Prints a summary of how many
items each track has and how many sources still need verifying.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS_DIR = ROOT / "items"

TRACKS = {
    "stoic_logic": "T1",
    "sophisms": "T2",
    "doctrine": "T3",
    "applied_ethics": "T4",
    "epistemic_honesty": "T5",
}
REQUIRED = ["id", "track", "prompt", "gold_answer", "rubric", "sources", "difficulty", "status"]
STATUSES = {"draft", "reviewed", "held", "retired"}
SOURCE_STATUSES = {"ledger", "verified", "to_verify"}


def main() -> int:
    errors: list[str] = []
    seen: set[str] = set()
    per_track: Counter[str] = Counter()
    to_verify = 0
    publishable = 0

    for path in sorted(ITEMS_DIR.glob("track*.json")):
        items = json.loads(path.read_text(encoding="utf-8"))
        for item in items:
            iid = item.get("id", f"<no id in {path.name}>")
            for field in REQUIRED:
                if field not in item:
                    errors.append(f"{iid}: missing field '{field}'")
            if iid in seen:
                errors.append(f"{iid}: duplicate id")
            seen.add(iid)

            track = item.get("track")
            if track not in TRACKS:
                errors.append(f"{iid}: unknown track '{track}'")
            elif not iid.startswith(TRACKS[track] + "-"):
                errors.append(f"{iid}: id prefix does not match track {track}")

            rubric = item.get("rubric", [])
            if not 3 <= len(rubric) <= 5:
                errors.append(f"{iid}: rubric has {len(rubric)} criteria (need 3 to 5)")

            if item.get("difficulty") not in (1, 2, 3):
                errors.append(f"{iid}: difficulty must be 1, 2 or 3")
            if item.get("status") not in STATUSES:
                errors.append(f"{iid}: bad status '{item.get('status')}'")

            sources = item.get("sources", [])
            if not sources:
                errors.append(f"{iid}: no sources")
            unverified = False
            for s in sources:
                if s.get("status") not in SOURCE_STATUSES:
                    errors.append(f"{iid}: source '{s.get('cite')}' has bad status")
                if s.get("status") == "verified" and not s.get("evidence"):
                    errors.append(f"{iid}: source '{s.get('cite')}' is verified but has no evidence")
                if s.get("status") == "to_verify":
                    to_verify += 1
                    unverified = True
            if item.get("status") == "reviewed" and unverified:
                errors.append(f"{iid}: marked reviewed but has to_verify sources")
            if not unverified:
                publishable += 1

            per_track[track] += 1

    print("Items per track:")
    for track in TRACKS:
        print(f"  {track:<18} {per_track[track]}")
    print(f"Total items: {sum(per_track.values())}")
    print(f"Items with every source verified: {publishable}")
    print(f"Sources still to verify: {to_verify}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  {e}")
        return 1
    print("\nAll items pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
