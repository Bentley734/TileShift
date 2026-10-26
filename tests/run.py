"""Run the ROM-free TileShift Lua fixture suites in independent Lua states."""
from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tests", nargs="*", help="Optional *_test.lua filenames")
    parser.add_argument(
        "--runtime", action="append", choices=("lua51", "lua53", "luajit21"),
        help="Runtime to run; repeat as needed. Defaults to every available runtime.",
    )
    parser.add_argument(
        "--lupa-path", type=Path, default=root.parent / ".tools" / "python",
        help="Directory containing the local lupa package.",
    )
    args = parser.parse_args()
    if args.lupa_path.is_dir():
        sys.path.insert(0, str(args.lupa_path.resolve()))
    paths = [root / "tests" / name for name in args.tests] if args.tests else sorted(
        (root / "tests").glob("*_test.lua")
    )
    if not paths:
        parser.error("No *_test.lua suites found")
    for path in paths:
        if not path.is_file() or not path.name.endswith("_test.lua"):
            parser.error(f"Not a Lua fixture suite: {path}")

    failed, ran, skipped = [], 0, []
    for flavor in args.runtime or ("lua51", "lua53", "luajit21"):
        try:
            runtime = importlib.import_module("lupa." + flavor).LuaRuntime
        except ImportError as exc:
            if args.runtime:
                failed.append((flavor, "runtime unavailable"))
                print(f"FAIL {flavor}: {exc}", flush=True)
            else:
                skipped.append(flavor)
                print(f"SKIP {flavor}: unavailable", flush=True)
            continue
        for path in paths:
            lua = runtime(unpack_returned_tuples=True)
            lua.globals().arg = lua.table_from({1: root.as_posix()})
            try:
                lua.execute("assert(loadfile(...))()", path.resolve().as_posix())
                print(f"PASS {flavor} {path.name}", flush=True)
            except Exception as exc:
                failed.append((flavor, path.name))
                print(f"FAIL {flavor} {path.name}: {exc}", flush=True)
            ran += 1
    if ran == 0:
        print("No Lua suites ran; install Lupa or pass --lupa-path.", flush=True)
        return 1
    print(f"Ran {ran} suites; {len(failed)} failures; {len(skipped)} runtimes skipped.", flush=True)
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
