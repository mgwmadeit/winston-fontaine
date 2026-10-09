"""Turn YouTube auto-caption .vtt files into clean plain text (drops rolling duplicates)."""
import re
import sys
from pathlib import Path

for path in sys.argv[1:]:
    seen, out = set(), []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line or "-->" in line or line.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        if line not in seen:
            seen.add(line)
            out.append(line)
    text = " ".join(out)
    dest = Path(path).with_suffix(".txt")
    dest.write_text(text, encoding="utf-8")
    print(f"{dest.name}: {len(text.split())} words")
