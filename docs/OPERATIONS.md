# Operations and recovery

## Routine checks

- Monitor `/health` from an external uptime service. A healthy web process does not guarantee the sensor is online; check dashboard last receipt/offline status too.
- Check database storage, cron job success and Render application errors. At a two-second interval one device produces 43,200 rows/day, or about 1.3 million rows in 30 days; measure actual disk use and adjust retention/capacity.
- The daily cleanup deletes readings older than `RETENTION_DAYS` (30 by default). Set the same value in the Render cron job and web service if you change it. Keep longer-term exports separately if needed.
- Review locked dependencies and base images periodically. `requirements.txt` pins Python packages with hashes; Docker base tags are maintained version-family tags, not immutable digests. Record the built image digest for each deployed release.

## Local backups

In Mac Terminal, from the project root:

```sh
sh scripts/backup.sh
```

Copy the resulting private dump off the host. Schedule backups according to your acceptable data loss window and verify them by restoring to an **empty test database**. Volume persistence is not a backup.

For a restore drill, create a separate Compose project/test database first. Restore using PostgreSQL 17 tools:

```sh
# Set PGPASSWORD privately in the terminal environment if required.
pg_restore --host=YOUR_TEST_HOST --username=YOUR_TEST_USER --dbname=YOUR_EMPTY_TEST_DATABASE --no-owner --no-acl backups/YOUR_BACKUP.dump
```

Check row counts, earliest/latest timestamps and `/health` using the restored database. Do not point this command at an existing production database. The archive includes the Alembic revision table.

## Render backups

Check the actual database plan's backup/recovery settings in Render before launch, and perform a restore drill. Follow [Render PostgreSQL recovery](https://render.com/docs/postgresql-backups) for the facilities available to your plan. Maintain a private off-platform logical backup if you need recovery independent of the cloud account. The Blueprint blocks public database connections; run exports via an authorized internal service/job or deliberately allow only your current IP temporarily, then restore the empty allowlist. Never expose the database to all IPs for convenience.

## Updates and rollback

1. Back up before schema changes and verify that the backup is readable.
2. Run tests against a dedicated PostgreSQL test database and run `pip-audit -r requirements.txt --disable-pip`.
3. Confirm the local tests pass, then push the tested commit.
4. Manually deploy the tested commit in Render. Migrations run before the web release.
5. Check `/health`, submit a real reading and verify it on the dashboard.
6. If the application fails, redeploy the previous compatible commit. Application rollback does not reverse database migrations. Prefer forward fixes; destructive downgrades need a planned restore procedure.

Locally, run `docker compose up -d --build` for an update and inspect `docker compose ps` and `docker compose logs --tail=100 api migrate retention`.

## Rotate secrets

Rotate the device key by changing Render's `DEVICE_API_KEY`, deploying, updating the private firmware config and reflashing the ESP32. Expect a short ingestion gap. Rotate the dashboard key by changing `DASHBOARD_API_KEY` and deploying; viewers must reconnect. Keep the values distinct and random, at least 32 characters. Never commit `.env` or `config.h`. Historical credentials in the pasted handover were intentionally not copied into this project; change those credentials if they have been shared beyond the intended people.

## Limits and scaling

This is a single-device/single-instance design. The ingest limiter is memory-based, not shared across replicas. Device identity is configured on the server. Add a device registry with hashed, individually revocable credentials and a shared limiter before expanding to multiple sensors. Add per-user identity and auditing if multiple organizations need access. Do not increase workers/instances while assuming the current limiter is global.

The dashboard's offline indicator tracks server receipt time. A buffered upload can briefly make an offline device appear active. For precise measurement-time reporting or lossless history, add an authenticated measurement timestamp protocol, clock-quality tracking and durable device storage.

Logs omit access URLs and request payloads. SQL errors return a generic 503, and only the exception class is logged. Investigate with controlled diagnostics without exposing database URLs or API keys.
