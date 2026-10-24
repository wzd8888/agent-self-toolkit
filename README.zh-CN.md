# agent-self-toolkit · Agent 自管理工具箱

[![tests](https://github.com/wzd8888/agent-self-toolkit/actions/workflows/tests.yml/badge.svg)](https://github.com/wzd8888/agent-self-toolkit/actions/workflows/tests.yml)

七个零依赖的小工具，专门拦「智能体自己坑自己」的四类毛病：**改坏文件、给自己放水、没证据就说完成、手滑跑危险命令**。

纯标准库 · 单文件可拷走 · 每个都带 `--self-test` · Python 3.8+。

## 四道闸

| 闸 | 工具 | 拦什么 |
|---|---|---|
| **写入** | `tools/fenced_update.py` | 整篇重写把**人手写的规则**冲掉。只改围栏内、幂等；默认只预览，`--yes` 才落盘（留 `.bak`），`--restore` 可回滚。 |
| **质量** | `tools/judge_calibrate.py` | 判官（AI 评分）没对过金标就用。与人工标注逐条比对，**样本 < 100 一律不放行**，输出 Wilson 95% 置信区间。 |
| **诚实** | `tools/report_guard.py` | 汇报里**没有出处的数字**、含糊词（好像/大概/估计）、以及无证据的「已完成/全绿」。 |
| **交付** | `tools/drill_acceptance.py` | 没真跑过就交付。按清单查文件齐不齐 + 冒烟命令 exit 是否为 0，判 PASS/FAIL。 |

## 三把小刀

| 工具 | 作用 |
|---|---|
| `tools/gate_cmd.py` | 命令三分类：`0` 放行（只读）· `1` 复核（变更）· `2` 拦截（不可逆）。 |
| `tools/md_toc.py` | Markdown 大纲 / 目录生成。 |
| `tools/csv_md.py` | CSV/TSV → Markdown 表格，支持对齐等选项。 |

## 快速上手

```sh
git clone https://github.com/<you>/agent-self-toolkit
cd agent-self-toolkit

sh tests/run_all.sh                    # 全绿: ALL PASS (7 tools)

# 1. 安全改文档：只替换围栏内，手写部分不动
python3 tools/fenced_update.py --file RULES.md --content new.txt          # 预览（只读）
python3 tools/fenced_update.py --file RULES.md --content new.txt --diff   # 看差异
python3 tools/fenced_update.py --file RULES.md --content new.txt --yes    # 落盘 + 备份

# 2. 信任判官之前先校准（每行 0/1；人工一份，判官一份）
python3 tools/judge_calibrate.py --human gold.txt --judge judge.txt --min-n 100

# 3. 汇报发出前自查
echo "修好了，内存大概 2G，应该没问题。" | python3 tools/report_guard.py -

# 4. 只有真跑通才算验收
python3 tools/drill_acceptance.py --dir ./dist --cmd "python3 -m pkg --version" --require README.md,pyproject.toml

# 5. 跑生成的命令前先过闸
python3 tools/gate_cmd.py "rm -rf /var/tmp/build"
```

所有工具都是**成功 exit 0、拒绝时非 0**，可直接嵌进 CI 或智能体回合循环。

## 设计取舍

- **失败就拒绝，通过就安静**：拒绝时非 0，没问题时不刷屏 —— 智能体每回合调用也不吵。
- **默认只读**：任何写操作都要显式开关，且留备份。
- **自带自测**：每个工具都内含断言，**含负例**（从不拒绝任何东西的闸，是装饰）。
- **单文件 + 纯 stdlib**：拷一个文件进项目就能用。

## 边界（说清楚）

- 这些是**流程闸**，不是正确性证明：`drill_acceptance` 只保证「命令跑过且 exit 0」，不保证结果对。
- `judge_calibrate` 需要人工标注数据；没有它就拒绝放行（这是设计）。
- `report_guard` 查的是**语言**，不是事实：它标出「该给出处的句子」，出处仍要你补。

## 许可

MIT，见 [LICENSE](LICENSE)。

---

[English](README.md)
