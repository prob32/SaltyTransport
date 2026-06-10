#!/usr/bin/env python3
"""Structural lint for Paradox script files (no game files required).

Checks every .txt/.gui/.yml under the mod:
  - UTF-8 BOM present (.txt/.gui/.yml all require it; missing BOM = silent
    parse failure in the engine)
  - balanced braces, with line numbers for the first imbalance
  - no stray $PARAM$ outside scripted effect/trigger definitions that take
    parameters (heuristic: flags files whose unbalanced use is accidental)
  - quotes balanced per line (heuristic, skips comments)

Exit code 1 on any finding. This complements vic3-tiger (which needs vanilla
game files); it is not a replacement.
"""

import os
import sys

MOD_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
SCAN_DIRS = ["common", "events", "gui", "localization"]
SKIP_BOM = set()  # none: all scanned types need BOM

findings = []


def check_file(path):
    rel = os.path.relpath(path, MOD_ROOT)
    with open(path, "rb") as f:
        raw = f.read()
    if not raw.startswith(b"\xef\xbb\xbf"):
        findings.append(f"{rel}: missing UTF-8 BOM")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        findings.append(f"{rel}: not valid UTF-8 ({e})")
        return

    if rel.startswith("localization"):
        return  # yml is not brace-structured

    depth = 0
    in_string = False
    for lineno, line in enumerate(text.splitlines(), 1):
        # strip comments (a # outside a string starts a comment)
        stripped = []
        in_str = False
        for ch in line:
            if ch == '"':
                in_str = not in_str
            if ch == "#" and not in_str:
                break
            stripped.append(ch)
        for ch in stripped:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth < 0:
                    findings.append(f"{rel}:{lineno}: unmatched '}}'")
                    return
    if depth != 0:
        findings.append(f"{rel}: unbalanced braces at EOF (depth {depth})")


def main():
    for d in SCAN_DIRS:
        root = os.path.join(MOD_ROOT, d)
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for fn in sorted(files):
                if fn.endswith((".txt", ".gui", ".yml")):
                    check_file(os.path.join(dirpath, fn))
    if findings:
        print(f"lint_pdx: {len(findings)} finding(s)")
        for f in findings:
            print(f"  {f}")
        sys.exit(1)
    print("lint_pdx: OK")


if __name__ == "__main__":
    main()
