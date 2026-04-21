# TrueNAS Access Reference

**Written:** 2026-04-21. Goal: capture everything needed to diagnose, patch, and deploy
TrueNAS-hosted services (8bit-pipeline, Navi, etc.) without asking the user for creds
or rediscovering access patterns every session.

---

## Connection details

| Thing | Value |
|-------|-------|
| **IP** | `192.168.4.2` |
| **Hostname** | TrueNAS SCALE 25.04.x (Electric Eel / Fangtooth line) |
| **Primary SSH user** | `truenas_admin` (uid=950, gid=950) |
| **SSH key** | `~/.ssh/id_ed25519` (Linux desktop + Mac — both machines) |
| **Storage pool** | `pool` (⚠️ NOT `tank` — old Navi docs reference `tank`, that's wrong) |
| **App dirs** | `/mnt/pool/apps/<service>/` (e.g. `/mnt/pool/apps/navi/`, `/mnt/pool/apps/8bit-pipeline/`) |
| **NAS data root** | `/mnt/pool/NAS/Media/` (shared over SMB) |
| **Timezone** | `America/New_York` (host + all containers) |

## Three access tiers — which to use

### Tier 1: direct SSH as `truenas_admin` (unprivileged)
Fine for: reading non-root files, running non-docker commands, SCP.

```bash
ssh -i ~/.ssh/id_ed25519 truenas_admin@192.168.4.2 '<command>'
```

Limitations:
- ❌ `sudo` prompts for a password (passwordless sudo **is NOT configured**, despite
  what `DEPLOY-HANDOFF.md` in the Navi project says — that doc is stale)
- ❌ Can't read docker socket (`truenas_admin` is not in the `docker` group; socket is
  `srw-rw---- root docker`)
- ❌ Can't read root-owned files/dirs created by containers running as root

### Tier 2: TrueNAS REST API via cronjob (full root)
Use this when you need docker commands, root-only reads, or anything sudo-gated.

```
API base:      http://192.168.4.2/api/v2.0/
Bearer token:  1-6qf41BNM6EGRqGzMIweeNf4HNYnlZS9r9g9BJQYRRZsGCzmVzBAkPhSYyGpnYqHt
```

Pattern: create a disabled cronjob with `user: root` and the command to run, trigger it
via `POST /cronjob/run`, poll for output, delete the cronjob. Output must be written to
a file (cronjobs don't return stdout to the API caller). This is the same pattern
`deploy/deploy-to-truenas.sh` uses.

**Canonical snippet** — run an arbitrary command as root, capture output:

```bash
TRUENAS_API_KEY="1-6qf41BNM6EGRqGzMIweeNf4HNYnlZS9r9g9BJQYRRZsGCzmVzBAkPhSYyGpnYqHt"
# 1. Ship the command script
cat > /tmp/remote-task.sh <<'EOF'
#!/bin/bash
{
  # your root-privileged commands here
  docker ps
  ls -la /mnt/pool/some/root-owned/path
} > /tmp/remote-task.out 2>&1
echo DONE >> /tmp/remote-task.out
EOF
chmod +x /tmp/remote-task.sh
scp -i ~/.ssh/id_ed25519 /tmp/remote-task.sh truenas_admin@192.168.4.2:/tmp/

# 2. Register + trigger cronjob
RESP=$(curl -s -X POST "http://192.168.4.2/api/v2.0/cronjob" \
  -H "Authorization: Bearer $TRUENAS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user":"root","command":"bash /tmp/remote-task.sh",
       "description":"ad-hoc","schedule":{"minute":"0","hour":"0","dom":"1","month":"1","dow":"0"},
       "enabled":false}')
JOB_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -X POST "http://192.168.4.2/api/v2.0/cronjob/run" \
  -H "Authorization: Bearer $TRUENAS_API_KEY" -H "Content-Type: application/json" \
  -d "{\"id\": $JOB_ID}" > /dev/null

# 3. Wait for output (poll the marker line)
for i in $(seq 1 30); do
  sleep 2
  if ssh -i ~/.ssh/id_ed25519 truenas_admin@192.168.4.2 \
       'tail -1 /tmp/remote-task.out 2>/dev/null' | grep -q DONE; then
    break
  fi
done

# 4. Fetch + cleanup
scp -i ~/.ssh/id_ed25519 truenas_admin@192.168.4.2:/tmp/remote-task.out /tmp/
curl -s -X DELETE "http://192.168.4.2/api/v2.0/cronjob/id/$JOB_ID" \
  -H "Authorization: Bearer $TRUENAS_API_KEY" > /dev/null
cat /tmp/remote-task.out
```

### Tier 3: SSH as root
If root SSH is enabled (check `/etc/ssh/sshd_config` on the NAS), you can bypass all
the above. It has **not** been verified enabled as of 2026-04-21. Don't rely on it.

---

## What's running on TrueNAS

| Service | Port | App dir | Container |
|---------|------|---------|-----------|
| **Navi** | 5055 | `/mnt/pool/apps/navi/` | `navi` |
| **8bit-pipeline** | (no UI) | `/mnt/pool/apps/8bit-pipeline/` | `8bit-pipeline` |

Add to this table when new services are deployed.

## Important data locations

```
/mnt/pool/NAS/Media/8-Bit Legacy/        — drop folders for 8bit-pipeline (SMB-shared)
  ├── podcast/{incoming,processing,archive,clips-archive,music-beds}
  ├── photos/{incoming,processing,archive}
  ├── state/                              — drop_watcher.json, buffer_scheduler.json
  └── logs/                               — drop_watcher-YYYYMMDD.log (root-owned if container runs as root!)

/mnt/pool/apps/navi/data/navi.db          — Navi SQLite DB (ALL user data) — NEVER delete
/mnt/pool/apps/8bit-pipeline/config/      — oauth2client.json, .yt_token.json
/mnt/pool/apps/8bit-pipeline/data/        — container-persistent state (transcripts, etc.)
/mnt/pool/apps/*/.env                     — API keys per service (chmod 600)
```

## Gotchas that have bitten us

1. **Containers running as UID 0 (root) create files that the SMB user can't open.**
   Fix: set `user: "950:950"` in each service's `docker-compose.yml` so the container
   runs as `truenas_admin`, whose UID matches the drop-folder ownership.

2. **The docker socket is gated by the `docker` group.** `truenas_admin` is NOT in that
   group. Either use the API route (Tier 2) or add `truenas_admin` to the `docker`
   group on the host (survives across TrueNAS upgrades? unverified — prefer API).

3. **TrueNAS SCALE overwrites some system files on upgrade.** Don't rely on manually-edited
   `/etc/sudoers.d/` or shell-rc changes persisting. App-level config under
   `/mnt/pool/apps/` IS safe.

4. **Pool is `pool`, NOT `tank`.** Old Navi deploy docs say `tank`. They're wrong —
   do not follow them verbatim.

5. **Don't `docker compose down -v`.** The `-v` flag deletes the named volumes, which
   includes Navi's database and 8bit-pipeline's cached transcripts. Use plain
   `docker compose down && docker compose up -d`.

6. **SMB POSIX ACLs** (`+` in `ls -l`): the drop folders have inherited ACLs. New
   subdirectories inherit them correctly only when the creator is a regular user.
   Root-owned subdirs lose the inheritance and become inaccessible over SMB.

---

## Common recipes

### Tail a container's logs
```bash
# via API (always works)
bash /tmp/remote-task.sh  # with: docker logs --tail 200 <container> > /tmp/remote-task.out

# via SSH (only if you're in the docker group — truenas_admin is NOT)
ssh truenas_admin@192.168.4.2 'docker logs --tail 200 <container>'  # will fail
```

### Restart a container
Use Tier 2 (API cronjob) with command: `cd /mnt/pool/apps/<service> && docker compose restart`

### Deploy an updated image (8bit-pipeline)
```bash
cd ~/Projects/8bit-legacy
export TRUENAS_API_KEY="1-6qf41BNM6EGRqGzMIweeNf4HNYnlZS9r9g9BJQYRRZsGCzmVzBAkPhSYyGpnYqHt"
./deploy/deploy-to-truenas.sh
```

### Fix root-owned drop folders created by a misbehaving container
```bash
# Tier 2: run as root via API
chown -R 950:950 "/mnt/pool/NAS/Media/8-Bit Legacy/photos/incoming/_failed"
chmod -R g+rwX,o-rwx "/mnt/pool/NAS/Media/8-Bit Legacy/photos/incoming/_failed"
```

---

## Where to put new secrets

- Per-service API keys → `/mnt/pool/apps/<service>/.env` (chmod 600, NOT in git)
- TrueNAS API key (root-equivalent) → kept in `config/.env` of deployers that need it
  (e.g. `~/Projects/8bit-legacy/config/.env`, Mac side). **This repo's `config/.env`
  does NOT have it on Linux desktop as of 2026-04-21** — copy from Mac via Syncthing
  or 1Password if needed.
