# DBA Central Dashboard

A Flask web app that shows your SQL Server control plane. It reads the `DBA_Central`
views directly — no intermediate layer.

It runs two ways:

| | Natively on Windows | In Docker |
|---|---|---|
| Reaches SQL Server at | `OIT-L222` | `host.docker.internal,1433` |
| Signs in with | Your Windows / Entra login | SQL login `dashboard_reader` |
| Best for | Quick local use | Isolated, repeatable, shareable runs |

Both start in **demo mode** (`DBA_DEMO=1`) unless you set `DBA_DEMO=0`.

### How it reaches the CMS (master) server

The "master node" is the **Central Management Server** host (`OIT-L222`, default
instance). It holds the `DBA_Central` database, which the collectors fill from every
registered node (`NODE_1` … `NODE_4`). The dashboard only ever connects to that one
server and database — it never talks to the nodes itself.

```
browser ──HTTP──▶ Flask app ──ODBC / TDS (TCP 1433)──▶ OIT-L222 · DBA_Central
                                                          ▲
                        Agent jobs / collectors ──────────┘── NODE_1 … NODE_4
```

The connection is configured with `DBA_SQL_HOST`, `DBA_SQL_PORT`, `DBA_SQL_DATABASE`,
`DBA_SQL_AUTH` (+ user/password) — see [Settings](#settings). Always confirm it with
**`/healthz`** before looking at the pages: it shows which server, database and login
the app reached, or the exact driver error. If a page cannot read its data, a red
banner at the top of the page shows the error instead of empty tables that look healthy.

---

## Option A — Docker (app in a container, SQL Server on the laptop)

```
┌──────────── company laptop (OIT-L222) ─────────────┐
│                                                    │
│  ┌─ Docker container ─┐        SQL Server          │
│  │ dashboard (Flask)  │──TCP──▶ default instance   │
│  │ ODBC Driver 18     │ 1433   DBA_Central         │
│  └────────────────────┘                            │
│     host.docker.internal = "the laptop"            │
└────────────────────────────────────────────────────┘
```

### Why it needs different settings

- **Address.** Inside a container, `localhost` and `OIT-L222` mean the container
  itself. Docker Desktop gives the name **`host.docker.internal`** for the laptop.
- **Port.** SQL Server Browser (UDP 1434) does not work through Docker networking,
  so give the **TCP port** directly. The default instance uses 1433.
- **Login.** A Linux container cannot sign in with your Windows / Entra ID login.
  It uses a **SQL login** with read-only access to the views.

### One-time setup on the laptop (in SSMS, connected to `OIT-L222`)

1. **Check TCP/IP on port 1433.** SQL Server Configuration Manager →
   *SQL Server Network Configuration* → *Protocols for MSSQLSERVER* → **TCP/IP: Enabled**.
   Open TCP/IP → *IP Addresses* → **IPAll**: *TCP Port* = `1433`, *TCP Dynamic Ports* = blank.
   Restart *SQL Server (MSSQLSERVER)* if you changed anything.
2. **Run `sql/create_dashboard_login.sql`.** Step 1 shows the authentication mode.
   If it says *Windows only*, do Step 2 (switch to mixed mode, then restart the service).
   Set your own long password in Step 3.
3. **Test the login from Windows first** — this proves port, mode and login before
   Docker is involved. In SSMS, connect to server `localhost,1433` with
   *SQL Server Authentication*, user `dashboard_reader`, and tick *Trust server certificate*.
   Run `SELECT * FROM cfg.vEstateMap;`

### Run it

```bat
copy .env.example .env
notepad .env                   :: set DBA_SQL_PASSWORD to the password from step 2
docker compose up --build
```

Open **http://localhost:5000/healthz** first. A good result looks like:

```json
{"status": "ok", "mode": "live", "target": "host.docker.internal,1433",
 "auth": "sql", "login": "dashboard_reader", "server": "OIT-L222",
 "database": "DBA_Central", "active_instances": 4}
```

Then open **http://localhost:5000**.

### If `/healthz` shows an error

| Error text contains | Cause | Fix |
|---|---|---|
| `Login timeout expired` / `TCP Provider` | Port 1433 not reachable | Step 1 (TCP on 1433, restart). Then check that Windows Firewall allows inbound TCP 1433 — this needs an admin, so ask IT if it is blocked |
| `Login failed for user 'dashboard_reader'` | Wrong password, or instance is Windows-only | Re-check `.env`; run Step 1 of the SQL script |
| `The server principal ... is not able to access the database` | User not created in `DBA_Central` | Re-run Step 4 of the SQL script |
| `SELECT permission was denied` | A new view has no grant | Re-run Step 4 (it grants every view) |
| `certificate chain was issued by an authority that is not trusted` | `DBA_SQL_TRUST_CERT=no` with the self-signed certificate | Set it to `yes`, or install a trusted certificate |

> **Company laptop note:** Docker Desktop needs admin rights to install, and a paid
> subscription for larger companies. If either is a problem, use Option B — the app
> is the same.

---

## Option B — natively on Windows (no Docker)

Install the [Microsoft ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server), then:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set DBA_DEMO=0
python app.py
```

This uses your Windows login (`DBA_SQL_AUTH=windows`, the default) against `OIT-L222`.
If you only have Driver 17: `set DBA_ODBC_DRIVER=ODBC Driver 17 for SQL Server`.

---

## Option C — natively on Linux / macOS

Windows logins are not available here, so use the SQL login from
`sql/create_dashboard_login.sql`. Install unixODBC and the
[ODBC Driver 18](https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server)
(`msodbcsql18`), then:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export DBA_DEMO=0 DBA_SQL_HOST=OIT-L222 DBA_SQL_PORT=1433 \
       DBA_SQL_AUTH=sql DBA_SQL_USER=dashboard_reader DBA_SQL_PASSWORD='...'
python app.py            # or: gunicorn --bind 127.0.0.1:5000 app:app
```

`DBA_SQL_HOST` must resolve from this machine — use the FQDN or IP if the short
name does not.

---

## Settings

All settings are environment variables. In Docker they come from `.env`.

| Variable | Default | Meaning |
|---|---|---|
| `DBA_DEMO` | `1` (Docker image: `0`) | `1` = sample data, `0` = live database |
| `DBA_SQL_HOST` | `OIT-L222` (Docker: `host.docker.internal`) | SQL Server host |
| `DBA_SQL_PORT` | blank (Docker: `1433`) | TCP port. Blank = let SQL Browser resolve the instance |
| `DBA_SQL_DATABASE` | `DBA_Central` | Repository database |
| `DBA_SQL_AUTH` | `windows` (Docker: `sql`) | `windows` or `sql` |
| `DBA_SQL_USER` / `DBA_SQL_PASSWORD` | — | Needed when `DBA_SQL_AUTH=sql` |
| `DBA_ODBC_DRIVER` | `ODBC Driver 18 for SQL Server` | ODBC driver name |
| `DBA_SQL_TRUST_CERT` | `yes` | Accept SQL Server's self-signed certificate |
| `DBA_BIND` / `DBA_PORT` | `127.0.0.1` / `5000` | Native run only. In Docker, gunicorn binds `0.0.0.0:5000` |
| `DBA_DEBUG` | `0` | `1` turns on the Flask debugger — never on a shared machine |

---

## Pages

| Page | Route | Reads from |
|---|---|---|
| Overview | `/` | All views — summary cards, recent alerts, disk |
| Estate map | `/estate` | `cfg.vEstateMap` |
| Patch & databases | `/patch` | `inv.vPatchCompliance`, `inv.vDatabaseSizes` |
| Health & alerts | `/health` | `cap.vDiskSpace`, `hlth.vRecentAlerts` |
| Backup & RPO | `/backup` | `bkp.vRpoCompliance` |
| Policy scorecard | `/policy` | `comp.vPolicyScorecard` |
| Platform health | `/platform` | `util.vCollectionStatus` |
| Connection check | `/healthz` | JSON: what the app reached, or the exact error |

## Starting a collector from the dashboard

The **Run health sweep** button on *Platform health* calls `POST /api/refresh`
(POST only — a plain link cannot trigger it), which starts the **`DBA - health sweep`** Agent job with `msdb.dbo.sp_start_job`.
The job runs as the SQL Agent service account, so the linked servers work whichever
login the dashboard uses. For the `dashboard_reader` login it needs the optional
Step 5 grant in `sql/create_dashboard_login.sql` — leave that out to keep the
dashboard strictly read-only.

## Files

```
dba-dashboard/
├─ app.py                        Flask app — config, routes, queries, demo data
├─ requirements.txt              flask, pyodbc
├─ Dockerfile                    Debian 12 + ODBC Driver 18 + gunicorn, non-root user
├─ docker-compose.yml            port 5000 on localhost only, host.docker.internal mapping
├─ .env.example                  copy to .env (never baked into the image)
├─ .dockerignore
├─ sql/
│  └─ create_dashboard_login.sql read-only SQL login for the container
└─ templates/                    one HTML template per page + base.html, _macros.html
```

## Production notes

- The container listens on `127.0.0.1:5000` only. To share it, change the port
  mapping in `docker-compose.yml` **and** add authentication in front of it first.
- Replace `DBA_SQL_TRUST_CERT=yes` with a trusted certificate on the instance.
- Rotate the `dashboard_reader` password; keep `.env` out of source control.
