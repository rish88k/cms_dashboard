"""
DBA Central Dashboard — Flask application
Connects to DBA_Central and renders the control plane dashboard.

Run natively on Windows (Windows login):
    pip install -r requirements.txt
    set DBA_DEMO=0
    python app.py

Run in Docker (SQL login, reaches the laptop through host.docker.internal):
    copy .env.example .env      (then edit the password)
    docker compose up --build

All settings come from environment variables — see .env.example.
"""

from flask import Flask, render_template, jsonify
import os
from datetime import datetime

try:
    import pyodbc
except ImportError:          # lets demo mode run without the ODBC stack
    pyodbc = None

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────
# CONFIG — every value can be set with an environment variable
# ─────────────────────────────────────────────────────────────
USE_DEMO_DATA = os.getenv('DBA_DEMO', '1') == '1'           # '0' = live database

SQL_HOST     = os.getenv('DBA_SQL_HOST', 'OIT-L222')        # in Docker: host.docker.internal
SQL_PORT     = os.getenv('DBA_SQL_PORT', '')                # in Docker: 1433 (Browser/UDP does not cross Docker NAT)
SQL_DATABASE = os.getenv('DBA_SQL_DATABASE', 'DBA_Central')
SQL_AUTH     = os.getenv('DBA_SQL_AUTH', 'windows').lower() # 'windows' or 'sql'
SQL_USER     = os.getenv('DBA_SQL_USER', '')
SQL_PASSWORD = os.getenv('DBA_SQL_PASSWORD', '')
ODBC_DRIVER  = os.getenv('DBA_ODBC_DRIVER', 'ODBC Driver 18 for SQL Server')
TRUST_CERT   = os.getenv('DBA_SQL_TRUST_CERT', 'yes')       # 'no' once the server has a trusted certificate


def build_conn_str():
    """Build the ODBC connection string from the settings above."""
    # host,port forces a direct TCP connection; host alone lets SQL Browser resolve it
    server = f"{SQL_HOST},{SQL_PORT}" if SQL_PORT else SQL_HOST
    parts = [
        f"DRIVER={{{ODBC_DRIVER}}}",
        f"SERVER={server}",
        f"DATABASE={SQL_DATABASE}",
        "Encrypt=yes",
        f"TrustServerCertificate={TRUST_CERT}",
    ]
    if SQL_AUTH == 'sql':
        if not SQL_USER or not SQL_PASSWORD:
            raise RuntimeError("DBA_SQL_AUTH=sql needs DBA_SQL_USER and DBA_SQL_PASSWORD")
        pwd = SQL_PASSWORD.replace('}', '}}')                    # ODBC escaping inside {...}
        parts += [f"UID={SQL_USER}", f"PWD={{{pwd}}}"]            # braces allow ; in passwords
    else:
        parts.append("Trusted_Connection=yes")
    return ";".join(parts) + ";"


if not USE_DEMO_DATA and pyodbc is None:
    raise RuntimeError("Live mode needs pyodbc and the Microsoft ODBC Driver 18 for SQL Server. "
                       "Install them, or set DBA_DEMO=1 for sample data.")

CONN_STR = None if USE_DEMO_DATA else build_conn_str()


def query(sql, demo_key=None):
    """Run a query against DBA_Central. Falls back to demo data if configured."""
    if USE_DEMO_DATA:
        return DEMO_DATA.get(demo_key, [])
    try:
        with pyodbc.connect(CONN_STR, timeout=5) as conn:
            cur = conn.cursor()
            cur.execute(sql)
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as e:
        app.logger.error(f"Query failed: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# DEMO DATA — swap USE_DEMO_DATA to '0' to use the live database
# ─────────────────────────────────────────────────────────────
DEMO_DATA = {
    'estate': [
        {'InstanceId': 3, 'ServerName': 'OIT-L222\\NODE_1', 'Environment': 'CMS-G',
         'GroupPath': '\\DatabaseEngineServerGroup\\CMS-G', 'IsActive': 1,
         'LastSyncUtc': '2026-09-23 18:35'},
        {'InstanceId': 4, 'ServerName': 'OIT-L222\\NODE_3', 'Environment': 'CMS-G',
         'GroupPath': '\\DatabaseEngineServerGroup\\CMS-G', 'IsActive': 1,
         'LastSyncUtc': '2026-09-23 18:35'},
        {'InstanceId': 5, 'ServerName': 'OIT-L222\\NODE_2', 'Environment': 'CMS-H',
         'GroupPath': '\\DatabaseEngineServerGroup\\CMS-H', 'IsActive': 1,
         'LastSyncUtc': '2026-09-23 18:35'},
        {'InstanceId': 6, 'ServerName': 'OIT-L222\\NODE_4', 'Environment': 'CMS-H',
         'GroupPath': '\\DatabaseEngineServerGroup\\CMS-H', 'IsActive': 1,
         'LastSyncUtc': '2026-09-23 18:35'},
    ],
    'patch': [
        {'ServerName': 'OIT-L222\\NODE_1', 'Environment': 'CMS-G', 'ProductVersion': '16.0.4175.1',
         'Edition': 'Developer Edition (64-bit)', 'PatchLevel': 'CU13',
         'TargetVersion': '16.0.4', 'PatchStatus': 'Compliant'},
        {'ServerName': 'OIT-L222\\NODE_2', 'Environment': 'CMS-H', 'ProductVersion': '16.0.4175.1',
         'Edition': 'Developer Edition (64-bit)', 'PatchLevel': 'CU13',
         'TargetVersion': '16.0.4', 'PatchStatus': 'Compliant'},
        {'ServerName': 'OIT-L222\\NODE_3', 'Environment': 'CMS-G', 'ProductVersion': '16.0.4175.1',
         'Edition': 'Developer Edition (64-bit)', 'PatchLevel': 'CU13',
         'TargetVersion': '16.0.4', 'PatchStatus': 'Compliant'},
        {'ServerName': 'OIT-L222\\NODE_4', 'Environment': 'CMS-H', 'ProductVersion': '16.0.2130.1',
         'Edition': 'Developer Edition (64-bit)', 'PatchLevel': 'CU4',
         'TargetVersion': '16.0.4', 'PatchStatus': 'Behind'},
    ],
    'disk': [
        {'ServerName': 'OIT-L222\\NODE_1', 'Environment': 'CMS-G', 'VolumePath': 'C:\\',
         'TotalGB': 476.3, 'FreeGB': 182.7, 'FreePercent': 38.4},
        {'ServerName': 'OIT-L222\\NODE_2', 'Environment': 'CMS-H', 'VolumePath': 'C:\\',
         'TotalGB': 476.3, 'FreeGB': 182.7, 'FreePercent': 38.4},
        {'ServerName': 'OIT-L222\\NODE_3', 'Environment': 'CMS-G', 'VolumePath': 'C:\\',
         'TotalGB': 476.3, 'FreeGB': 52.1, 'FreePercent': 10.9},
        {'ServerName': 'OIT-L222\\NODE_4', 'Environment': 'CMS-H', 'VolumePath': 'C:\\',
         'TotalGB': 476.3, 'FreeGB': 18.4, 'FreePercent': 3.9},
    ],
    'alerts': [
        {'ServerName': 'OIT-L222\\NODE_4', 'Environment': 'CMS-H', 'AlertUtc': '2026-09-23 18:42',
         'AlertType': 'DiskLow', 'Severity': 'Critical',
         'Message': 'C:\\ at 3.9% free (18.4 GB of 476.3 GB)', 'IsSent': 0},
        {'ServerName': 'OIT-L222\\NODE_3', 'Environment': 'CMS-G', 'AlertUtc': '2026-09-23 18:42',
         'AlertType': 'DiskLow', 'Severity': 'Warning',
         'Message': 'C:\\ at 10.9% free (52.1 GB of 476.3 GB)', 'IsSent': 0},
        {'ServerName': 'OIT-L222\\NODE_4', 'Environment': 'CMS-H', 'AlertUtc': '2026-09-23 18:40',
         'AlertType': 'PatchBehind', 'Severity': 'Warning',
         'Message': 'Build 16.0.2130.1 — target is 16.0.4', 'IsSent': 0},
        {'ServerName': 'OIT-L222\\NODE_1', 'Environment': 'CMS-G', 'AlertUtc': '2026-09-23 18:35',
         'AlertType': 'BackupMissing', 'Severity': 'Critical',
         'Message': 'No full backup in 25+ hours for [AppDB]', 'IsSent': 0},
        {'ServerName': 'OIT-L222\\NODE_2', 'Environment': 'CMS-H', 'AlertUtc': '2026-09-23 18:35',
         'AlertType': 'RpoExceeded', 'Severity': 'Warning',
         'Message': '[TestDB] RPO gap is 240 min (target: 60 min)', 'IsSent': 0},
    ],
    'databases': [
        {'ServerName': 'OIT-L222\\NODE_1', 'Environment': 'CMS-G', 'DatabaseName': 'AppDB',
         'SizeMB': 4096.0, 'RecoveryModel': 'FULL', 'State': 'ONLINE', 'CompatLevel': 160},
        {'ServerName': 'OIT-L222\\NODE_1', 'Environment': 'CMS-G', 'DatabaseName': 'ReportDB',
         'SizeMB': 12288.0, 'RecoveryModel': 'SIMPLE', 'State': 'ONLINE', 'CompatLevel': 160},
        {'ServerName': 'OIT-L222\\NODE_2', 'Environment': 'CMS-H', 'DatabaseName': 'TestDB',
         'SizeMB': 2048.0, 'RecoveryModel': 'FULL', 'State': 'ONLINE', 'CompatLevel': 160},
        {'ServerName': 'OIT-L222\\NODE_3', 'Environment': 'CMS-G', 'DatabaseName': 'StageDB',
         'SizeMB': 8192.0, 'RecoveryModel': 'SIMPLE', 'State': 'ONLINE', 'CompatLevel': 160},
        {'ServerName': 'OIT-L222\\NODE_4', 'Environment': 'CMS-H', 'DatabaseName': 'DevDB',
         'SizeMB': 1024.0, 'RecoveryModel': 'SIMPLE', 'State': 'ONLINE', 'CompatLevel': 150},
    ],
    'backup': [
        {'ServerName': 'OIT-L222\\NODE_1', 'Environment': 'CMS-G', 'DatabaseName': 'AppDB',
         'LastFullUtc': '2026-09-22 05:00', 'LastLogUtc': '2026-09-23 18:30',
         'RpoTargetMin': 60, 'RpoActualMin': 12, 'IsCompliant': 1},
        {'ServerName': 'OIT-L222\\NODE_2', 'Environment': 'CMS-H', 'DatabaseName': 'TestDB',
         'LastFullUtc': '2026-09-23 05:00', 'LastLogUtc': None,
         'RpoTargetMin': 60, 'RpoActualMin': 240, 'IsCompliant': 0},
        {'ServerName': 'OIT-L222\\NODE_3', 'Environment': 'CMS-G', 'DatabaseName': 'StageDB',
         'LastFullUtc': '2026-09-23 05:00', 'LastLogUtc': None,
         'RpoTargetMin': 60, 'RpoActualMin': 45, 'IsCompliant': 1},
        {'ServerName': 'OIT-L222\\NODE_4', 'Environment': 'CMS-H', 'DatabaseName': 'DevDB',
         'LastFullUtc': None, 'LastLogUtc': None,
         'RpoTargetMin': 60, 'RpoActualMin': 99999, 'IsCompliant': 0},
    ],
    'policy': [
        {'ServerName': 'OIT-L222\\NODE_1', 'Environment': 'CMS-G', 'PolicyName': 'AutoShrink_Off',
         'Category': 'Performance', 'Result': 'Pass', 'Detail': ''},
        {'ServerName': 'OIT-L222\\NODE_1', 'Environment': 'CMS-G', 'PolicyName': 'BackupCompression_On',
         'Category': 'Performance', 'Result': 'Pass', 'Detail': 'value=1'},
        {'ServerName': 'OIT-L222\\NODE_1', 'Environment': 'CMS-G', 'PolicyName': 'CostThreshold_50Plus',
         'Category': 'Performance', 'Result': 'Fail', 'Detail': 'value=5'},
        {'ServerName': 'OIT-L222\\NODE_2', 'Environment': 'CMS-H', 'PolicyName': 'AutoShrink_Off',
         'Category': 'Performance', 'Result': 'Pass', 'Detail': ''},
        {'ServerName': 'OIT-L222\\NODE_2', 'Environment': 'CMS-H', 'PolicyName': 'CostThreshold_50Plus',
         'Category': 'Performance', 'Result': 'Fail', 'Detail': 'value=5'},
        {'ServerName': 'OIT-L222\\NODE_3', 'Environment': 'CMS-G', 'PolicyName': 'NoDBsOnCDrive',
         'Category': 'Storage', 'Result': 'Fail', 'Detail': 'C:\\Data\\StageDB.mdf'},
        {'ServerName': 'OIT-L222\\NODE_4', 'Environment': 'CMS-H', 'PolicyName': 'AdHocOptimize_On',
         'Category': 'Performance', 'Result': 'Fail', 'Detail': 'value=0'},
    ],
    'collection': [
        {'CollectorName': 'InventoryCollector', 'TargetServer': 'OIT-L222\\NODE_1',
         'StartUtc': '2026-09-23 18:42', 'Status': 'Success', 'Message': 'Collected'},
        {'CollectorName': 'DiskSpaceCollector', 'TargetServer': 'OIT-L222\\NODE_1',
         'StartUtc': '2026-09-23 18:42', 'Status': 'Success', 'Message': 'Collected'},
        {'CollectorName': 'BackupCollector', 'TargetServer': 'OIT-L222\\NODE_2',
         'StartUtc': '2026-09-23 18:42', 'Status': 'Success', 'Message': 'Collected'},
        {'CollectorName': 'ErrorLogSweep', 'TargetServer': 'OIT-L222\\NODE_3',
         'StartUtc': '2026-09-23 18:42', 'Status': 'Failed', 'Message': 'Login timeout expired'},
        {'CollectorName': 'PolicyEvaluator', 'TargetServer': 'OIT-L222\\NODE_4',
         'StartUtc': '2026-09-23 18:42', 'Status': 'Success', 'Message': 'Collected'},
    ],
}


# ─────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────

@app.route('/')
def overview():
    estate = query("SELECT * FROM cfg.vEstateMap WHERE IsActive = 1", 'estate')
    alerts = query("SELECT * FROM hlth.vRecentAlerts ORDER BY AlertUtc DESC", 'alerts')
    patch = query("SELECT * FROM inv.vPatchCompliance", 'patch')
    disk = query("SELECT * FROM cap.vDiskSpace", 'disk')
    backup = query("SELECT * FROM bkp.vRpoCompliance", 'backup')
    policy = query("SELECT * FROM comp.vPolicyScorecard", 'policy')

    # Summary metrics
    stats = {
        'instances': len(estate),
        'alerts_critical': sum(1 for a in alerts if a.get('Severity') == 'Critical'),
        'alerts_warning': sum(1 for a in alerts if a.get('Severity') == 'Warning'),
        'patch_compliant': sum(1 for p in patch if p.get('PatchStatus') == 'Compliant'),
        'patch_total': len(patch),
        'backup_compliant': sum(1 for b in backup if b.get('IsCompliant') == 1),
        'backup_total': len(backup),
        'policy_pass': sum(1 for p in policy if p.get('Result') == 'Pass'),
        'policy_total': len(policy),
        'disk_critical': sum(1 for d in disk if d.get('FreePercent', 100) < 5),
        'disk_warning': sum(1 for d in disk if 5 <= d.get('FreePercent', 100) < 15),
    }

    return render_template('overview.html',
                           stats=stats, estate=estate, alerts=alerts[:10],
                           patch=patch, disk=disk, active='overview')


@app.route('/estate')
def estate():
    data = query("SELECT * FROM cfg.vEstateMap ORDER BY Environment, ServerName", 'estate')
    return render_template('estate.html', estate=data, active='estate')


@app.route('/patch')
def patch():
    data = query("SELECT * FROM inv.vPatchCompliance ORDER BY PatchStatus DESC, ServerName", 'patch')
    dbs = query("SELECT * FROM inv.vDatabaseSizes ORDER BY SizeMB DESC", 'databases')
    return render_template('patch.html', patch=data, databases=dbs, active='patch')


@app.route('/health')
def health():
    disk = query("SELECT * FROM cap.vDiskSpace ORDER BY FreePercent ASC", 'disk')
    alerts = query("SELECT * FROM hlth.vRecentAlerts ORDER BY AlertUtc DESC", 'alerts')
    return render_template('health.html', disk=disk, alerts=alerts, active='health')


@app.route('/backup')
def backup():
    data = query("SELECT * FROM bkp.vRpoCompliance ORDER BY IsCompliant ASC, ServerName", 'backup')
    return render_template('backup.html', backup=data, active='backup')


@app.route('/policy')
def policy():
    data = query("SELECT * FROM comp.vPolicyScorecard ORDER BY Result ASC, ServerName", 'policy')
    return render_template('policy.html', policy=data, active='policy')


@app.route('/platform')
def platform():
    data = query("SELECT * FROM util.vCollectionStatus ORDER BY StartUtc DESC", 'collection')
    return render_template('platform.html', collection=data, active='platform')


@app.route('/healthz')
def healthz():
    """Connection check. Open this first when the pages show no data."""
    if USE_DEMO_DATA:
        return jsonify({'status': 'ok', 'mode': 'demo'})
    target = f"{SQL_HOST},{SQL_PORT}" if SQL_PORT else SQL_HOST
    try:
        with pyodbc.connect(CONN_STR, timeout=5) as conn:
            row = conn.cursor().execute(
                "SELECT @@SERVERNAME, DB_NAME(), SUSER_SNAME(), "
                "(SELECT COUNT(*) FROM cfg.Instance WHERE IsActive = 1)"
            ).fetchone()
        return jsonify({'status': 'ok', 'mode': 'live', 'target': target,
                        'auth': SQL_AUTH, 'server': row[0], 'database': row[1],
                        'login': row[2], 'active_instances': row[3]})
    except Exception as e:
        return jsonify({'status': 'error', 'mode': 'live', 'target': target,
                        'auth': SQL_AUTH, 'error': str(e)}), 503


@app.route('/api/refresh')
def api_refresh():
    """Start the health sweep Agent job (P5 write-back preview).

    The job runs as the SQL Agent service account, so the linked servers work
    whichever login the dashboard uses. Needs the optional grant in
    sql/create_dashboard_login.sql.
    """
    if USE_DEMO_DATA:
        return jsonify({'status': 'demo', 'message': 'Demo mode — no action taken'})
    try:
        with pyodbc.connect(CONN_STR, timeout=10, autocommit=True) as conn:
            conn.cursor().execute("EXEC msdb.dbo.sp_start_job @job_name = N'DBA - health sweep'")
        return jsonify({'status': 'ok', 'message': 'Health sweep job started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    host = os.getenv('DBA_BIND', '127.0.0.1')     # 0.0.0.0 inside a container
    port = int(os.getenv('DBA_PORT', '5000'))
    mode = 'DEMO DATA' if USE_DEMO_DATA else f"LIVE — {SQL_HOST}{',' + SQL_PORT if SQL_PORT else ''} ({SQL_AUTH} auth)"
    print(f"\n  DBA Central Dashboard\n  Mode: {mode}\n  Open: http://localhost:{port}\n")
    app.run(debug=os.getenv('DBA_DEBUG', '0') == '1', host=host, port=port)
