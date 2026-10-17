# agent-self-toolkit

Small, dependency-free tools for the boring part of autonomous agents: **guarding their own work**.

An agent that writes files, grades its own output, and reports status will drift — it deletes what it
should keep, scores itself too kindly, says "done" without evidence, and runs a destructive command
because it looked harmless. These seven single-file Python tools put a mechanical gate in front of
each of those four failure modes.

No dependencies. Python 3.8+. Every tool has `--self-test` and works standalone.

## The gates

| Gate | Tool | What it stops |
|---|---|---|
| **Write** | `tools/fenced_update.py` | Rewriting a whole document and losing hand-written rules. Updates only the fenced block, idempotently; dry-run by default, `--yes` writes, `--restore` rolls back. |
| **Quality** | `tools/judge_calibrate.py` | An LLM judge that was never checked against human labels. Compares judge vs gold, refuses to pass below 100 samples, reports Wilson 95% CI. |
| **Honesty** | `tools/report_guard.py` | Reports with unsourced numbers, hedge words ("probably", "seems"), or "done" with no evidence. |
| **Delivery** | `tools/drill_acceptance.py` | Shipping something that was never actually run. Checks files exist and a smoke command exits 0. |

## The small knives

| Tool | What it does |
|---|---|
| `tools/gate_cmd.py` | Classifies a shell command: `0` allow (read-only) · `1` review (mutating) · `2` block (irreversible). |
| `tools/md_toc.py` | Markdown outline / table-of-contents generator. |
| `tools/csv_md.py` | CSV/TSV → markdown table, with alignment options. |

## Quickstart

```sh
git clone https://github.com/<you>/agent-self-toolkit
cd agent-self-toolkit

# prove it works on your machine
sh tests/run_all.sh          # ALL PASS (7 tools)

# 1. safe doc update: only the fenced block changes
python3 tools/fenced_update.py --file RULES.md --content new_notes.txt        # preview, read-only
python3 tools/fenced_update.py --file RULES.md --content new_notes.txt --diff # see the diff
python3 tools/fenced_update.py --file RULES.md --content new_notes.txt --yes  # write (+ .bak)

# 2. check a judge before you trust it (one 0/1 per line, human file vs judge file)
python3 tools/judge_calibrate.py --human gold.txt --judge judge.txt --min-n 100

# 3. audit a report before sending it
echo "Fixed it, memory is now about 2G, should be fine." | python3 tools/report_guard.py -

# 4. accept a delivery only if it actually runs
python3 tools/drill_acceptance.py --dir ./dist --cmd "python3 -m package --version" --require README.md,pyproject.toml

# 5. before running a generated command
python3 tools/gate_cmd.py "rm -rf /var/tmp/build"
```

Every tool exits `0` on pass and non-zero on refusal, so they compose in CI or in an agent loop.

## Design choices

- **Fail closed, stay quiet when green.** Gates return non-zero on refusal and print nothing alarming
  when there is nothing wrong — an agent should be able to call them every turn.
- **Read-only by default.** Anything that writes needs an explicit flag and leaves a backup.
- **Self-testing.** Each tool carries its own assertions, including negative cases (a gate that never
  rejects anything is decoration, not a gate).
- **Single file, stdlib only.** Copy one file into your project and it works.

## Limits

- These are *process* guards, not correctness proofs. `drill_acceptance` checks that a command ran and
  exited 0 — not that the output is right.
- `judge_calibrate` needs human-labeled data; without it, it will refuse to pass (by design).
- `report_guard` is a linter for language, not a fact-checker. It flags claims that need a source; you
  still have to supply the source.

## License

MIT — see [LICENSE](LICENSE).

---

[中文说明](README.zh-CN.md)
