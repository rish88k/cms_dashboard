# DBA Central Dashboard — container image
# Debian 12 is pinned on purpose: Microsoft's ODBC apt repo path is per release.
FROM python:3.12-slim-bookworm

# Microsoft ODBC Driver 18 for SQL Server + unixODBC
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl gnupg ca-certificates \
 && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
      | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
 && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list \
      -o /etc/apt/sources.list.d/mssql-release.list \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc \
 && apt-get purge -y curl gnupg && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY app.py .
COPY templates/ templates/

# Run as a non-root user
RUN useradd --create-home --uid 10001 dashboard
USER dashboard

ENV DBA_DEMO=0 \
    DBA_SQL_HOST=host.docker.internal \
    DBA_SQL_PORT=1433 \
    DBA_SQL_AUTH=sql \
    PYTHONUNBUFFERED=1

EXPOSE 5000

HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/healthz', timeout=8).status == 200 else 1)"

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:app"]
