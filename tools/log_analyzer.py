"""Summarise a DUT log: event counts, faults and state-transition history.

Usage:  python tools/log_analyzer.py path/to/log.txt
Log line format:  t=<ms> <LEVEL> <EVENT> <detail...>
"""
import re
import sys
from collections import Counter

LINE = re.compile(r"^t=(?P<t>\d+)\s+(?P<level>[A-Z]+)\s+(?P<event>[A-Z_]+)\s*(?P<detail>.*)$")


def parse(lines):
    for raw in lines:
        m = LINE.match(raw.strip())
        if m:
            yield {"t": int(m["t"]), "level": m["level"], "event": m["event"], "detail": m["detail"]}


def analyse(lines) -> dict:
    entries = list(parse(lines))
    return {
        "total": len(entries),
        "by_level": dict(Counter(e["level"] for e in entries)),
        "by_event": dict(Counter(e["event"] for e in entries)),
        "faults": [e for e in entries if e["event"] == "FAULT"],
        "transitions": [(e["t"], e["detail"]) for e in entries if e["event"] == "STATE"],
    }


def main(path: str) -> None:
    with open(path) as fh:
        result = analyse(fh)
    print(f"Entries: {result['total']}  Levels: {result['by_level']}")
    for e in result["faults"]:
        print(f"FAULT at t={e['t']} ms: {e['detail']}")
    for t, d in result["transitions"]:
        print(f"  t={t:>6} ms  {d}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
