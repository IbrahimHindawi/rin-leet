"""LeetCode in rin.

    python leet.py next                  start the next unsolved problem on the path
    python leet.py random [-d easy]      start a random unsolved problem
    python leet.py start 1               set up problems/0001-two-sum/ (by number or slug)
    python leet.py test 1                run LeetCode's example cases on your solution
    python leet.py submit 1              test, then submit if the examples pass
    python leet.py show 1                print the statement
    python leet.py list [-d medium] [--todo] [--path blind75]
    python leet.py stats

`start` writes solution.rin with LeetCode's C signature as a comment; write a
rin proc with that same signature. `test` and `submit` compile it to one C file
(`rin compile --single-file`), put it in leetgo's file under judge/, and hand
it to leetgo. Problem numbers, titles and difficulties come from leetgo's
question cache.
"""
import argparse
import datetime
import json
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROBLEMS = ROOT / "problems"
PATHS = ROOT / "paths"
PROGRESS = ROOT / "progress.json"
JUDGE = ROOT / "judge"
BEGIN, END = "// @lc code=begin\n", "// @lc code=end"

DIFFICULTIES = ("Easy", "Medium", "Hard")


# ---- problems ---------------------------------------------------------------

def leetgo_cache():
    home = Path(os.environ.get("LEETGO_HOME", Path.home() / ".config" / "leetgo"))
    return home / "cache" / "leetcode-questions.json"


def load_problems():
    """Every LeetCode problem, from the cache leetgo keeps of the question list."""
    cache = leetgo_cache()
    if not cache.exists():
        leetgo("cache", "update")
    if not cache.exists():
        sys.exit(f"no question list at {cache}; run `leetgo cache update` in judge/")
    problems = []
    for q in json.loads(cache.read_text(encoding="utf-8")):
        if not q.get("questionFrontendId", "").isdigit():
            continue
        problems.append({
            "id": int(q["questionFrontendId"]),
            "slug": q["titleSlug"],
            "title": q["title"],
            "difficulty": q["difficulty"],
            "paid": bool(q.get("isPaidOnly")),
        })
    return sorted(problems, key=lambda p: p["id"])


def folder_of(p):
    return PROBLEMS / f"{p['id']:04d}-{p['slug']}"


def find(problems, ref):
    ref = ref.strip().rstrip("/\\")
    ref = Path(ref).name if ("/" in ref or "\\" in ref) else ref
    m = re.match(r"^0*(\d+)(?:-(.*))?$", ref)
    for p in problems:
        if (m and p["id"] == int(m.group(1))) or p["slug"] == ref:
            return p
    sys.exit(f"no problem matches '{ref}'")


def load_progress():
    try:
        return json.loads(PROGRESS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_progress(progress):
    PROGRESS.write_text(json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def solved(progress, p):
    return "solved" in progress.get(p["slug"], {})


# ---- tools ------------------------------------------------------------------

def rin_home():
    env = os.environ.get("RIN_HOME")
    if env and (Path(env) / "rin.exe").exists():
        return Path(env)
    found = shutil.which("rin")
    if found:
        return Path(found).resolve().parent
    default = Path("C:/devel/rin-windows-x64")
    if (default / "rin.exe").exists():
        return default
    sys.exit("cannot find rin.exe: set RIN_HOME or put it on PATH")


def leetgo(*args):
    """Runs leetgo in judge/, printing what it says; returns its output."""
    run = subprocess.run(["leetgo", *args], cwd=JUDGE, capture_output=True, text=True, encoding="utf-8")
    out = run.stdout + run.stderr
    print(out.rstrip())
    return out


def leetcode_file(p, fresh=False):
    """judge/c/<id>.<slug>.c, leetgo's copy of LeetCode's C template.
    `fresh` picks it again, restoring the template a submit overwrote."""
    def existing():
        return [f for f in (JUDGE / "c").glob("*.c") if f.name.split(".")[0] == f"{p['id']:04d}"]
    if fresh or not existing():
        leetgo("pick", str(p["id"]), "--skip-editor", "-y")
    files = existing()
    if not files:
        reason = "it is Premium only" if p["paid"] else "are you logged in to leetcode.com in Firefox?"
        sys.exit(f"leetgo could not pick problem {p['id']}: {reason}")
    return files[0]


def code_block(text):
    return text[text.index(BEGIN) + len(BEGIN):text.index(END)]


# ---- commands ---------------------------------------------------------------

def start(p):
    folder = folder_of(p)
    solution = folder / "solution.rin"
    rel = folder.relative_to(ROOT)
    if solution.exists():
        print(f"{rel}{os.sep}solution.rin already exists")
        return
    lc = leetcode_file(p, fresh=True)
    template = code_block(lc.read_text(encoding="utf-8")).strip("\n")
    folder.mkdir(parents=True, exist_ok=True)
    statement = lc.with_suffix(".md")
    if statement.exists():
        shutil.copyfile(statement, folder / "README.md")
    comment = "\n".join(("// " + line).rstrip() for line in template.splitlines())
    solution.write_text(
        'import "../../lib/lc.rin"\n'
        "\n"
        f"// {p['id']}. {p['title']} -- {p['difficulty']}\n"
        "// LeetCode calls this C function; write it in rin with the same signature,\n"
        "// importing the std containers you use. Call lc_begin() once at the top for\n"
        "// an arena that is emptied for each test case.\n"
        "//\n"
        f"{comment}\n",
        encoding="utf-8")
    print(f"{rel}{os.sep}  {p['difficulty']}")
    print(f"  write {rel / 'solution.rin'}, then: python leet.py test {p['id']}")


def build(p):
    """Compiles solution.rin to one C file and puts it in leetgo's file."""
    folder = folder_of(p)
    if not (folder / "solution.rin").exists():
        sys.exit(f"no solution yet: python leet.py start {p['id']}")
    (folder / "build").mkdir(exist_ok=True)
    rin = subprocess.run([str(rin_home() / "rin.exe"), "compile", "solution.rin", "-o", "build/solution.c",
                          "--single-file"], cwd=folder, capture_output=True, text=True)
    if rin.returncode != 0:
        sys.exit((rin.stdout + rin.stderr).strip())
    lc = leetcode_file(p)
    text = lc.read_text(encoding="utf-8")
    c = (folder / "build" / "solution.c").read_text(encoding="utf-8")
    lc.write_text(text[:text.index(BEGIN) + len(BEGIN)] + "\n" + c + "\n" + text[text.index(END):],
                  encoding="utf-8", newline="\n")


def cmd_start(problems, args):
    start(find(problems, args.problem))


def cmd_test(problems, args):
    p = find(problems, args.problem)
    build(p)
    return 0 if "Accepted" in leetgo("test", str(p["id"])) else 1


def cmd_submit(problems, args):
    p = find(problems, args.problem)
    build(p)
    if "Accepted" not in leetgo("test", str(p["id"])):
        print("\nnot submitted: the examples fail")
        return 1
    if "Accepted" not in leetgo("submit", str(p["id"])):
        return 1
    progress = load_progress()
    progress.setdefault(p["slug"], {}).setdefault("solved", datetime.date.today().isoformat())
    save_progress(progress)
    return 0


def cmd_show(problems, args):
    p = find(problems, args.problem)
    statement = folder_of(p) / "README.md"
    if not statement.exists():
        statement = leetcode_file(p).with_suffix(".md")
    print(statement.read_text(encoding="utf-8"))


def matches(p, args, progress):
    if getattr(args, "difficulty", None) and p["difficulty"].lower() != args.difficulty:
        return False
    if getattr(args, "todo", False) and solved(progress, p):
        return False
    return True


def path_slugs(name):
    path = PATHS / f"{name}.txt"
    if not path.exists():
        sys.exit(f"no path named {name}; see {PATHS.relative_to(ROOT)}{os.sep}")
    return [line.split("#")[0].strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.split("#")[0].strip()]


def on_path(problems, name):
    by_slug = {p["slug"]: p for p in problems}
    return [by_slug[s] for s in path_slugs(name) if s in by_slug]


def cmd_list(problems, args):
    progress = load_progress()
    pool = on_path(problems, args.path) if args.path else problems
    shown = 0
    for p in pool:
        if not matches(p, args, progress):
            continue
        mark = "x" if solved(progress, p) else ("." if folder_of(p).exists() else " ")
        paid = "$" if p["paid"] else " "
        print(f"[{mark}] {p['id']:4d} {paid} {p['difficulty']:6}  {p['title']}")
        shown += 1
        if args.limit and shown >= args.limit:
            break


def cmd_random(problems, args):
    progress = load_progress()
    pool = [p for p in problems if not p["paid"] and matches(p, args, progress) and not solved(progress, p)]
    if not pool:
        print("nothing left to pick with those filters")
        return 1
    start(random.choice(pool))


def cmd_next(problems, args):
    progress = load_progress()
    pool = [p for p in on_path(problems, args.path) if not p["paid"] and not solved(progress, p)]
    if not pool:
        print(f"every free problem on {args.path} is solved")
        return 0
    start(pool[0])


def cmd_stats(problems, args):
    progress = load_progress()
    for d in DIFFICULTIES:
        pool = [p for p in problems if p["difficulty"] == d and not p["paid"]]
        print(f"{d:6}  {sum(solved(progress, p) for p in pool):4} / {len(pool)}")
    for path in sorted(PATHS.glob("*.txt")):
        pool = on_path(problems, path.stem)
        print(f"path {path.stem}: {sum(solved(progress, p) for p in pool)} / {len(pool)}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # leetgo prints ● and ✔
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    for name, fn in (("start", cmd_start), ("test", cmd_test), ("submit", cmd_submit), ("show", cmd_show)):
        s = sub.add_parser(name)
        s.add_argument("problem", help="number, slug, or folder")
        s.set_defaults(fn=fn)

    for name, fn in (("list", cmd_list), ("random", cmd_random)):
        s = sub.add_parser(name)
        s.add_argument("-d", "--difficulty", choices=[d.lower() for d in DIFFICULTIES])
        if name == "list":
            s.add_argument("--todo", action="store_true", help="hide solved problems")
            s.add_argument("--path", help="only the problems on a path, in its order")
            s.add_argument("-n", "--limit", type=int)
        s.set_defaults(fn=fn)

    s = sub.add_parser("next")
    s.add_argument("--path", default="blind75")
    s.set_defaults(fn=cmd_next)

    s = sub.add_parser("stats")
    s.set_defaults(fn=cmd_stats)

    args = parser.parse_args()
    sys.exit(args.fn(load_problems(), args) or 0)


if __name__ == "__main__":
    main()
