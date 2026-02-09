from pathlib import Path

patterns = ["huge_dir", "**/huge_dir", "**/huge_dir/", "**/huge_dir/*"]
paths = ["huge_dir", "data/huge_dir", "huge_dir/file"]

print(f"{'Path':<20} | {'Pattern':<15} | Match?")
print("-" * 50)

for p_str in paths:
    p = Path(p_str)
    for pat in patterns:
        clean_pat = pat.rstrip("/")
        try:
            match = p.match(clean_pat)
            if not match and clean_pat.startswith("**/"):
                match = p.match(clean_pat[3:])
            print(f"{p_str:<20} | {pat:<15} | {match}")
        except Exception as e:
            print(f"{p_str:<20} | {pat:<15} | Error: {e}")
