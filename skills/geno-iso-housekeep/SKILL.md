---
name: geno-iso-housekeep
description: >-
  Background housekeeping daemon — wiki maintenance, session mining, health
  aggregation, retro triage, and discovery scanning. Runs autonomously via
  /loop in a geno-iso container. Use when user says /geno-iso-housekeep.
argument-hint: "[--once] [--task <specific-task>]"
license: MIT
metadata:
  author: 42euge
  version: "0.1.0"
observability:
  success_signal: "housekeeping task completed and trace emitted"
  failure_signals:
    - "no stale items found (idle tick)"
    - "task execution failed"
  knowledge_reads:
    - "~/.geno/traces/ (health freshness)"
    - "~/.geno/health/ (skill health cards)"
    - "~/.geno/retro/queue.jsonl (retro queue depth)"
    - "~/.geno/datasets/manifest.json (last mine date)"
    - "~/.geno/geno-notes/.geno-notes/config.toml (wiki staleness)"
    - "~/.geno/discovery/ (last scan date)"
  knowledge_writes:
    - "~/.geno/iso/inbox.jsonl (user notifications)"
    - "~/.geno/health/ (refreshed cards)"
    - "~/.geno/datasets/ (mined examples)"
---

# geno-iso — Background Housekeeping Daemon

Autonomous housekeeping loop for the geno ecosystem. On each wake, checks what's stale across the system, picks the highest-impact task, executes it, and goes back to sleep. Designed to run continuously in a Docker container via `/loop`.

## Priority Queue

On each wake, check staleness in this order and execute the first stale item:

| Priority | Task | Stale when | Action |
|----------|------|-----------|--------|
| 1 | Retro triage | `~/.geno/retro/queue.jsonl` has entries | Run `geno-trace queue` to check depth; process top entries via retro analysis |
| 2 | Health refresh | Health cards older than 1 hour | Run `geno-trace health --refresh` |
| 3 | Wiki compile | `wiki_last_compiled` older than 24 hours and primary sources changed | Run `geno-notes compile` |
| 4 | Session mining | New traces since last mine (check `~/.geno/datasets/manifest.json` last date vs latest trace) | Run `geno-mine extract --since <last-mine-date>` |
| 5 | Discovery scan | Last scan older than 7 days (check `~/.geno/discovery/last_scan`) | Run `geno-discover scan --dry-run` |

## Workflow

### 1. Check staleness

For each item in the priority queue, check its staleness condition:

```bash
# 1. Retro queue
geno-trace queue --json 2>/dev/null

# 2. Health freshness — check newest health card timestamp
ls -lt ~/.geno/health/*.json 2>/dev/null | head -1

# 3. Wiki staleness — read config
cat ~/.geno/geno-notes/.geno-notes/config.toml 2>/dev/null | grep wiki_last_compiled

# 4. Mining freshness — check manifest
cat ~/.geno/datasets/manifest.json 2>/dev/null | python3 -c "import sys,json; m=json.load(sys.stdin); print(m.get('latest','never'))"

# 5. Discovery freshness
cat ~/.geno/discovery/last_scan 2>/dev/null || echo "never"
```

### 2. Execute highest-priority stale task

Run the first stale task found. Log what you're doing:

```bash
echo '{"type":"status","task":"<task-name>","started":"<ISO>"}' >> ~/.geno/iso/inbox.jsonl
```

### 3. Emit trace

After executing:

```bash
geno-trace emit \
  --skill geno-iso \
  --status <success|failure> \
  --tool-calls <count> \
  --errors <count> \
  --tags "housekeeping" "<task-name>"
```

### 4. Write notification

If the task produced user-visible results, write to the inbox:

```bash
echo '{"type":"<task>","summary":"<one-line>","timestamp":"<ISO>","details":{}}' >> ~/.geno/iso/inbox.jsonl
```

Examples:
- `{"type":"retro","summary":"3 skills need retro patches","skills":["turbocharge","cruise","tasks-start"]}`
- `{"type":"mine","summary":"47 new training examples extracted","sft":32,"dpo":15}`
- `{"type":"wiki","summary":"compiled 2 wiki pages from 8 new journal entries"}`
- `{"type":"discovery","summary":"found 2 new skill candidates","candidates":["superpowers","geno-calendar"]}`

### 5. Self-pace

If running via `/loop` (dynamic mode):
- **Queue is deep** (3+ stale items): short sleep (60–120s)
- **1–2 stale items**: medium sleep (270s, stay in cache)
- **Nothing stale**: long sleep (1200–1800s)

If running with `--once`: stop after one task.

## Mode Integration

Check `$GENO_MODE` environment variable:

**Dev mode** (`GENO_MODE=dev`):
- Retro patches: auto-create branches and PRs (with scrubbed bodies)
- Dataset updates: push to dataset repo if configured
- Discovery: auto-install candidates that pass audit

**User mode** (`GENO_MODE=user`, default):
- All changes stay local
- Notifications written to inbox for next interactive session pickup
- Never push, never create PRs, never auto-install

## Inbox Pickup (SessionStart hook)

The companion SessionStart hook (in geno-tools) checks the inbox:

```bash
# In hooks/hooks.json or scripts/bootstrap.sh:
if [ -s ~/.geno/iso/inbox.jsonl ]; then
  echo "📬 geno-iso has $(wc -l < ~/.geno/iso/inbox.jsonl) notifications"
  cat ~/.geno/iso/inbox.jsonl
  # Archive after display
  mv ~/.geno/iso/inbox.jsonl ~/.geno/iso/inbox.$(date +%Y%m%d%H%M%S).jsonl
fi
```

## Error Recovery

- If a task fails, log the error to inbox and move to the next stale item
- If Docker volume mounts are missing, log and skip (don't crash the loop)
- If `geno-trace`, `geno-mine`, or `geno-notes` CLIs are not available, skip tasks that need them
- Never do destructive operations on user data

## What NOT to Do

- **Don't modify user code.** geno-iso only touches `~/.geno/` state files.
- **Don't read user project files.** Only read session transcripts (for mining) and skill repos (for retro).
- **Don't push in user mode.** All network operations require `GENO_MODE=dev`.
- **Don't auto-install skills.** Discovery proposes candidates; installation requires user approval.

## Runtime

Runs in Docker via `docker compose up -d`. Uses `/loop` dynamic mode for self-pacing. Communicates with interactive sessions via `~/.geno/iso/inbox.jsonl`.
