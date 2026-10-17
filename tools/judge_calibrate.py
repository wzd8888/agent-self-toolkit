#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判官校准尺 · judge_calibrate.py
================================
来源：吸收 github/awesome-copilot `skills/phoenix-evals`（reference: validation.md /
      fundamentals-anti-patterns.md）= 我方 D5-2 批次最值钱机制。
用途：**凡由"判官"出分时（AI 判官 / 自评 / 评估脚本 / 验收器）上线前，先对人类金标算这道尺。**
      已焊进 `memory/复盘流程_定式_v1.md` §七「判官校准闸」。

口径（validation.md）：
  - 金标 ≥100 例、~50/50 平衡；
  - 目标 accuracy > 0.80 **且 TPR/TNR 双 > 0.70**（只看准确率会被类别不平衡骗 = TNR 陷阱）；
  - 二元(0/1)优于 Likert；
  - 能力类评估保持 ~50–80% 通过（100% = 无信号）；
  - LLM 判官逐跑有噪声 → repetitions 取多数票（平票保守取 0）。

用法：
  python3 tools/judge_calibrate.py --self-test
  python3 tools/judge_calibrate.py --human gold.txt --judge judge.txt   # 每行一个 0/1
  python3 tools/judge_calibrate.py --demo
  python3 tools/judge_calibrate.py --human gold.txt --judge judge.txt [--min-n 100]   # 前置门：n 不足或类别失衡 → 一律不放行（--min-n 可调）
退出码：0 = 通过（或自检/demo 成功）；3 = 判官未过闸（别上线）；1 = 断言失败；2 = 用法错。
纯 stdlib · 纯离线 · 不联网。
"""
import sys


def confusion(human, judge):
    """human/judge 等长 0/1 序列（1=pass）。返回 tp, tn, fp, fn。"""
    assert len(human) == len(judge), "human/judge 长度必须一致"
    tp = tn = fp = fn = 0
    for h, j in zip(human, judge):
        if h == 1 and j == 1:
            tp += 1
        elif h == 0 and j == 0:
            tn += 1
        elif h == 0 and j == 1:
            fp += 1
        else:
            fn += 1
    return tp, tn, fp, fn


def _wilson(p, n, z=1.96):
    """二项比例的 Wilson 95% 置信区间（小样本比正态近似稳）。"""
    if n == 0:
        return (0.0, 1.0)
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return ((c - h) / d, (c + h) / d)


def gate_precheck(n, pos, min_n=100, pos_lo=0.40, pos_hi=0.60):
    """P-14 前置硬门：金标规模/平衡不达标 → 不给出「放行」结论。返回 (ok, reasons)。"""
    reasons = []
    if n < min_n:
        reasons.append("金标样本 n=%d < 门槛 %d（结论不可信）" % (n, min_n))
    if n > 0:
        pr = pos / n
        if not (pos_lo <= pr <= pos_hi):
            reasons.append("正类占比 %.2f 越界 [%.2f, %.2f]（不平衡会被准确率骗）" % (pr, pos_lo, pos_hi))
    return (len(reasons) == 0), reasons


def validate_judge(human, judge, acc_min=0.80, tpr_min=0.70, tnr_min=0.70,
                   min_n=100, pos_lo=0.40, pos_hi=0.60):
    tp, tn, fp, fn = confusion(human, judge)
    n = tp + tn + fp + fn
    acc = (tp + tn) / n if n else 0.0
    tpr = tp / (tp + fn) if (tp + fn) else 0.0     # Recall / Sensitivity
    tnr = tn / (tn + fp) if (tn + fp) else 0.0     # Specificity
    po = (tp + tn) / n if n else 0.0
    pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (n * n) if n else 0.0
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    pos = tp + fn
    gate_ok, gate_reasons = gate_precheck(n, pos, min_n, pos_lo, pos_hi)
    return {
        "n": n, "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "accuracy": acc, "tpr": tpr, "tnr": tnr, "kappa": kappa,
        "acc_ci": _wilson(acc, n), "pos_rate": (pos / n if n else 0.0),
        "gate_ok": gate_ok, "gate_reasons": gate_reasons,
        # P-14：前置不达标 → 即便指标好看也一律不放行
        "deploy_ok": (gate_ok and acc > acc_min and tpr > tpr_min and tnr > tnr_min),
    }


def majority_vote(votes):
    """每次重复的 0/1 → 多数票；平票向 0（保守：不放行）。"""
    return 1 if sum(votes) * 2 > len(votes) else 0


def saturation_guard(pass_rate, lo=0.50, hi=0.80):
    """能力类评估应落 ~50–80%；100% 通过 = 无信号。"""
    return lo <= pass_rate <= hi


def similarity_for_generation_guard(metric):
    """BERTScore/ROUGE/BLEU/METEOR 只可测检索，不可测生成质量。"""
    return metric.lower() not in {"bertscore", "rouge", "bleu", "meteor"}


def _report(r):
    print("== 判官校准尺 ==")
    print("  样本 n=%d  (tp=%d tn=%d fp=%d fn=%d · 正类占比 %.2f)" % (
        r["n"], r["tp"], r["tn"], r["fp"], r["fn"], r.get("pos_rate", 0.0)))
    print("  accuracy = %.3f  (95%% CI %.3f–%.3f)  [门槛 >0.80]" % (r["accuracy"], r["acc_ci"][0], r["acc_ci"][1]))
    print("  TPR      = %.3f   [门槛 >0.70]" % r["tpr"])
    print("  TNR      = %.3f   [门槛 >0.70]  ← 单看准确率会被类别不平衡骗" % r["tnr"])
    print("  kappa    = %.3f" % r["kappa"])
    if not r.get("gate_ok", True):
        print("  前置门   = ❌ 未达标（P-14 硬门）:")
        for why in r.get("gate_reasons", []):
            print("             - " + why)
    else:
        print("  前置门   = ✅ 达标（n 足够 · 类别平衡）")
    print("  判定     = %s" % ("✅ 放行（可上线）" if r["deploy_ok"] else "❌ 未过闸（先别上线）"))
    return 0 if r["deploy_ok"] else 3


def _load01(path):
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip().replace(",", " ")
            for tok in ln.split():
                if tok == "":
                    continue
                out.append(1 if tok in ("1", "true", "True", "pass", "yes") else 0)
    return out


def _self_test():
    ok = 0
    human = [1] * 50 + [0] * 50
    judge = human.copy()
    for i in range(5):
        judge[i] = 0
    for i in range(50, 55):
        judge[i] = 1
    r = validate_judge(human, judge)
    assert (r["tp"], r["tn"], r["fp"], r["fn"]) == (45, 45, 5, 5), r
    assert abs(r["accuracy"] - 0.90) < 1e-9, r
    assert abs(r["tpr"] - 0.90) < 1e-9 and abs(r["tnr"] - 0.90) < 1e-9, r
    assert abs(r["kappa"] - 0.80) < 1e-9, r
    assert r["deploy_ok"] is True, r
    ok += 1

    bad = [1] * 50 + [0] * 50
    bad_judge = ([1] * 25 + [0] * 25) + ([1] * 25 + [0] * 25)
    rb = validate_judge(bad, bad_judge)
    assert rb["tpr"] == 0.5 and rb["tnr"] == 0.5 and rb["deploy_ok"] is False, rb
    ok += 1

    h3 = [1] * 20 + [0] * 80
    j3 = [1] * 20 + [1] * 28 + [0] * 52
    r3 = validate_judge(h3, j3)
    assert abs(r3["tpr"] - 1.0) < 1e-9 and r3["tnr"] < 0.70 and r3["deploy_ok"] is False, r3
    ok += 1

    assert majority_vote([1, 1, 0]) == 1 and majority_vote([1, 0, 0]) == 0
    assert majority_vote([1, 0]) == 0, "平票保守取 0"
    ok += 1

    assert saturation_guard(0.65) is True
    assert saturation_guard(1.00) is False and saturation_guard(0.20) is False
    ok += 1

    assert similarity_for_generation_guard("bertscore") is False
    assert similarity_for_generation_guard("rouge") is False
    assert similarity_for_generation_guard("fact_faithfulness") is True
    ok += 1

    # P-14 前置硬门 + P-12 证据链（Wilson CI）
    small = [1] * 25 + [0] * 25
    rs = validate_judge(small, small)
    assert rs["gate_ok"] is False and rs["deploy_ok"] is False, "n<100 应触发前置门且不放行"
    rb2 = validate_judge([1] * 20 + [0] * 80, [1] * 20 + [0] * 80)
    assert rb2["gate_ok"] is False, "类别失衡应触发前置门"
    r_ok = validate_judge(human, judge)
    assert r_ok["gate_ok"] is True and r_ok["deploy_ok"] is True
    assert 0.0 <= r_ok["acc_ci"][0] <= r_ok["accuracy"] <= r_ok["acc_ci"][1] <= 1.0
    ok += 1

    print("OK · judge_calibrate self-test passed · %d 组断言" % ok)
    return 0


def main(argv):
    if "--self-test" in argv:
        return _self_test()
    if "--demo" in argv:
        human = [1] * 50 + [0] * 50
        judge = human.copy()
        for i in range(5):
            judge[i] = 0
        for i in range(50, 55):
            judge[i] = 1
        return _report(validate_judge(human, judge))
    if "--human" in argv and "--judge" in argv:
        human = _load01(argv[argv.index("--human") + 1])
        judge = _load01(argv[argv.index("--judge") + 1])
        # P-14 前置硬门：输入形状不对 → 干净 HALT（exit 2），不裸抛
        if not human or not judge:
            sys.stderr.write("错误：输入为空（human=%d judge=%d）\n" % (len(human), len(judge)))
            return 2
        if len(human) != len(judge):
            sys.stderr.write("错误：human/judge 行数不一致（%d vs %d）\n" % (len(human), len(judge)))
            return 2
        min_n = int(argv[argv.index("--min-n") + 1]) if "--min-n" in argv else 100
        return _report(validate_judge(human, judge, min_n=min_n))
    print("usage: python3 tools/judge_calibrate.py --self-test | --demo | --human gold.txt --judge judge.txt")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
