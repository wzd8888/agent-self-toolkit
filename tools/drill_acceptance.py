#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""drill_acceptance.py — 演练场 · L1「可运行闸」（自动验收 第一级）

把一件"演练交付物"自动判 PASS/FAIL：① 文件齐不齐 ② 冒烟能不能跑通(exit=0)。
L2「质量闸」(评测集 + 评分器)另由 judge_calibrate.py 承担。

用法:
  python3 tools/drill_acceptance.py --spec tools/drill/<x>.json
  python3 tools/drill_acceptance.py --dir <交付目录> --cmd "python3 demo.py" \
      --require README.md,main.py [--expect-exit 0] [--timeout 30] [--json 报告.json]
  python3 tools/drill_acceptance.py --self-test

spec.json 字段: {"name","dir","cmd","expect_exit"(默认0),"require":[],"readme"(bool),"timeout"(默认30)}
退出码: 0=PASS  3=FAIL  2=用法/自检错
"""
import argparse, json, os, subprocess, sys, tempfile, shutil, time


def check(spec):
    res = {"name": spec.get("name", "<unnamed>"), "checks": [], "pass": True}

    def add(name, ok, detail=""):
        res["checks"].append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            res["pass"] = False

    d = spec.get("dir")
    if not d or not os.path.isdir(d):
        add("dir_exists", False, "交付目录不存在: %s" % d)
        return res
    add("dir_exists", True, d)

    for f in spec.get("require", []) or []:
        p = os.path.join(d, f)
        add("file:%s" % f, os.path.isfile(p) or os.path.isdir(p), p)

    if spec.get("readme"):
        ok = any(os.path.isfile(os.path.join(d, n))
                 for n in ("README.md", "README", "readme.md", "readme.txt"))
        add("readme", ok, "需 README/部署说明")

    cmd = spec.get("cmd")
    if cmd:
        exp = int(spec.get("expect_exit", 0))
        to = int(spec.get("timeout", 30))
        t0 = time.time()
        try:
            p = subprocess.run(cmd, shell=True, cwd=d, capture_output=True,
                               text=True, timeout=to)
            rc = p.returncode
            ok = (rc == exp)
            det = "exit=%d (期望%d) %.1fs" % (rc, exp, time.time() - t0)
            if not ok:
                det += " | stderr: " + (p.stderr or "")[-200:].replace("\n", " ")
            add("smoke_exit", ok, det)
        except subprocess.TimeoutExpired:
            add("smoke_exit", False, "超时 >%ds" % to)
        except Exception as e:  # noqa
            add("smoke_exit", False, "执行异常: %s" % e)
    return res


def run_self_test():
    tmp = tempfile.mkdtemp(prefix="drill_selftest_")
    try:
        good = os.path.join(tmp, "good"); os.makedirs(good)
        open(os.path.join(good, "main.py"), "w").write("print('ok')\n")
        open(os.path.join(good, "README.md"), "w").write("# demo\n")
        sg = {"name": "good", "dir": good, "cmd": "python3 main.py",
              "require": ["main.py"], "readme": True, "timeout": 10}
        r1 = check(sg)

        bad = os.path.join(tmp, "bad"); os.makedirs(bad)
        open(os.path.join(bad, "main.py"), "w").write("import sys; sys.exit(1)\n")
        sb = {"name": "bad", "dir": bad, "cmd": "python3 main.py",
              "require": ["main.py", "missing.py"], "readme": True, "timeout": 10}
        r2 = check(sb)

        ok = (r1["pass"] is True) and (r2["pass"] is False)
        print("self-test good =>", "PASS" if r1["pass"] else "FAIL", "(期望 PASS)")
        print("self-test bad  =>", "PASS" if r2["pass"] else "FAIL", "(期望 FAIL)")
        if not ok:
            print("SELF-TEST FAILED"); return 2
        print("SELF-TEST OK"); return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec"); ap.add_argument("--dir"); ap.add_argument("--cmd")
    ap.add_argument("--require", default="")
    ap.add_argument("--readme", dest="readme", action="store_true", default=True,
                    help="要求目录含 README（默认开）")
    ap.add_argument("--no-readme", dest="readme", action="store_false",
                    help="不校验 README（对 memory/ 等非交付目录用）")
    ap.add_argument("--expect-exit", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--json"); ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return run_self_test()
    if a.spec:
        spec = json.load(open(a.spec, encoding="utf-8"))
    elif a.dir:
        spec = {"name": os.path.basename(os.path.abspath(a.dir)), "dir": a.dir,
                "cmd": a.cmd, "require": [x for x in a.require.split(",") if x],
                "readme": a.readme, "expect_exit": a.expect_exit, "timeout": a.timeout}
    else:
        ap.print_usage(); return 2
    res = check(spec)
    print("# 演练验收 L1 · %s => %s" % (res["name"], "PASS ✅" if res["pass"] else "FAIL ❌"))
    for c in res["checks"]:
        print("  [%s] %s  %s" % ("✅" if c["ok"] else "❌", c["check"], c["detail"]))
    if a.json:
        open(a.json, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=2))
        print("# 报告: %s" % a.json)
    return 0 if res["pass"] else 3


if __name__ == "__main__":
    sys.exit(main())
