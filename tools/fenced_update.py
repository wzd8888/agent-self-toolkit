#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""围栏幂等更新器 · fenced_update.py
==================================
来源：吸收 github/awesome-copilot `skills/vardoger-analyze`（我方 D7-1 批次）。
用途：**任何自动写回我方文档**（蒸馏/复盘/Dreaming/总盘/索引 cron）——机器生成块放进
      围栏 `<!-- <token>:start --> … <!-- <token>:end -->`，写回**只替换围栏内**，
      **围栏外手写规矩原样保留**；同内容重写幂等（可安全重跑）；写前自动备份。
已焊进 `memory/复盘流程_定式_v1.md` §八「自动重写安全壳」。

写操作门禁（P-10 · 默认只读 → 差异预览 → 显式批准 → 回滚）：
  默认：只读——算好结果、打印「待写入」差异，**不落盘**（有变更则退出码 3 等批准）。
用法：
  python3 tools/fenced_update.py --self-test
  python3 tools/fenced_update.py --file <doc.md> --content <新内容.txt> [--token gen]     # 预览（只读）
  python3 tools/fenced_update.py --file <doc.md> --content <新内容.txt> --diff            # 打印 unified diff
  python3 tools/fenced_update.py --file <doc.md> --content <新内容.txt> --yes             # 显式批准 → 备份 .bak 后写入
  python3 tools/fenced_update.py --file <doc.md> --content <新内容.txt> --dry-run         # 打印完整结果（只读）
  echo "内容" | python3 tools/fenced_update.py --file <doc.md> --content - --diff
  python3 tools/fenced_update.py --file <doc.md> --restore                                # 从 .bak 回滚
退出码：0 成功/无变化/预览；1 断言失败；2 用法错；3 有变更但未给 --yes（未写·待批准）。
纯 stdlib · 纯离线。
"""
import argparse
import difflib
import shutil
import sys

START = "<!-- {token}:start -->"
END = "<!-- {token}:end -->"


def upsert_fenced(existing, content, token="gen"):
    """只替换围栏内内容；无围栏则追加；围栏外文本原样保留（保手工规则）。"""
    st, en = START.format(token=token), END.format(token=token)
    block = "%s\n%s\n%s" % (st, content.rstrip("\n"), en)
    si, ei = existing.find(st), existing.find(en)
    if si != -1 and ei != -1 and ei > si:
        return existing[:si] + block + existing[ei + len(en):]
    if existing.strip() == "":
        return block + "\n"
    return existing.rstrip("\n") + "\n\n" + block + "\n"


# ---------- 机制：长历史先分批（map → reduce） ----------
def chunk(items, size):
    """把长列表按 size 切批；size<=0 视为不切。"""
    if size <= 0:
        return [list(items)]
    return [list(items[i:i + size]) for i in range(0, len(items), size)]


def is_stale(state, now, ttl):
    """state 缺 last_run 或超出 ttl → 过期需刷新；否则新鲜可早退。"""
    last = state.get("last_run")
    if last is None:
        return True
    return (now - last) >= ttl


def make_diff(existing, new, path="<doc>"):
    """生成 existing→new 的 unified diff 文本（用于写前预览）。"""
    a = existing.splitlines(keepends=True)
    b = new.splitlines(keepends=True)
    return "".join(difflib.unified_diff(a, b, fromfile=path, tofile=path + " (new)", n=2))


def _self_test():
    tests = []

    def check(name, cond):
        tests.append((name, bool(cond)))

    hand = "# 我手写的规矩（人写部分）\n- 永远保留手写规则\n"
    g1 = upsert_fenced(hand, "- 偏好精简输出\n- 先验证再汇报")
    check("首写追加围栏", "<!-- gen:start -->" in g1 and "<!-- gen:end -->" in g1)
    check("首写保手工规则", "永远保留手写规则" in g1)
    g2 = upsert_fenced(g1, "- 偏好精简输出\n- 先验证再汇报")
    check("同内容重写=幂等", g2 == g1)
    g3 = upsert_fenced(g1, "- 只用中文")
    check("更新替换围栏内", "只用中文" in g3 and "先验证再汇报" not in g3)
    check("更新仍保手工规则", "永远保留手写规则" in g3)
    check("更新唯一围栏", g3.count("<!-- gen:start -->") == 1)
    check("空文件首写", upsert_fenced("", "X").startswith("<!-- gen:start -->"))
    check("围栏在文末后仍保留尾部", "尾注" in upsert_fenced("<!-- gen:start -->\nold\n<!-- gen:end -->\n\n尾注\n", "new"))

    check("chunk 覆盖全部条目", sum(len(b) for b in chunk(list(range(5)), 2)) == 5)
    check("chunk size<=0 不切", len(chunk([1, 2, 3], 0)) == 1)

    check("缺 last_run = 过期", is_stale({}, now=100, ttl=10) is True)
    check("未到 ttl = 新鲜", is_stale({"last_run": 95}, now=100, ttl=10) is False)
    check("到 ttl = 过期", is_stale({"last_run": 90}, now=100, ttl=10) is True)

    d = make_diff("a\nb\n", "a\nc\n", "x")
    check("diff 命中增删", "-b" in d and "+c" in d and d.startswith("---"))
    check("diff 无变化为空", make_diff("a\n", "a\n", "x") == "")

    passed = sum(1 for _, ok in tests if ok)
    for name, ok in tests:
        print(("  PASS " if ok else "  FAIL ") + name)
    print("\n%d/%d PASS" % (passed, len(tests)))
    return 0 if passed == len(tests) else 1


def main():
    ap = argparse.ArgumentParser(description="围栏幂等更新（只改围栏内·保手写·幂等·可回滚）")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--file", help="要更新的文档")
    ap.add_argument("--content", help="新内容文件，或 - 表示 stdin")
    ap.add_argument("--token", default="gen", help="围栏 token（默认 gen）")
    ap.add_argument("--diff", action="store_true", help="打印 unified diff（只读预览）")
    ap.add_argument("--dry-run", action="store_true", help="打印完整结果（只读预览）")
    ap.add_argument("--yes", action="store_true", help="显式批准写入（缺省=只读预览·不落盘）")
    ap.add_argument("--restore", action="store_true", help="从 <file>.bak 回滚")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(_self_test())
    if not args.file:
        ap.print_help()
        sys.exit(2)

    # 回滚（P-10 最后一环）
    if args.restore:
        bak = args.file + ".bak"
        try:
            shutil.copy2(bak, args.file)
        except FileNotFoundError:
            sys.stderr.write("restore 失败：无备份 %s\n" % bak)
            sys.exit(2)
        print("restored: %s <- %s" % (args.file, bak))
        sys.exit(0)

    if args.content is None:
        ap.print_help()
        sys.exit(2)

    if args.content == "-":
        content = sys.stdin.read()
    else:
        with open(args.content, "r", encoding="utf-8") as fh:
            content = fh.read()

    try:
        with open(args.file, "r", encoding="utf-8") as fh:
            existing = fh.read()
    except FileNotFoundError:
        existing = ""

    new = upsert_fenced(existing, content, token=args.token)

    # 无变化（幂等）→ 直接成功，不需批准
    if new == existing:
        print("no change: %s (幂等·未写)" % args.file)
        sys.exit(0)

    # 只读预览
    if args.dry_run:
        sys.stdout.write(new)
        sys.exit(0)
    if args.diff:
        d = make_diff(existing, new, args.file)
        sys.stdout.write(d if d.endswith("\n") or d == "" else d + "\n")
        sys.exit(0)

    # 门禁：未显式批准 → 不落盘
    if not args.yes:
        d = make_diff(existing, new, args.file)
        sys.stdout.write(d if d.endswith("\n") or d == "" else d + "\n")
        sys.stderr.write("\n[待批准] 有变更未写入。确认无误后加 --yes 落盘（写前自动备份 .bak）。\n")
        sys.exit(3)

    # 显式批准 → 备份 + 写
    if existing != "":
        shutil.copy2(args.file, args.file + ".bak")
    with open(args.file, "w", encoding="utf-8") as fh:
        fh.write(new)
    print("updated: %s (token=%s%s)" % (args.file, args.token, " · 备份 .bak" if existing != "" else ""))
    sys.exit(0)


if __name__ == "__main__":
    main()
