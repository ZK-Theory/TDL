"""Strip duplicate header/abstract from body.tex and fix LaTeX issues."""

import re
from pathlib import Path

body_path = Path("c:/Projects/TDL/papers/P01-VR-PH-Core/latex/body.tex")

with open(body_path, encoding="utf-8") as f:
    lines = f.readlines()

# 1. Strip header block (title, authors, date, abstract, keywords) — lines 1-20
#    These duplicate what main.tex already defines.
lines = lines[20:]
text = "".join(lines)

# 2. Fix {wave}pid double-brace issue (causes unbalanced-brace LaTeX error)
text = text.replace(r"\texttt{{wave}pid}", r"\texttt{\{wave\}pid}")


# 3. Fix underscores inside \texttt{...} (underscore is special in LaTeX text mode)
def escape_texttt_underscores(m: re.Match) -> str:
    inner = m.group(1)
    inner = re.sub(r"(?<!\\)_", r"\\_", inner)
    return r"\texttt{" + inner + "}"


text = re.sub(r"\\texttt\{([^}]*)\}", escape_texttt_underscores, text)

# 4. Note: bare & in the content are valid table column separators — do NOT touch them.
#    The only problematic & was in the header (line 4: "JASA: Applications & Case Studies")
#    which is removed by step 1.

with open(body_path, "w", encoding="utf-8") as f:
    f.write(text)

print(f"Done. {len(text.splitlines())} lines written.")
