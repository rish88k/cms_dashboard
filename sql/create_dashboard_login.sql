/*  Dashboard login for the Docker container
    Run on the CMS host: OIT-L222 (default instance), as a sysadmin.

    Why: a Linux container cannot sign in with your Windows / Entra ID login,
    so the dashboard uses a SQL login. This login can only read the dashboard
    views in DBA_Central. Re-run the script after you add new views.          */

/* ── Step 1: check the authentication mode ──────────────────────────────── */
SELECT CASE SERVERPROPERTY('IsIntegratedSecurityOnly')
         WHEN 1 THEN 'Windows only  -> SQL logins are refused. Do Step 2.'
         ELSE        'Mixed mode    -> OK. Skip Step 2.'
       END AS AuthenticationMode;
GO

/* ── Step 2 (only if Windows only): switch to mixed mode ────────────────────
   SSMS: right-click the server > Properties > Security >
         "SQL Server and Windows Authentication mode" > OK.
   Then restart "SQL Server (MSSQLSERVER)" in SQL Server Configuration Manager.
   The T-SQL equivalent (also needs the restart):

EXEC master.dbo.xp_instance_regwrite
     N'HKEY_LOCAL_MACHINE',
     N'Software\Microsoft\MSSQLServer\MSSQLServer',
     N'LoginMode', REG_DWORD, 2;
*/

/* ── Step 3: the login ───────────────────────────────────────────────────── */
USE master;
GO
IF SUSER_ID(N'dashboard_reader') IS NULL
    CREATE LOGIN dashboard_reader
        WITH PASSWORD        = N'change-me-to-a-long-random-value',   -- same value as DBA_SQL_PASSWORD in .env
             DEFAULT_DATABASE = DBA_Central,
             CHECK_POLICY     = ON,
             CHECK_EXPIRATION = OFF;     -- a service login; rotate it on your own schedule
GO

/* ── Step 4: read access to the dashboard views only ─────────────────────── */
USE DBA_Central;
GO
IF USER_ID(N'dashboard_reader') IS NULL
    CREATE USER dashboard_reader FOR LOGIN dashboard_reader;
GO

DECLARE @sql nvarchar(max) = N'';
SELECT @sql += N'GRANT SELECT ON ' + QUOTENAME(s.name) + N'.' + QUOTENAME(v.name)
             + N' TO dashboard_reader;' + CHAR(10)
FROM   sys.views v
JOIN   sys.schemas s ON s.schema_id = v.schema_id;
EXEC sys.sp_executesql @sql;
PRINT @sql;
GO

-- /healthz also reads one table directly
GRANT SELECT ON cfg.Instance TO dashboard_reader;
GO

/* ── Step 5 (optional): let the dashboard start the health sweep job ────────
   Needed only for the /api/refresh endpoint. SQLAgentOperatorRole can start
   ANY local Agent job, so leave this out unless you want that button.

USE msdb;
IF USER_ID(N'dashboard_reader') IS NULL
    CREATE USER dashboard_reader FOR LOGIN dashboard_reader;
ALTER ROLE SQLAgentOperatorRole ADD MEMBER dashboard_reader;
*/

/* ── Step 6: verify as the new login ────────────────────────────────────── */
EXECUTE AS LOGIN = N'dashboard_reader';
    SELECT SUSER_SNAME() AS LoggedInAs, COUNT(*) AS ActiveInstances
    FROM   DBA_Central.cfg.vEstateMap WHERE IsActive = 1;
REVERT;
GO
