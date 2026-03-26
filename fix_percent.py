import re
from pathlib import Path

body_path = Path("C:/Projects/TDL/papers/P01-VR-PH-Core/latex/body.tex")
text = body_path.read_text(encoding="utf-8")

lines = text.split("\n")
new_lines = []
changed = 0
for line in lines:
    stripped = line.lstrip()
    if stripped.startswith("%"):
        # Genuine LaTeX comment line — leave it alone
        new_lines.append(line)
    else:
        # Escape all unescaped % in this line
        new_line = re.sub(r"(?<!\\)%", r"\\%", line)
        if new_line != line:
            changed += 1
            print(f"Fixed: {line.strip()!r}")
        new_lines.append(new_line)

body_path.write_text("\n".join(new_lines), encoding="utf-8")
print(f"\nDone. {changed} lines fixed.")
