import os
from pathlib import Path

base_dir = str(Path(__file__).parent / "paper")
intro_file = os.path.join(base_dir, "paper_draft_intro_discussion_conclusion.md")
lit_file = os.path.join(base_dir, "paper_draft_literature_review.md")
meth_file = os.path.join(base_dir, "paper_draft_methodology.md")
res_file = os.path.join(base_dir, "paper_draft_results.md")
output_file = os.path.join(base_dir, "paper_final_revised.md")


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()


def main():
    intro_content = read_file(intro_file)
    lit_content = read_file(lit_file)
    meth_content = read_file(meth_file)
    res_content = read_file(res_file)

    # Split Intro file into Part 1 (Abstract + Intro) and Part 2 (Discussion + Conclusion)
    # Finding the split point "## 5. Discussion"
    split_idx = -1
    for i, line in enumerate(intro_content):
        if line.strip().startswith("## 5. Discussion"):
            split_idx = i
            break

    if split_idx == -1:
        print("Error: Could not find '## 5. Discussion' in intro file.")
        return

    part1 = intro_content[:split_idx]
    part2 = intro_content[split_idx:]

    # Construct final content
    final_lines = []
    final_lines.extend(part1)
    final_lines.append("\n\n")
    final_lines.extend(lit_content)
    final_lines.append("\n\n")
    final_lines.extend(meth_content)
    final_lines.append("\n\n")
    final_lines.extend(res_content)
    final_lines.append("\n\n")
    final_lines.extend(part2)

    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(final_lines)

    print(f"Successfully compiled paper to {output_file}")
    print(f"Total lines: {len(final_lines)}")


if __name__ == "__main__":
    main()
