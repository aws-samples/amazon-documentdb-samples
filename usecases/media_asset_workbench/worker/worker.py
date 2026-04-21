"""
Media Asset Workbench - Worker Process
Runs on the EC2 instance with S3 Files mounted at /mnt/assets.

S3 Files key insight: this worker uses os.walk(), open(), and PIL/ffprobe
against /mnt/assets exactly as it would against a local directory.
There are no S3 SDK calls in the processing hot path — the file system
semantics come from the S3 Files mount.
"""
import os
import sys
import time
import logging
import datetime
import hashlib
from pathlib import Path

import boto3
import pymongo
from bson import ObjectId

from processors import process_asset, get_asset_type

# ── Config ─────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    stream=sys.stdout,
)
log = logging.getLogger('maw-worker')

DOCDB_SECRET_ARN = os.environ['DOCDB_SECRET_ARN']
BUCKET_NAME = os.environ.get('BUCKET_NAME', '')  # display only
MOUNT_PATH = os.environ.get('MOUNT_PATH', '/mnt/assets')
POLL_INTERVAL = int(os.environ.get('POLL_INTERVAL', 5))
STALE_JOB_TIMEOUT = int(os.environ.get('STALE_JOB_TIMEOUT', 300))  # seconds
CA_BUNDLE = '/etc/ssl/certs/rds-combined-ca-bundle.pem'

# ── DocumentDB connection ──────────────────────────────────────────────────────
# MongoClient is a connection-pooled singleton. It is created once and reused
# across all jobs. _reset_db_client() discards it so the next get_db() call
# rebuilds it — used when a PyMongoError signals the connection is broken.

_db_client = None
_db_secret_cache = None


def _get_docdb_secret():
    global _db_secret_cache
    if _db_secret_cache is None:
        import json
        sm = boto3.client('secretsmanager', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
        resp = sm.get_secret_value(SecretId=DOCDB_SECRET_ARN)
        _db_secret_cache = json.loads(resp['SecretString'])
    return _db_secret_cache


def get_db():
    global _db_client
    if _db_client is None:
        secret = _get_docdb_secret()
        uri = (
            f"mongodb://{secret['username']}:{secret['password']}@{secret['host']}:{secret.get('port', 27017)}"
            f'/?tls=true&tlsCAFile={CA_BUNDLE}&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false'
        )
        _db_client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
    return _db_client['media_asset_workbench']


def _reset_db_client():
    global _db_client
    if _db_client is not None:
        try:
            _db_client.close()
        except Exception:
            pass
        _db_client = None


# ── Job processing ─────────────────────────────────────────────────────────────

def claim_next_job(db) -> dict | None:
    """Atomically claim a pending job, first recovering any stale running jobs."""
    cutoff = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(seconds=STALE_JOB_TIMEOUT)
    ).isoformat()
    result = db.jobs.update_many(
        {'state': 'running', '$or': [
            {'lastHeartbeatAt': {'$lt': cutoff}},
            {'lastHeartbeatAt': {'$exists': False}, 'startedAt': {'$lt': cutoff}},
        ]},
        {'$set': {'state': 'pending'}, '$unset': {'startedAt': '', 'worker': ''}},
    )
    if result.modified_count:
        log.warning('Reset %d stale job(s) back to pending', result.modified_count)

    return db.jobs.find_one_and_update(
        {'state': 'pending'},
        {'$set': {'state': 'running', 'startedAt': _now(), 'lastHeartbeatAt': _now(), 'worker': _worker_id()}},
        return_document=pymongo.ReturnDocument.AFTER,
        sort=[('createdAt', pymongo.ASCENDING)],
    )


def run_job(db, job: dict) -> None:
    dataset_id = job['datasetId']
    log.info(f"Starting job {job['_id']} for dataset {dataset_id}")

    # Update dataset status
    db.datasets.update_one(
        {'_id': dataset_id},
        {'$set': {'status': 'processing', 'processingStartedAt': _now()}},
    )
    db.jobs.update_one({'_id': job['_id']}, {'$set': {'stage': 'scanning'}})

    dataset = db.datasets.find_one({'_id': dataset_id})
    if not dataset:
        _fail_job(db, job, 'dataset not found')
        return

    # The dataset's S3 prefix maps to a path on the S3 Files mount
    s3_prefix = dataset.get('s3Prefix', f'datasets/{dataset_id}/')
    mount_dir = os.path.join(MOUNT_PATH, s3_prefix.strip('/'))

    if not os.path.isdir(mount_dir):
        _fail_job(db, job, f'mount path not found: {mount_dir}')
        return

    # Scan the mounted directory — standard filesystem walk over S3-resident content
    all_files = []
    for root, _dirs, files in os.walk(mount_dir):
        for fname in files:
            if fname.startswith('.') or fname.endswith('.thumb.jpg'):
                continue
            all_files.append(os.path.join(root, fname))

    total = len(all_files)
    log.info(f"Found {total} files in {mount_dir}")

    db.datasets.update_one(
        {'_id': dataset_id},
        {'$set': {'stats.totalFiles': total}},
    )
    db.jobs.update_one(
        {'_id': job['_id']},
        {'$set': {'stage': 'processing', 'totalFiles': total}},
    )

    processed = 0
    errors = 0

    for file_path in all_files:
        try:
            _process_file(db, dataset_id, file_path, mount_dir)
            processed += 1
        except Exception as exc:
            log.warning(f"Error processing {file_path}: {exc}")
            errors += 1

        # Write progress to DocumentDB — drives live UI updates
        db.datasets.update_one(
            {'_id': dataset_id},
            {'$set': {'stats.processedFiles': processed, 'stats.errorFiles': errors}},
        )
        db.jobs.update_one(
            {'_id': job['_id']},
            {'$set': {'processedFiles': processed, 'errorFiles': errors, 'lastHeartbeatAt': _now()}},
        )

    # Complete
    db.jobs.update_one(
        {'_id': job['_id']},
        {'$set': {'state': 'complete', 'completedAt': _now()}},
    )
    db.datasets.update_one(
        {'_id': dataset_id},
        {'$set': {'status': 'complete', 'processingCompletedAt': _now()}},
    )
    log.info(f"Job {job['_id']} complete. processed={processed} errors={errors}")


def _process_file(db, dataset_id: str, file_path: str, mount_dir: str) -> None:
    rel_path = os.path.relpath(file_path, mount_dir)
    asset_type = get_asset_type(file_path)
    size = os.path.getsize(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    # Upsert asset record
    asset_id = _stable_id(dataset_id, rel_path)
    db.assets.update_one(
        {'_id': asset_id},
        {'$set': {
            'datasetId': dataset_id,
            'path': rel_path,
            'filename': os.path.basename(file_path),
            'type': asset_type,
            'extension': ext,
            'size': size,
            'status': 'processing',
            'updatedAt': _now(),
        }},
        upsert=True,
    )

    # Process — PIL/ffprobe read directly from the S3 Files mount path
    processor_result = process_asset(file_path, asset_type)

    # Derive S3 key for thumbnail (still within the S3 Files-backed bucket)
    thumb_s3_key = None
    if processor_result.get('thumbnail_path'):
        thumb_rel = os.path.relpath(processor_result['thumbnail_path'], MOUNT_PATH)
        thumb_s3_key = thumb_rel

    tags = processor_result.get('tags', [])

    update = {
        'status': 'processed' if processor_result.get('processed') else 'error',
        'tags': tags,
        'thumbnailKey': thumb_s3_key,
        'processorResult': {k: v for k, v in processor_result.items()
                            if k not in ('tags', 'thumbnail_path', 'error')},
        'processorError': processor_result.get('error'),
        'processedAt': _now(),
    }
    db.assets.update_one({'_id': asset_id}, {'$set': update})

    log.debug(f"  {rel_path} [{asset_type}] -> {update['status']}")


def _fail_job(db, job: dict, reason: str) -> None:
    log.error(f"Job {job['_id']} failed: {reason}")
    db.jobs.update_one(
        {'_id': job['_id']},
        {'$set': {'state': 'failed', 'error': reason, 'failedAt': _now()}},
    )
    db.datasets.update_one(
        {'_id': job['datasetId']},
        {'$set': {'status': 'failed'}},
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _worker_id() -> str:
    import socket
    return socket.gethostname()


def _stable_id(dataset_id: str, rel_path: str) -> str:
    return hashlib.md5(f'{dataset_id}:{rel_path}'.encode()).hexdigest()


# ── Main loop ──────────────────────────────────────────────────────────────────

def main():
    log.info(f"Worker starting. Mount={MOUNT_PATH} Bucket={BUCKET_NAME}")

    # Wait for initial connection
    while True:
        try:
            get_db().command('ping')
            log.info("Connected to DocumentDB")
            break
        except Exception as exc:
            log.warning(f"DocumentDB not ready: {exc}. Retrying in 10s...")
            _reset_db_client()
            time.sleep(10)

    if not os.path.ismount(MOUNT_PATH):
        log.warning(
            f"{MOUNT_PATH} is not a mount point. "
            "S3 Files may not be mounted yet — processing will fail. "
            "See README for S3 Files mount instructions."
        )

    log.info("Polling for jobs...")
    while True:
        try:
            db = get_db()
            job = claim_next_job(db)
            if job:
                run_job(db, job)
            else:
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            log.info("Shutting down")
            sys.exit(0)
        except pymongo.errors.PyMongoError as exc:
            log.error(f"DocumentDB connection error: {exc}. Reconnecting...")
            _reset_db_client()
            time.sleep(POLL_INTERVAL)
        except Exception as exc:
            log.error(f"Unexpected error: {exc}", exc_info=True)
            time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
