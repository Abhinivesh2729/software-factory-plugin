#!/usr/bin/env python3
"""PreToolUse hook: run ledger + budget and loop guard for factory operator runs.

Shipped in the software-factory plugin (hooks/hooks.json), so it fires whatever
folder a session starts in. It does nothing for a session until that session runs
`factory-run start`. From then on it:
  - records `factory-run start|item|done|park|end` in ~/.factory/ledger.jsonl
  - tracks tokens per model from the session transcript (incrementally)
  - trips when a run or item passes its time / token budget, or when the same
    tool call repeats `repeat_limit` times inside one item (a loop)
  - once tripped, blocks every tool except the ones needed to wrap up:
    factory-run, gh issue/pr comment|edit, git add/commit/push/status,
    writes to the factory home's digests/ decisions.md memory/, PushNotification.
Exit 2 + stderr = block the call and show Claude the reason.
Never fails a call because of its own errors.
"""
import hashlib, json, os, re, shlex, sys, time

HOME = os.path.expanduser("~")
STATE_DIR = os.path.join(HOME, ".factory/run")
LEDGER = os.path.join(HOME, ".factory/ledger.jsonl")


def factory_home():
    """The owner's private factory home (config, policy, memory). Set by the setup skill."""
    try:
        with open(os.path.join(HOME, ".factory/config.json")) as f:
            return os.path.expanduser(json.load(f).get("home", ""))
    except Exception:
        return ""


FACTORY = factory_home()


def factory_config():
    return load_json(os.path.join(FACTORY, "factory.json"), {}) if FACTORY else {}
CMD_RE = re.compile(r"^\s*(?:\S*/)?factory-run(?:\s+(.*))?$", re.S)


def now():
    return time.time()


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(t))


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def save_state(sid, st):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = os.path.join(STATE_DIR, f".{sid}.tmp")
    with open(tmp, "w") as f:
        json.dump(st, f, indent=1)
    os.replace(tmp, os.path.join(STATE_DIR, f"{sid}.json"))
    # `current.json` lets the CLI find the live run without knowing the session id.
    if st.get("status") != "ended":
        with open(os.path.join(STATE_DIR, "current.json"), "w") as f:
            json.dump({"session": sid}, f)


def ledger(event, sid, st, **extra):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    row = {"ts": iso(now()), "event": event, "session": sid,
           "transcript": st.get("transcript")}
    row.update(extra)
    with open(LEDGER, "a") as f:
        f.write(json.dumps(row) + "\n")


def effective(tot):
    return sum(m.get("input", 0) + m.get("cache_write", 0) + m.get("output", 0)
               + m.get("cache_read", 0) / 10 for m in tot.values())


def update_tokens(st):
    """Read new transcript lines since the last offset and add usage per model."""
    path = st.get("transcript")
    if not path or not os.path.exists(path):
        return
    off = st.get("offset", 0)
    with open(path, "rb") as f:
        f.seek(off)
        chunk = f.read()
    end = chunk.rfind(b"\n")
    if end < 0:
        return
    st["offset"] = off + end + 1
    seen = set(st.get("seen_ids", [])[-200:])
    tot = st.setdefault("tokens", {})
    for line in chunk[: end + 1].splitlines():
        try:
            j = json.loads(line)
        except Exception:
            continue
        m = j.get("message")
        if j.get("type") != "assistant" or not isinstance(m, dict) or not m.get("usage"):
            continue
        mid = m.get("id")  # one API message can span several transcript lines
        if mid in seen:
            continue
        seen.add(mid)
        u, model = m["usage"], m.get("model", "?")
        t = tot.setdefault(model, {})
        for k, src in (("input", "input_tokens"), ("output", "output_tokens"),
                       ("cache_read", "cache_read_input_tokens"),
                       ("cache_write", "cache_creation_input_tokens")):
            t[k] = t.get(k, 0) + (u.get(src) or 0)
    st["seen_ids"] = list(seen)[-200:]


def close_item(sid, st, outcome, note=""):
    it = st.get("item")
    if not it:
        return
    ledger("item_end", sid, st, project=it["project"], ref=it["ref"],
           activity=it["activity"], outcome=outcome, note=note,
           minutes=round((now() - it["started"]) / 60, 1),
           effective_tokens=int(effective(st.get("tokens", {})) - it["tokens_at_start"]))
    st.setdefault("history", []).append({"ref": it["ref"], "activity": it["activity"],
                                         "title": it["title"], "outcome": outcome, "note": note})
    st["history"] = st["history"][-10:]
    st["item"] = None
    if (st.get("trip") or {}).get("scope") == "item":
        st["trip"] = None


def handle_cmd(sid, data, args):
    """Apply a `factory-run` subcommand to the run state. Returns a block reason or None."""
    try:
        argv = shlex.split(args or "")
    except ValueError:
        argv = (args or "").split()
    sub = argv[0] if argv else "status"
    path = os.path.join(STATE_DIR, f"{sid}.json")
    st = load_json(path, None)
    if sub == "start":
        if "--workspace" not in argv and "--company" in argv:
            return None  # another factory tool's run marker, not ours
        company = argv[argv.index("--workspace") + 1] if "--workspace" in argv[:-1] else None
        cos = companies()
        if company not in cos or cos[company].get("bucket"):
            real = ", ".join(k for k, c in cos.items() if not c.get("bucket")) or "?"
            return f"Name the workspace this run serves: `factory-run start --workspace <id>` ({real}). One workspace per run."
        st = {"engine": "software-factory-plugin", "session": sid, "status": "running", "started": now(), "company": company,
              "transcript": data.get("transcript_path"), "offset": 0,
              "tokens": {}, "item": None, "trip": None, "history": []}
        # Count tokens already spent in this session before `start`.
        update_tokens(st)
        st["tokens_at_start"] = effective(st["tokens"])
        save_state(sid, st)
        ledger("run_start", sid, st, company=company)
        return None
    if not st or st.get("engine") != "software-factory-plugin":
        return None  # not a run of this plugin; let the CLI print its own error
    update_tokens(st)
    if sub == "item":
        if (st.get("trip") or {}).get("scope") == "run":
            return f"Run budget is spent ({st['trip']['reason']}). Don't start new items: write the digest, notify, then `factory-run end`."
        close_item(sid, st, "abandoned", "new item started before done/park")
        ref = argv[1] if len(argv) > 1 else "?"
        st["item"] = {"ref": ref, "project": ref.split("#")[0],
                      "activity": argv[2] if len(argv) > 2 else "other",
                      "title": " ".join(argv[3:]) if len(argv) > 3 else "",
                      "started": now(), "tokens_at_start": effective(st["tokens"]),
                      "calls": {}}
        ledger("item_start", sid, st, project=st["item"]["project"], ref=ref,
               activity=st["item"]["activity"], title=st["item"]["title"])
    elif sub in ("done", "park"):
        close_item(sid, st, "done" if sub == "done" else "parked", " ".join(argv[1:]))
    elif sub == "end":
        close_item(sid, st, "abandoned", "run ended")
        st["status"] = "ended"
        ledger("run_end", sid, st, minutes=round((now() - st["started"]) / 60, 1),
               effective_tokens=int(effective(st["tokens"]) - st.get("tokens_at_start", 0)),
               tokens=st["tokens"])
        try:
            os.remove(os.path.join(STATE_DIR, "current.json"))
        except OSError:
            pass
    save_state(sid, st)
    return None


ALLOWED_BASH = re.compile(
    r"^\s*(?:cd\s+\S+|(?:\S*/)?factory-run\b.*|gh\s+(?:issue|pr)\s+(?:comment|edit|view)\b.*"
    r"|git\s+(?:-C\s+\S+\s+)?(?:add|commit|push|status|diff|log)\b.*|cat\s+.*|ls\b.*|date\b.*)\s*$", re.S)


# Never allowed in a factory run, whatever the approval policy says.
DENY = [
    (r"\bgit\s+(?:-C\s+\S+\s+)?push\b[^\n]*(?:--force\b|--force-with-lease\b|\s-f\b|--tags\b|--mirror\b|--delete\b|\s\+\S)", "git push --force/--tags/--delete"),
    (r"\bgit\s+(?:-C\s+\S+\s+)?tag\b", "git tag"),
    (r"\bgit\s+(?:-C\s+\S+\s+)?reset\s+--hard\b", "git reset --hard"),
    (r"\bgh\s+repo\s+(?:delete|edit|archive|rename)\b", "gh repo delete/edit/archive"),
    (r"\bgh\s+release\b", "gh release"),
    (r"\bgh\s+workflow\s+(?:run|enable|disable)\b", "gh workflow run"),
    (r"\bgh\s+pr\s+merge\b[^\n]*--admin\b", "gh pr merge --admin"),
    (r"\bgh\s+api\b[^\n]*(?:-X|--method)\s*['\"]?(?:PUT|PATCH|DELETE)\b", "gh api PUT/PATCH/DELETE"),
    (r"\bgh\s+secret\b", "gh secret"),
]


def companies():
    """Workspaces (a client or a product line). A run serves exactly one."""
    return factory_config().get("workspaces", {})


def foreign(company, text):
    """Name the first path, repo, handle or secret prefix of another company found in a tool input."""
    t = text.lower().replace("~/", HOME.lower() + "/")
    for k, c in companies().items():
        if k == company or k == "shared":
            continue
        for p in c.get("paths", []):
            p = os.path.expanduser(p).rstrip("*").rstrip("/").lower()
            if p and p in t:
                return f"{c['name']} path {p}"
        for r in c.get("repos", []):
            if re.search(r"(?<![\w.-])" + re.escape(r.lower()) + r"(?![\w.-])", t):
                return f"{c['name']} repo {r}"
        for h in (c.get("handles") or {}).values():
            if re.search(r"(?<![\w.])@?" + re.escape(h.lower()) + r"(?![\w])", t):
                return f"{c['name']} account @{h}"
    return None


def denied(cmd):
    for pat, name in DENY:
        if re.search(pat, cmd, re.I):
            return name
    return None


def stop_requested(b):
    """Phone kill switch: label `factory:stop` on the pinned status issue."""
    cfg = b.get("status_issue") or {}
    if not cfg.get("number"):
        return False
    import subprocess
    try:
        out = subprocess.run(["gh", "issue", "view", str(cfg["number"]), "-R", cfg["repo"],
                              "--json", "labels", "--jq", ".labels[].name"],
                             capture_output=True, text=True, timeout=8).stdout
        return "factory:stop" in out.split()
    except Exception:
        return False


def wrap_up_allowed(tool, tin):
    if tool in ("PushNotification",) or tool.startswith("mcp__ccd_turn__"):
        return True
    if tool in ("Read",):
        return True
    if tool in ("Write", "Edit") and FACTORY:
        p = os.path.realpath(tin.get("file_path", ""))
        return p.startswith(os.path.join(os.path.realpath(FACTORY), "digests") + os.sep) or \
            p.startswith(os.path.join(os.path.realpath(FACTORY), "memory") + os.sep) or \
            p == os.path.join(os.path.realpath(FACTORY), "decisions.md")
    if tool == "Bash":
        parts = re.split(r"&&|\|\||;|\n", tin.get("command", ""))
        return all(ALLOWED_BASH.match(p) for p in parts if p.strip()) and \
            not re.search(r"\$\(|`", tin.get("command", ""))
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    sid = data.get("session_id") or ""
    tool = data.get("tool_name") or ""
    tin = data.get("tool_input") or {}
    if tool == "Bash":
        cmd = tin.get("command", "")
        m = CMD_RE.match(cmd)
        # Only a bare `factory-run ...` counts; compound commands go through the guard.
        if m and not re.search(r"&&|\|\||;|\||`|\$\(|\n", cmd.strip()):
            reason = handle_cmd(sid, data, m.group(1))
            if reason:
                print(reason, file=sys.stderr)
                return 2
            return 0
    st = load_json(os.path.join(STATE_DIR, f"{sid}.json"), None)
    if not st or st.get("status") != "running" or st.get("engine") != "software-factory-plugin":
        return 0
    if st.get("company"):
        bad = foreign(st["company"], json.dumps(tin))
        if bad:
            print(f"FACTORY GUARD: this run serves {st['company']} only and that call touches {bad}. "
                  f"Never mix workspaces in one run. Leave it for that workspace's own run.", file=sys.stderr)
            return 2
    if tool == "Bash":
        bad = denied(tin.get("command", ""))
        if bad:
            print(f"FACTORY GUARD: `{bad}` is never allowed in factory runs (factory policy: never). "
                  f"Find another way or leave it for the owner in the digest.", file=sys.stderr)
            return 2
    b = factory_config().get("budget", {})
    b.setdefault("status_issue", factory_config().get("status_issue"))
    update_tokens(st)
    t, eff = now(), effective(st["tokens"])
    trip = st.get("trip")
    if not (trip and trip.get("scope") == "run") and t - st.get("stop_checked", 0) > 120:
        st["stop_checked"] = t
        if stop_requested(b):
            trip = {"scope": "run", "reason": "the owner pressed stop (label factory:stop on the status issue)"}
            trip["at"] = t
            st["trip"] = trip
            ledger("trip", sid, st, **trip)
    if not trip:
        run_eff = eff - st.get("tokens_at_start", 0)
        if (t - st["started"]) / 60 > b.get("run_minutes", 180):
            trip = {"scope": "run", "reason": f"run passed {b.get('run_minutes', 180)} min"}
        elif run_eff > b.get("run_effective_tokens", 3e7):
            trip = {"scope": "run", "reason": f"run passed {int(b.get('run_effective_tokens', 3e7)):,} effective tokens"}
        it = st.get("item")
        if not trip and it:
            key = hashlib.sha1((tool + json.dumps(tin, sort_keys=True)).encode()).hexdigest()[:12]
            it["calls"][key] = it["calls"].get(key, 0) + 1
            if (t - it["started"]) / 60 > b.get("item_minutes", 45):
                trip = {"scope": "item", "reason": f"{it['ref']} passed {b.get('item_minutes', 45)} min"}
            elif eff - it["tokens_at_start"] > b.get("item_effective_tokens", 8e6):
                trip = {"scope": "item", "reason": f"{it['ref']} passed {int(b.get('item_effective_tokens', 8e6)):,} effective tokens"}
            elif it["calls"][key] >= b.get("repeat_limit", 6):
                trip = {"scope": "item", "reason": f"{it['ref']} repeated the same {tool} call {it['calls'][key]} times (loop)"}
        if trip:
            trip["at"] = t
            st["trip"] = trip
            ledger("trip", sid, st, **trip)
    save_state(sid, st)
    if trip and not wrap_up_allowed(tool, tin):
        if trip["scope"] == "item":
            msg = (f"FACTORY GUARD: {trip['reason']}. Stop this item now. Comment on the issue/PR what you tried "
                   f"and why it is not feasible yet, add label factory:parked, run `factory-run park \"<one-line reason>\"`, "
                   f"then continue with the next item (or wrap up).")
        else:
            msg = (f"FACTORY GUARD: {trip['reason']}. The run is over. Park the current item if any "
                   f"(`factory-run park \"<reason>\"`), write and commit the digest, send ONE PushNotification "
                   f"saying the run stopped and why, then `factory-run end`. Do nothing else.")
        print(msg, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
