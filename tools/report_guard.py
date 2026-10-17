#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report_guard.py — 汇报出口自检器（谎报军情 · 防呆闸）

用途：任何要发出去的**汇报草稿**，发送前过一遍——
  1. 逐条列出草稿里的**数字/规格宣称**（核/内存/G/元/%/版本/时长/条/批…）→ 逼自己逐条标源或当场取证。
  2. 揪出**软词禁区**（好像/大概/估计/应该/差不多/印象里/记得是…）→ 报道里出现 = 硬红旗。
  3. 揪出**未标定性的断言**（"Done/完成/已修/全绿/清零/通过" 等）→ 提示：无证据不算，须附 exit/日志/链接。

读法（军法级·宁可少报不可假报）：
  - 凡报数字/规格 → **先跑命令拿真值 → 只从输出抄**，禁凭记忆。
  - 没验证的结论不许当结论报；推断标「推断/待核实」。
  - 软词（好像/大概）**不准入汇报**。

用法：
  python3 tools/report_guard.py "草稿文本"
  echo "草稿" | python3 tools/report_guard.py -
  python3 tools/report_guard.py --file draft.md
  python3 tools/report_guard.py --self-test

退出码：0 = 无红旗（可发）｜3 = 命中软词/未定性断言（须先处置再发）
"""
import re
import sys

UNITS = ("核|GB|MB|KB|TB|GHz|MHz|G|元|¥|%|％|ms|s|分钟|小时|天|周|月|年|"
         "条|个|批|卡|行|次|人|台|份|处|项|版|步|级|档|倍|万|亿|核|张|字|词")

NUM_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(\s*(?:" + UNITS + r"))?")

SOFT_WORDS = ["好像", "大概", "大约", "似乎", "估计", "差不多", "应该是", "应该是吧",
              "可能就是", "貌似", "印象里", "印象中", "我记得", "记得是", "应该没问题",
              "八成", "或许", "没准", "可能吧", "说不准",
              # English hedges (case-insensitive match applied below)
              "probably", "maybe", "perhaps", "seems", "seem to", "i think",
              "i guess", "should be", "more or less", "sort of", "kind of", "presumably"]

# Hedges that only count when glued to a number ("about 2G"), not in normal prose.
HEDGE_NUM_RE = re.compile(r"\b(about|around|approximately|roughly|some|circa)\s+(?=\d)", re.I)

# 定性断言（需证据支撑）
ASSERT_WORDS = ["Done", "done", "完成", "已修", "修好", "修完", "全绿", "清零",
                "通过", "搞定", "OK", "ok", "PASS", "FAIL", "已闭环", "结案", "已解决", "没问题"]

# 有明显来源标记的豁免（同行出现下列词，视为已标源/已取证）
SOURCE_MARK = ["实测", "取证", "来源", "Source", "exit", "exit=", "nproc", "wc -l",
               "命令", "输出", "日志", "#L", "card", "regression", "回归", "self-test",
               "自检", "口报", "已核", "核对", "run ", "跑了", "查了"]


def scan(text: str):
    nums, softs, asserts = [], [], []
    for m in NUM_RE.finditer(text):
        unit = (m.group(2) or "").strip()
        nums.append((m.group(0).strip(), unit))
    low = text.lower()
    for m in HEDGE_NUM_RE.finditer(text):
        softs.append(m.group(0).strip())
    for w in SOFT_WORDS:
        if w.isascii():
            for m in re.finditer(r"\b" + re.escape(w) + r"\b", low):
                softs.append(text[m.start():m.end()].strip())
            continue
        if w in text:
            softs.append(w)
    for w in ASSERT_WORDS:
        if w in text:
            asserts.append(w)
    has_source = any(s in text for s in SOURCE_MARK)
    return nums, softs, asserts, has_source


def report(text: str):
    nums, softs, asserts, has_source = scan(text)
    print("=" * 56)
    print("汇报出口自检 · report_guard")
    print("=" * 56)
    print(f"\n① 数字/规格宣称（{len(nums)} 条）——逐条问：『实测了吗？源在哪？』")
    if nums:
        for i, (tok, unit) in enumerate(nums, 1):
            tag = "⚙规格" if unit else "数"
            print(f"   {i:>2}. {tok:<14} [{tag}]")
    else:
        print("   （无）")
    print(f"\n② 软词禁区（{len(softs)} 处）——报道里出现 = 红旗，删掉或改成确定值：")
    print("   " + ("，".join(softs) if softs else "（无 ✅）"))
    print(f"\n③ 定性断言（{len(asserts)} 处）——每处须挂证据（exit/日志/链接），否则改『推断/待核实』：")
    print("   " + ("，".join(asserts) if asserts else "（无）"))
    print(f"\n④ 源标记：{'✅ 检测到取证痕迹（' + ', '.join(s for s in SOURCE_MARK if s in text) + '）' if has_source else '⚠️ 未检测到任何源/取证痕迹'}")
    print("\n" + "-" * 56)
    red = bool(softs) or (bool(asserts) and not has_source)
    if red:
        print("🔴 有红旗 → 先处置（删软词 / 给断言补证据 / 数字实测）再发。exit=3")
        return 3
    print("🟢 无红旗 → 可发。exit=0")
    return 0


def self_test():
    ok = True
    t1 = "网关内存实测 1.45G（brief_core 输出）· 核数 nproc=4"
    n, s, a, hs = scan(t1)
    if not (len(n) >= 2 and not s and hs):
        ok = False
        print("FAIL t1", n, s, hs)
    t2 = "大概是 8 核吧，负载应该没问题，已完成"
    n, s, a, hs = scan(t2)
    if not (s and a and not hs and len(n) >= 1):
        ok = False
        print("FAIL t2", s, a, hs, n)
    t3 = "D-C32 已 PASS（drill 18 项 exit=0）"
    n, s, a, hs = scan(t3)
    if not (a and hs):
        ok = False
        print("FAIL t3", a, hs)
    print("self-test:", "PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    if "--file" in argv:
        i = argv.index("--file")
        with open(argv[i + 1], "r", encoding="utf-8") as f:
            text = f.read()
    elif "-" in argv or not argv:
        text = sys.stdin.read()
    else:
        text = " ".join(argv)
    return report(text)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
