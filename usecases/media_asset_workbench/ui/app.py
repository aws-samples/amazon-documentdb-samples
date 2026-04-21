"""
Media Asset Workbench - Local UI + API Server
FastAPI serves both the REST API (talks directly to DocumentDB via SSM tunnel)
and the static frontend.

Prerequisites:
  1. SSM port forward open:  aws ssm start-session --target <INSTANCE_ID>
       --document-name AWS-StartPortForwardingSessionToRemoteHost
       --parameters 'host=<DOCDB_ENDPOINT>,portNumber=27017,localPortNumber=27017'
  2. /etc/hosts entry:  127.0.0.1 <DOCDB_ENDPOINT>

Run: uvicorn app:app --reload --port 8080
"""
import logging
import os
import re
import json
import datetime
import secrets

import boto3
import pymongo
from bson import ObjectId
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pymongo.errors import PyMongoError
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / 'config.env', override=False)

log = logging.getLogger('maw-ui')

# ── Config ─────────────────────────────────────────────────────────────────────

DOCDB_SECRET_ARN = os.environ.get('DOCDB_SECRET_ARN', '')
BUCKET_NAME = os.environ.get('BUCKET_NAME', '')
REGION = os.environ.get('AWS_REGION', 'us-east-1')
CA_BUNDLE = os.environ.get('CA_BUNDLE_PATH', str(Path(__file__).parent.parent / 'rds-combined-ca-bundle.pem'))

if not DOCDB_SECRET_ARN:
    print(
        '\n[WARNING] DOCDB_SECRET_ARN is not set.\n'
        'Run deploy.sh first, then check config.env.\n'
    )

# ── DocumentDB ─────────────────────────────────────────────────────────────────

_db_client = None
_sm_client = boto3.client('secretsmanager', region_name=REGION)
_s3_client = boto3.client('s3', region_name=REGION)


def _get_docdb_secret() -> dict:
    resp = _sm_client.get_secret_value(SecretId=DOCDB_SECRET_ARN)
    return json.loads(resp['SecretString'])


def _ensure_indexes(db) -> None:
    db.assets.create_index([('datasetId', 1), ('status', 1)])
    db.assets.create_index([('datasetId', 1), ('type', 1)])
    db.assets.create_index([('datasetId', 1), ('path', 1)])
    db.jobs.create_index([('state', 1), ('createdAt', 1)])
    db.jobs.create_index([('datasetId', 1), ('state', 1)])


def get_db():
    global _db_client
    if _db_client is None:
        secret = _get_docdb_secret()
        # directConnection=true bypasses replica-set member discovery —
        # required when connecting via SSM port forward, as internal member
        # hostnames are not reachable outside the VPC.
        uri = (
            f"mongodb://{secret['username']}:{secret['password']}"
            f"@{secret['host']}:{secret.get('port', 27017)}"
            f"/?tls=true&tlsCAFile={CA_BUNDLE}"
            f"&directConnection=true&retryWrites=false"
        )
        _db_client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        _ensure_indexes(_db_client['media_asset_workbench'])
    return _db_client['media_asset_workbench']


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title='Media Asset Workbench')


@app.exception_handler(PyMongoError)
async def pymongo_error_handler(request, exc):
    return JSONResponse(status_code=503, content={'error': 'Database unavailable'})


# ── Utilities ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f'{prefix}_{secrets.token_hex(8)}'


def _attach_thumbnails(docs: list) -> None:
    for doc in docs:
        if doc.get('thumbnailKey'):
            try:
                doc['thumbnailUrl'] = _s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': BUCKET_NAME, 'Key': doc['thumbnailKey']},
                    ExpiresIn=3600,
                )
            except Exception as exc:
                log.warning('Failed to generate presigned URL for %s: %s', doc['thumbnailKey'], exc)


# ── Config endpoint ────────────────────────────────────────────────────────────

@app.get('/config.json')
async def config():
    """Expose runtime config to the frontend JS."""
    return JSONResponse({'bucketName': BUCKET_NAME})


# ── Datasets ───────────────────────────────────────────────────────────────────

@app.get('/datasets')
def list_datasets(limit: int = Query(default=20, le=100)):
    db = get_db()
    docs = list(db.datasets.find({}, limit=limit, sort=[('createdAt', -1)]))
    return {'datasets': docs, 'count': len(docs)}


@app.post('/datasets', status_code=201)
def create_dataset(body: dict):
    name = body.get('name', '').strip()
    if not name:
        raise HTTPException(400, 'name is required')
    db = get_db()
    dataset_id = _new_id('ds')
    doc = {
        '_id': dataset_id,
        'name': name,
        'description': body.get('description', ''),
        's3Prefix': f'datasets/{dataset_id}/',
        'status': 'created',
        'createdAt': _now(),
        'stats': {'totalFiles': 0, 'processedFiles': 0, 'errorFiles': 0},
    }
    db.datasets.insert_one(doc)
    return doc


@app.get('/datasets/{dataset_id}')
def get_dataset(dataset_id: str):
    db = get_db()
    doc = db.datasets.find_one({'_id': dataset_id})
    if not doc:
        raise HTTPException(404, 'Dataset not found')
    return doc


@app.delete('/datasets/{dataset_id}')
def delete_dataset(dataset_id: str):
    db = get_db()
    active = db.jobs.find_one(
        {'datasetId': dataset_id, 'state': {'$in': ['pending', 'running']}}
    )
    if active:
        raise HTTPException(409, 'Cannot delete dataset with an active job')
    db.assets.delete_many({'datasetId': dataset_id})
    db.jobs.delete_many({'datasetId': dataset_id})
    db.datasets.delete_one({'_id': dataset_id})
    return {'deleted': dataset_id}


# ── Assets ─────────────────────────────────────────────────────────────────────

@app.get('/datasets/{dataset_id}/assets')
def list_assets(
    dataset_id: str,
    type: str = Query(default=None),
    tag: str = Query(default=None),
    status: str = Query(default=None),
    q: str = Query(default=None, max_length=100),
    limit: int = Query(default=50, le=200),
    skip: int = Query(default=0, ge=0),
):
    db = get_db()
    query = {'datasetId': dataset_id}
    if type:
        query['type'] = type
    if tag:
        query['tags'] = tag
    if status:
        query['status'] = status
    if q:
        query['filename'] = {'$regex': re.escape(q), '$options': 'i'}

    docs = list(db.assets.find(query, skip=skip, limit=limit, sort=[('path', 1)]))
    _attach_thumbnails(docs)
    total = db.assets.count_documents(query)
    return {'assets': docs, 'total': total, 'skip': skip, 'limit': limit}


@app.get('/assets/{asset_id}')
def get_asset(asset_id: str):
    db = get_db()
    doc = db.assets.find_one({'_id': asset_id})
    if not doc:
        raise HTTPException(404, 'Asset not found')
    _attach_thumbnails([doc])
    return doc


# ── Jobs ───────────────────────────────────────────────────────────────────────

@app.get('/jobs')
def list_jobs(limit: int = Query(default=20, le=100)):
    db = get_db()
    docs = list(db.jobs.find({}, limit=limit, sort=[('createdAt', -1)]))
    return {'jobs': docs}


@app.get('/jobs/{job_id}')
def get_job(job_id: str):
    db = get_db()
    doc = db.jobs.find_one({'_id': job_id})
    if not doc:
        raise HTTPException(404, 'Job not found')
    return doc


# ── Upload ─────────────────────────────────────────────────────────────────────

@app.post('/upload-url')
def get_upload_url(body: dict):
    filename = body.get('filename', 'upload')
    dataset_id = body.get('datasetId', 'unassigned')
    content_type = body.get('contentType', 'application/octet-stream')

    if not re.match(r'^[\w\-.]+$', filename):
        raise HTTPException(400, 'Invalid filename')
    if not re.match(r'^[\w\-]+$', dataset_id):
        raise HTTPException(400, 'Invalid datasetId')

    s3_key = f'datasets/{dataset_id}/{filename}'
    url = _s3_client.generate_presigned_url(
        'put_object',
        Params={'Bucket': BUCKET_NAME, 'Key': s3_key, 'ContentType': content_type},
        ExpiresIn=300,
    )
    return {'uploadUrl': url, 's3Key': s3_key}


# ── Process ────────────────────────────────────────────────────────────────────

@app.post('/process', status_code=201)
def trigger_processing(body: dict):
    dataset_id = body.get('datasetId', '').strip()
    if not dataset_id:
        raise HTTPException(400, 'datasetId is required')
    db = get_db()
    if not db.datasets.find_one({'_id': dataset_id}):
        raise HTTPException(404, 'Dataset not found')

    job_id = _new_id('job')
    job = {
        '_id': job_id,
        'datasetId': dataset_id,
        'stage': 'queued',
        'state': 'pending',
        'createdAt': _now(),
        'totalFiles': 0,
        'processedFiles': 0,
        'errorFiles': 0,
    }
    db.jobs.insert_one(job)
    db.datasets.update_one({'_id': dataset_id}, {'$set': {'status': 'queued'}})
    return job


# ── Poll ───────────────────────────────────────────────────────────────────────

@app.get('/datasets/{dataset_id}/poll')
def poll_updates(dataset_id: str, since: str = Query(default=None)):
    db = get_db()
    dataset = db.datasets.find_one({'_id': dataset_id})
    if not dataset:
        raise HTTPException(404, 'Dataset not found')

    recent_query = {'datasetId': dataset_id}
    if since:
        recent_query['processedAt'] = {'$gt': since}

    recent_assets = list(db.assets.find(
        recent_query,
        {'_id': 1, 'filename': 1, 'type': 1, 'status': 1, 'tags': 1,
         'thumbnailKey': 1, 'processedAt': 1},
        limit=20,
        sort=[('processedAt', -1)],
    ))

    active_job = db.jobs.find_one(
        {'datasetId': dataset_id, 'state': {'$in': ['pending', 'running']}},
        sort=[('createdAt', -1)],
    )

    return {
        'dataset': dataset,
        'job': active_job,
        'recentAssets': recent_assets,
        'serverTime': _now(),
    }


# ── Sample packs ───────────────────────────────────────────────────────────────

SAMPLE_PACKS = {
    'marketing-images': {
        'id': 'marketing-images',
        'name': 'Marketing Image Pack',
        'description': '30 product and lifestyle images (JPG/PNG, mixed sizes)',
        'fileCount': 30,
        'sizeMb': 18,
        's3Prefix': 'sample-packs/marketing-images/',
    },
    'video-clips': {
        'id': 'video-clips',
        'name': 'Short Video Clips',
        'description': '8 short MP4 clips (HD and 4K, 5-30 seconds each)',
        'fileCount': 8,
        'sizeMb': 45,
        's3Prefix': 'sample-packs/video-clips/',
    },
    'mixed-media': {
        'id': 'mixed-media',
        'name': 'Mixed Media Set',
        'description': 'Photos and short videos — realistic production mix',
        'fileCount': 20,
        'sizeMb': 28,
        's3Prefix': 'sample-packs/mixed-media/',
    },
}


@app.get('/sample-packs')
def list_sample_packs():
    return {'samplePacks': list(SAMPLE_PACKS.values())}


@app.post('/sample-packs/load', status_code=201)
def load_sample_pack(body: dict):
    pack_id = body.get('packId', '').strip()
    if pack_id not in SAMPLE_PACKS:
        raise HTTPException(400, f'Unknown pack. Valid options: {sorted(SAMPLE_PACKS)}')

    db = get_db()
    dataset_id = _new_id('ds')
    doc = {
        '_id': dataset_id,
        'name': f'Sample: {pack_id}',
        'description': f'Built-in sample pack: {pack_id}',
        's3Prefix': SAMPLE_PACKS[pack_id]['s3Prefix'],
        'status': 'created',
        'samplePack': pack_id,
        'createdAt': _now(),
        'stats': {'totalFiles': 0, 'processedFiles': 0, 'errorFiles': 0},
    }
    db.datasets.insert_one(doc)

    job_id = _new_id('job')
    job = {
        '_id': job_id,
        'datasetId': dataset_id,
        'stage': 'queued',
        'state': 'pending',
        'createdAt': _now(),
        'totalFiles': 0,
        'processedFiles': 0,
        'errorFiles': 0,
    }
    db.jobs.insert_one(job)
    db.datasets.update_one({'_id': dataset_id}, {'$set': {'status': 'queued'}})
    return {'dataset': doc, 'job': job}


# ── Static UI ──────────────────────────────────────────────────────────────────

STATIC_DIR = Path(__file__).parent / 'static'


@app.get('/', response_class=HTMLResponse)
async def root():
    return (STATIC_DIR / 'index.html').read_text()


app.mount('/static', StaticFiles(directory=str(STATIC_DIR)), name='static')


@app.get('/{full_path:path}', response_class=HTMLResponse)
async def spa_fallback(full_path: str):
    return (STATIC_DIR / 'index.html').read_text()


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:app', host='127.0.0.1', port=8080, reload=True)
