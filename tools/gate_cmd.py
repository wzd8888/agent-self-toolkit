#!/usr/bin/env python3
"""gate_cmd.py — 命令三分类闸（焊自 Codex execpolicy + awesome-copilot aws-resource-query 只读白/黑名单）。

用途：跑 shell 前自查 / 可接 guard 脚本；把「只读=放行 · 变更=复核 · 不可逆=拦」机器化。
用法：
    python3 tools/gate_cmd.py "ls -la"
    echo "rm -rf /tmp/x" | python3 tools/gate_cmd.py -
退出码：0=ALLOW（只读·放行）· 1=REVIEW（变更·先取证/复核）· 2=BLOCK（不可逆/红线·拦）
纯离线·无依赖。活的·可更正。
"""
import re
import sys

# 只读命令白名单（首词）——命中即倾向放行
READONLY = {
    "ls", "cat", "head", "tail", "wc", "grep", "rg", "find", "fd", "pgrep", "ps",
    "pwd", "echo", "printf", "which", "command", "type", "stat", "du", "df", "file",
    "tree", "sort", "uniq", "cut", "tr", "date", "env", "printenv", "id", "whoami",
    "uptime", "free", "uname", "hostname", "readlink", "realpath", "basename", "dirname",
    "sed", "awk", "diff", "cmp", "md5sum", "sha256sum", "jq", "column", "less", "more",
}

# 红线：任何情况直接拦（BLOCK）
NEVER = [
    (r"\brm\s+-[a-z]*r[a-z]*f?\b.*\s/(\s|$)", "rm -rf /"),
    (r"\brm\s+-rf\s+/(\s|$)", "rm -rf /"),
    (r"\bmkfs(\.\w+)?\b", "格式化磁盘 mkfs"),
    (r"\bdd\b.*\bof=/dev/(sd|nvme|hd|vd)", "dd 写裸盘"),
    (r">\s*/dev/(sd|nvme|hd|vd)", "重定向写裸盘"),
    (r":\(\)\s*\{.*\};\s*:", "fork 炸弹"),
    (r"\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(ba)?sh\b", "curl/wget 管道进 shell"),
    (r"\bchmod\s+-R\s+777\s+/(\s|$)", "chmod -R 777 /"),
    (r"\bgit\s+push\b.*--force\b", "git push --force"),
    (r"\b(shutdown|reboot|halt|poweroff)\b", "关机/重启"),
]

# 需复核：变更类（REVIEW）
REVIEW = [
    (r"\bsed\b\s+-i", "sed -i 原地改文件"),
    (r"\bawk\b.*-i\s+inplace", "awk 原地改文件"),
    (r"\brm\b", "删文件 rm"),
    (r"\bmv\b", "移动/改名 mv"),
    (r"\bcp\b", "复制 cp"),
    (r"\b(pkill|kill|killall)\b", "杀进程（先 pgrep 取证）"),
    (r"\bchmod\b|\bchown\b", "改权限/属主"),
    (r"\b(sudo|doas)\b", "提权"),
    (r"\b(apt|apt-get|pip|pip3|npm|pnpm|yarn|cargo)\s+(install|add|i)\b", "装包"),
    (r"\bgit\s+(push|reset|clean|checkout|rebase)\b", "git 写操作"),
    (r"\bmkdir\b|\brmdir\b|\btouch\b|\btruncate\b", "建/删目录或文件"),
    (r"\b>\s*[^&|]", "重定向写文件"),
    (r"\bsystemctl\b|\bservice\b", "服务操作"),
    (r"\bcurl\b|\bwget\b|\bnc\b|\bssh\b|\bscp\b|\brsync\b", "网络/远程"),
    (r"\b(python3?|node|bash|sh|perl)\b\s+-[ce]", "内联执行代码"),
    (r"\b(crontab|at)\b", "定时任务"),
    (r"\bdocker\b|\bkubectl\b", "容器/集群"),
]


def classify(cmd: str):
    c = " ".join(cmd.split())
    for pat, why in NEVER:
        if re.search(pat, c):
            return 2, "BLOCK", f"红线：{why}"
    # 管道/子命令拆开逐段查（只读整条才放行）
    segs = re.split(r"[|;&]+", c)
    for s in segs:
        for pat, why in REVIEW:
            if re.search(pat, s):
                return 1, "REVIEW", f"变更操作：{why}"
    first = ""
    m = re.match(r"^\s*([a-zA-Z0-9_.\-]+)", c)
    if m:
        first = m.group(1)
    if first in READONLY or " " not in c:
        return 0, "ALLOW", f"只读命令（{first or c}）"
    return 1, "REVIEW", f"命令不在只读白名单（{first}）→ 按变更对待"


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 1
    if a[0] == "-":
        cmd = sys.stdin.read()
    else:
        cmd = " ".join(a)
    code, verdict, why = classify(cmd)
    icon = {0: "✅", 1: "🟡", 2: "⛔"}[code]
    print(f"{icon} {verdict} · {why}")
    print(f"   命令: {cmd.strip()[:200]}")
    return code


if __name__ == "__main__":
    sys.exit(main())
