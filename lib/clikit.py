"""clikit — shared chrome for the CLITOOLS suite.

SKILLER and PROMPTER each grew their own copy of the same ~250 lines of
terminal framing, color, config resolution and GLM streaming. SALVAGER,
KEYRING and RECALLER would have made five copies. This module is that
code, extracted once, so a fix to the frame renderer or the shared-config
search path lands in every tool at the same time.

Zero dependencies, stdlib only, same as everything else here.

Config resolution (machine-wide install, see install-global.sh):
    QGLM_API_KEY env  >  ~/.qglm.yaml  >  /usr/local/share/qglm/.qglm.yaml
so any account on this host works without its own setup.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request

HOME = os.path.expanduser("~")

# Machine-wide config, seeded by install-global.sh. Overridable for tests.
SHARED_QGLM_DIR = os.environ.get("QGLM_SHARED_DIR", "/usr/local/share/qglm")

DEFAULT_ENDPOINT = "https://api.z.ai/api/coding/paas/v4/chat/completions"
DEFAULT_MODEL = "glm-4.7-flash"


# ---------------------------------------------------------------- color

def _tty() -> bool:
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


class C:
    on = _tty()

    @classmethod
    def _c(cls, code: str, s: str) -> str:
        return f"\033[{code}m{s}\033[0m" if cls.on else s

    @classmethod
    def frame(cls, s):  return cls._c("38;5;39", s)     # bright blue
    @classmethod
    def hero(cls, s):   return cls._c("1;38;5;135", s)  # bold purple
    @classmethod
    def title(cls, s):  return cls._c("1;38;5;15", s)   # bold white
    @classmethod
    def dim(cls, s):    return cls._c("38;5;245", s)    # grey
    @classmethod
    def key(cls, s):    return cls._c("38;5;114", s)    # green
    @classmethod
    def ok(cls, s):     return cls._c("1;38;5;114", s)  # bold green
    @classmethod
    def warn(cls, s):   return cls._c("1;38;5;214", s)  # orange
    @classmethod
    def bad(cls, s):    return cls._c("1;38;5;203", s)  # red
    @classmethod
    def body(cls, s):   return cls._c("38;5;252", s)    # near-white
    @classmethod
    def purple(cls, s): return cls._c("38;5;141", s)    # soft purple


ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def visible_len(s: str) -> int:
    return len(ANSI_RE.sub("", s))


def clip_ansi(s: str, maxlen: int) -> str:
    """Truncate to maxlen visible chars, preserving ANSI codes."""
    if visible_len(s) <= maxlen:
        return s
    out, count, i = [], 0, 0
    while i < len(s) and count < maxlen:
        m = ANSI_RE.match(s, i)
        if m:
            out.append(m.group(0))
            i = m.end()
        else:
            out.append(s[i])
            count += 1
            i += 1
    out.append("\033[0m" if C.on else "")
    return "".join(out)


# ---------------------------------------------------------------- framing

def term_width() -> int:
    cols = shutil.get_terminal_size(fallback=(100, 24)).columns
    return max(74, min(cols, 100))


def frame(lines, title=None, footer=None, width=None, pad=2):
    """Render lines inside a rounded box. Lines may carry ANSI color."""
    w = width or term_width()
    inner = w - 2 - 2 * pad
    out = []

    if title:
        out.append(C.frame("╭──") + C.title(f" {title} ") +
                   C.frame("─" * max(0, w - 6 - len(title)) + "╮"))
    else:
        out.append(C.frame("╭" + "─" * (w - 2) + "╮"))

    for ln in lines:
        ln = clip_ansi(ln, inner)
        gap = inner - visible_len(ln)
        out.append(C.frame("│") + " " * pad + ln + " " * max(0, gap) +
                   " " * pad + C.frame("│"))

    if footer:
        out.append(C.frame("╰" + "─" * max(0, w - 6 - len(footer))) +
                   C.dim(f" {footer} ") + C.frame("──╯"))
    else:
        out.append(C.frame("╰" + "─" * (w - 2) + "╯"))
    return "\n".join(out)


def wrap_block(text: str, width: int):
    """Wrap multi-line text to width, preserving blank lines and indent."""
    lines = []
    for raw in text.split("\n"):
        if not raw.strip():
            lines.append("")
            continue
        indent = " " * (len(raw) - len(raw.lstrip()))
        wrapped = textwrap.wrap(
            raw.strip(), width=max(10, width - len(indent)),
            break_long_words=False, break_on_hyphens=False,
        ) or [""]
        lines.extend(indent + w for w in wrapped)
    return lines


def hero_block(hero_art, tagline, ramp, width):
    """Center ASCII art with a per-row color ramp, tagline underneath."""
    lines = hero_art.split("\n")
    art_w = max(len(l) for l in lines)
    center = max(width, art_w)
    out = []
    for i, l in enumerate(lines):
        shade = ramp[min(i, len(ramp) - 1)]
        colored = (f"\033[1;38;5;{shade}m{l.rstrip()}\033[0m"
                   if C.on else l.rstrip())
        out.append(" " * max(0, (center - art_w) // 2) + colored)
    out.append(" " * max(0, (center - len(tagline)) // 2) + C.dim(tagline))
    return "\n".join(out)


def stat_line(label, value, width, label_w=14):
    room = max(8, width - label_w)
    if len(value) > room:
        value = value[: room - 1] + "…"
    return C.key(f"{label:<{label_w}}") + C.body(value)


def tilde(path: str) -> str:
    """Shorten only this user's home; shared/global paths stay explicit."""
    return path.replace(HOME, "~") if path.startswith(HOME) else path


def human_bytes(n: float) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if abs(n) < 1024 or unit == "T":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}T"


def human_age(seconds: float) -> str:
    """Compact relative age: 3d, 5h, 12m."""
    if seconds < 0:
        return "future"
    for div, unit in ((86400 * 365, "y"), (86400 * 30, "mo"),
                      (86400, "d"), (3600, "h"), (60, "m")):
        if seconds >= div:
            return f"{seconds / div:.0f}{unit}"
    return f"{seconds:.0f}s"


# ---------------------------------------------------------------- config

def load_config(model_env=None, default_model=DEFAULT_MODEL):
    """Resolve GLM credentials the same way across every tool.

    Per-user config wins; the machine-wide file is the fallback so any
    account on this host works without its own setup. Env always wins.
    """
    cfg = {
        "endpoint": DEFAULT_ENDPOINT,
        "api_key": "",
        "model": default_model,
        "timeout": 600,
    }
    for path in (os.path.join(HOME, ".qglm.yaml"),
                 os.path.join(SHARED_QGLM_DIR, ".qglm.yaml")):
        if cfg["api_key"]:
            break
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    m = re.match(r"\s*(api_key|endpoint)\s*:\s*(.+)", line)
                    if m:
                        cfg[m.group(1)] = m.group(2).strip().strip("'\"")
        except OSError:
            continue
    cfg["api_key"] = os.environ.get("QGLM_API_KEY", cfg["api_key"])
    cfg["endpoint"] = os.environ.get("QGLM_ENDPOINT", cfg["endpoint"])
    if model_env:
        cfg["model"] = os.environ.get(model_env, cfg["model"])
    cfg["thinking"] = "disabled"
    return cfg


def clipboard_copy(text: str) -> bool:
    try:
        proc = subprocess.run(["pbcopy"], input=text.encode("utf-8"),
                              timeout=10)
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


# ---------------------------------------------------------------- GLM call

def call_glm(cfg, messages, temperature=0.2, max_tokens=4096, label="thinking"):
    """Streaming chat-completions call with a live progress line.

    Returns (text, elapsed_seconds, usage_dict)."""
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "top_p": 0.9,
        "max_tokens": max_tokens,
        "stream": True,
        # The thinking phase costs ~50s per call for little gain on the
        # deduce-and-match workloads these tools run.
        "thinking": {"type": cfg.get("thinking", "disabled")},
    }
    req = urllib.request.Request(
        cfg["endpoint"],
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {cfg['api_key']}"})
    chunks, usage, served = [], {}, None
    start = time.time()
    last_draw = 0.0
    spinner = "◢◣◤◥"
    live = sys.stderr.isatty()
    try:
        with urllib.request.urlopen(req, timeout=cfg["timeout"]) as resp:
            for i, raw in enumerate(resp):
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                    delta = obj["choices"][0].get("delta", {})
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
                if obj.get("usage"):
                    usage = obj["usage"]
                if obj.get("model"):
                    served = obj["model"]
                content = delta.get("content") or ""
                if content:
                    chunks.append(content)
                now = time.time()
                if live and now - last_draw >= 0.15:
                    last_draw = now
                    n = sum(len(c) for c in chunks)
                    sys.stderr.write(
                        f"\r  {spinner[i % 4]} {label}… "
                        f"{n:,} chars · {now - start:.0f}s ")
                    sys.stderr.flush()
    finally:
        if live:
            sys.stderr.write("\r" + " " * 70 + "\r")
            sys.stderr.flush()
    if served:
        usage["_served"] = served
    return "".join(chunks), time.time() - start, usage


def merge_usage(*usages):
    """Sum token usage across calls into one telemetry dict."""
    tot = {"prompt": 0, "cached": 0, "out": 0, "cache_supported": False}
    for u in usages:
        if not u:
            continue
        tot["prompt"] += u.get("prompt_tokens", 0)
        det = u.get("prompt_tokens_details")
        if det is not None:
            tot["cache_supported"] = True
            tot["cached"] += det.get("cached_tokens", 0)
        tot["out"] += u.get("completion_tokens", 0)
    return tot


# $/1M tokens (input, cached input, output) — z.ai pricing 2026-07
PRICING = {
    "glm-4.7-flash": (0.0, 0.0, 0.0),
    "glm-4.5-flash": (0.0, 0.0, 0.0),
    "glm-4.7": (0.6, 0.11, 2.2),
    "glm-4.6": (0.6, 0.11, 2.2),
    "glm-4.5": (0.6, 0.11, 2.2),
    "glm-4.5-air": (0.2, 0.03, 1.1),
    "glm-4-32b-0414-128k": (0.1, None, 0.1),
}


def telemetry_line(tot, model=""):
    """One-line cache/token telemetry with real z.ai pricing."""
    if not tot["prompt"]:
        return C.dim(" telemetry unavailable (no usage in stream)")
    pct = 100.0 * tot["cached"] / tot["prompt"]
    price = PRICING.get(model.lower())
    if tot["cached"]:
        cache_part = C.ok(f'{tot["cached"]:,} cached ({pct:.0f}%)')
    elif tot["cache_supported"]:
        cache_part = C.dim("0 cached (cold)")
    else:
        cache_part = C.dim("cache n/a for this model")
    if price and price[0] == 0.0:
        note = "  →  free tier ✦"
    elif price and tot["cached"] and price[1] is not None:
        full = tot["prompt"] * price[0] + tot["out"] * price[2]
        real = ((tot["prompt"] - tot["cached"]) * price[0]
                + tot["cached"] * price[1] + tot["out"] * price[2])
        note = (f'  →  ${real / 1e6:.4f} '
                f'(cache saved {100 * (1 - real / full):.0f}%)')
    elif price:
        cost = tot["prompt"] * price[0] + tot["out"] * price[2]
        note = f'  →  ${cost / 1e6:.4f}'
    else:
        note = ""
    return (C.dim(" tokens  ") + C.body(f'{tot["prompt"]:,} in') +
            C.dim(" · ") + cache_part +
            C.dim(" · ") + C.body(f'{tot["out"]:,} out') + C.dim(note))


# ---------------------------------------------------------------- shell

def run(cmd, cwd=None, timeout=30):
    """Run a command, returning stdout or '' on any failure."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout)
        return p.stdout if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def user_homes():
    """Every real home directory on this machine, current user first."""
    homes = [HOME]
    for base in ("/Users", "/home"):
        try:
            names = sorted(os.listdir(base))
        except OSError:
            continue
        for name in names:
            if name.startswith(".") or name == "Shared":
                continue
            p = os.path.join(base, name)
            if os.path.isdir(p) and p not in homes and os.access(p, os.R_OK):
                homes.append(p)
    return homes
