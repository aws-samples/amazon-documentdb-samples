/**
 * Media Asset Workbench - Frontend
 * Vanilla JS, no build step. Polls the local API for live updates.
 */

// ── Config ────────────────────────────────────────────────────────────────────

let BUCKET_NAME = '';

async function loadConfig() {
  const res = await fetch('/config.json');
  const cfg = await res.json();
  BUCKET_NAME = cfg.bucketName;
}

// ── State ─────────────────────────────────────────────────────────────────────

const state = {
  currentDatasetId: null,
  assets: [],
  assetsSkip: 0,
  assetsLimit: 48,
  filterType: '',
  filterStatus: '',
  filterSearch: '',
  pollTimer: null,
  lastPollTime: '',
};

// ── API ───────────────────────────────────────────────────────────────────────

async function api(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

const get = (path, params) => {
  const qs = params ? '?' + new URLSearchParams(params) : '';
  return api('GET', `${path}${qs}`);
};
const post = (path, body) => api('POST', path, body);
const del = (path) => api('DELETE', path);

// ── Bootstrap ─────────────────────────────────────────────────────────────────

async function init() {
  await loadConfig();
  await Promise.all([loadSamplePacks(), loadDatasets()]);
  bindEvents();
}

// ── Sample packs ──────────────────────────────────────────────────────────────

let samplePacks = [];

async function loadSamplePacks() {
  const sel = document.getElementById('sample-pack-select');
  try {
    const data = await get('/sample-packs');
    samplePacks = data.samplePacks;
    sel.innerHTML = '<option value="">Choose a sample pack...</option>'
      + samplePacks.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
  } catch (e) {
    sel.innerHTML = `<option value="">Error loading packs</option>`;
  }
}

// ── Datasets ──────────────────────────────────────────────────────────────────

async function loadDatasets() {
  const el = document.getElementById('datasets-list');
  try {
    const data = await get('/datasets');
    if (!data.datasets.length) {
      el.innerHTML = '<div class="empty-sm">No datasets yet</div>';
      return;
    }
    el.innerHTML = data.datasets.map(ds => `
      <div class="dataset-item ${ds._id === state.currentDatasetId ? 'active' : ''}"
           data-dataset-id="${ds._id}">
        <div class="di-name">${esc(ds.name)}</div>
        <div class="di-meta">
          <span class="status-dot status-${ds.status}"></span>
          ${ds.status} &middot; ${ds.stats?.processedFiles || 0}/${ds.stats?.totalFiles || 0} files
        </div>
      </div>
    `).join('');
  } catch (e) {
    el.innerHTML = `<div class="error-sm">Failed: ${e.message}</div>`;
  }
}

async function openDataset(datasetId) {
  state.currentDatasetId = datasetId;
  state.assets = [];
  state.assetsSkip = 0;
  state.lastPollTime = '';

  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('dataset-view').style.display = '';

  const data = await get(`/datasets/${datasetId}`);
  renderDatasetHeader(data);
  updateStorageView(data);
  await refreshAssets();
  startPolling();
  await loadDatasets(); // refresh sidebar
}

function renderDatasetHeader(ds) {
  document.getElementById('dv-name').textContent = ds.name;
  const badge = document.getElementById('dv-status-badge');
  badge.textContent = ds.status;
  badge.className = `status-badge status-${ds.status}`;

  // Progress bar
  const total = ds.stats?.totalFiles || 0;
  const processed = ds.stats?.processedFiles || 0;
  const section = document.getElementById('progress-section');

  if (['processing', 'queued'].includes(ds.status)) {
    section.style.display = '';
    document.getElementById('progress-label').textContent =
      ds.status === 'queued' ? 'Queued...' : 'Processing via S3 Files...';
    document.getElementById('progress-fraction').textContent =
      total ? `${processed} / ${total}` : '';
    const pct = total ? Math.round((processed / total) * 100) : 0;
    document.getElementById('progress-bar').style.width = `${pct}%`;
  } else if (ds.status === 'complete') {
    section.style.display = '';
    document.getElementById('progress-label').textContent = 'Complete — syncing thumbnails...';
    document.getElementById('progress-fraction').textContent = `${processed} files`;
    document.getElementById('progress-bar').style.width = '100%';
  } else {
    section.style.display = 'none';
  }
}

function updateStorageView(ds) {
  const flow = document.getElementById('data-flow');
  flow.style.display = '';
  const prefix = ds.s3Prefix || '';
  document.getElementById('flow-s3-path').textContent = `s3://${BUCKET_NAME}/${prefix}`;
  document.getElementById('flow-mount-path').textContent = `/mnt/assets/${prefix.replace(/^\//, '')}`;
}

// ── Assets ────────────────────────────────────────────────────────────────────

async function refreshAssets(append = false) {
  if (!state.currentDatasetId) return;
  const params = {
    limit: state.assetsLimit,
    skip: append ? state.assetsSkip : 0,
  };
  if (state.filterType) params.type = state.filterType;
  if (state.filterStatus) params.status = state.filterStatus;
  if (state.filterSearch) params.q = state.filterSearch;

  const data = await get(`/datasets/${state.currentDatasetId}/assets`, params);

  // Update DocumentDB query indicator
  const queryParts = [`datasetId: "${state.currentDatasetId}"`];
  if (state.filterType) queryParts.push(`type: "${state.filterType}"`);
  if (state.filterStatus) queryParts.push(`status: "${state.filterStatus}"`);
  if (state.filterSearch) queryParts.push(`filename: {$regex: "${state.filterSearch}"}`);
  const qi = document.getElementById('query-text');
  if (qi) qi.textContent = `db.assets.find({${queryParts.join(', ')}})`;

  if (!append) {
    state.assets = data.assets;
    state.assetsSkip = data.assets.length;
  } else {
    state.assets = [...state.assets, ...data.assets];
    state.assetsSkip += data.assets.length;
  }

  renderAssets();
  document.getElementById('filter-stats').textContent =
    `${data.total} asset${data.total !== 1 ? 's' : ''}`;

  const loadMore = document.getElementById('load-more-btn');
  loadMore.style.display = state.assets.length < data.total ? '' : 'none';
}

function renderAssets() {
  const grid = document.getElementById('asset-grid');
  if (!state.assets.length) {
    grid.innerHTML = '<div class="empty-sm">No assets found</div>';
    return;
  }
  grid.innerHTML = state.assets.map(asset => {
    const thumb = asset.thumbnailUrl
      ? `<img src="${asset.thumbnailUrl}" alt="${esc(asset.filename)}" loading="lazy" />`
      : `<div class="asset-no-thumb">${typeIcon(asset.type)}</div>`;
    return `
      <div class="asset-card status-border-${asset.status}" data-asset-id="${asset._id}">
        <div class="asset-thumb">${thumb}</div>
        <div class="asset-info">
          <div class="asset-filename">${esc(asset.filename)}</div>
          <div class="asset-meta">
            <span class="asset-type-badge type-${asset.type}">${asset.type}</span>
            <span class="status-dot status-${asset.status}"></span>
          </div>
          ${asset.tags?.length ? `<div class="asset-tags">${asset.tags.slice(0, 4).map(t => `<span class="tag">${esc(t)}</span>`).join('')}</div>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

function typeIcon(type) {
  return { image: '&#128444;', video: '&#127909;', audio: '&#127925;' }[type] || '&#128196;';
}

// ── Live polling ──────────────────────────────────────────────────────────────

function startPolling() {
  stopPolling();
  state.pollTimer = setInterval(poll, 2000);
  poll(); // immediate first tick
}

function stopPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

async function poll() {
  if (!state.currentDatasetId) return;
  try {
    const params = {};
    if (state.lastPollTime) params.since = state.lastPollTime;

    const data = await get(`/datasets/${state.currentDatasetId}/poll`, params);
    state.lastPollTime = data.serverTime;

    renderDatasetHeader(data.dataset);
    updateJobStatusBar(data.job, data.dataset);

    // Splice new assets into the grid without a full reload
    if (data.recentAssets?.length) {
      const existingIds = new Set(state.assets.map(a => a._id));
      const newOnes = data.recentAssets.filter(a => !existingIds.has(a._id));
      if (newOnes.length) {
        state.assets = [...newOnes, ...state.assets];
        renderAssets();
      }
      // Update status on existing assets
      for (const updated of data.recentAssets) {
        const idx = state.assets.findIndex(a => a._id === updated._id);
        if (idx !== -1) {
          state.assets[idx] = { ...state.assets[idx], ...updated };
        }
      }
      renderAssets();
    }

    // Stop polling when done
    if (['complete', 'failed'].includes(data.dataset.status)) {
      stopPolling();
      // Wait for S3 Files to sync thumbnails back to S3 before fetching presigned URLs
      await new Promise(r => setTimeout(r, 5000));
      await refreshAssets(); // final full refresh with presigned URLs
      document.getElementById('progress-label').textContent = 'Complete';
    }
  } catch (e) {
    // Swallow poll errors silently — network blip shouldn't break the UI
  }
}

function updateJobStatusBar(job, dataset) {
  const bar = document.getElementById('job-status-bar');
  const text = document.getElementById('job-status-text');

  // Data flow pipeline animation
  const steps = ['flow-s3', 'flow-s3files', 'flow-worker', 'flow-docdb'];
  const arrows = ['flow-arrow-1', 'flow-arrow-2', 'flow-arrow-3'];
  steps.forEach(id => { const el = document.getElementById(id); if (el) { el.className = 'flow-step'; } });
  arrows.forEach(id => { const el = document.getElementById(id); if (el) { el.className = 'flow-arrow'; } });

  if (job && job.state === 'running') {
    const pct = job.totalFiles
      ? Math.round((job.processedFiles / job.totalFiles) * 100)
      : 0;
    text.textContent = `Processing ${job.processedFiles}/${job.totalFiles} files (${pct}%) via S3 Files`;
    bar.className = 'topbar-status status-running';
    // Animate: S3 done, S3 Files active, Worker active, DocDB receiving
    ['flow-s3'].forEach(id => { const el = document.getElementById(id); if (el) el.className = 'flow-step flow-done'; });
    ['flow-s3files', 'flow-worker'].forEach(id => { const el = document.getElementById(id); if (el) el.className = 'flow-step flow-active'; });
    ['flow-docdb'].forEach(id => { const el = document.getElementById(id); if (el) el.className = 'flow-step flow-active'; });
    arrows.forEach(id => { const el = document.getElementById(id); if (el) el.className = 'flow-arrow arrow-active'; });
  } else if (dataset.status === 'complete') {
    text.textContent = `Complete — ${dataset.stats.processedFiles} files in DocumentDB`;
    bar.className = 'topbar-status status-complete';
    steps.forEach(id => { const el = document.getElementById(id); if (el) el.className = 'flow-step flow-done'; });
  } else if (dataset.status === 'queued') {
    text.textContent = 'Job queued, waiting for worker...';
    bar.className = 'topbar-status status-queued';
    ['flow-s3'].forEach(id => { const el = document.getElementById(id); if (el) el.className = 'flow-step flow-active'; });
  } else {
    text.textContent = 'Ready';
    bar.className = 'topbar-status';
  }
}

// ── Asset detail panel ────────────────────────────────────────────────────────

async function openAssetDetail(assetId) {
  const panel = document.getElementById('detail-panel');
  panel.style.display = '';
  try {
    const asset = await get(`/assets/${assetId}`);
    const thumb = document.getElementById('detail-thumbnail');
    if (asset.thumbnailUrl) {
      thumb.src = asset.thumbnailUrl;
      thumb.style.display = '';
    } else {
      thumb.style.display = 'none';
    }
    const displayAsset = { ...asset };
    delete displayAsset.thumbnailUrl;
    document.getElementById('detail-json').textContent =
      JSON.stringify(displayAsset, null, 2);
    // Update query indicator to show the specific asset query
    const qi = document.getElementById('query-text');
    if (qi) qi.textContent = `db.assets.find({"datasetId": "${asset.datasetId}", "filename": "${asset.filename}"})`;
    // S3 Files terminal-style output
    const src = document.getElementById('detail-source');
    if (src) {
      const svMount = document.getElementById('flow-mount-path')?.textContent || '/mnt/assets/';
      const mountPath = `${svMount.replace(/\/$/, '')}/${asset.path || asset.filename}`;
      const baseName = mountPath.replace(/\.[^.]+$/, '');
      src.innerHTML = safeHtml`<span class="term-prompt">$</span> findmnt /mnt/assets
<span class="term-output">TARGET      SOURCE       FSTYPE  OPTIONS
/mnt/assets 127.0.0.1:/  nfs4    rw,relatime,vers=4.2,rsize=1048576,
                                  wsize=1048576,hard,proto=tcp,
                                  sec=sys,addr=127.0.0.1</span>

<span class="term-prompt">$</span> ls -1 ${baseName}*
<span class="term-output">${mountPath + (asset.thumbnailKey ? '\n' + baseName + '.thumb.jpg' : '')}</span>

<span class="term-comment"># reads directly from S3 via filesystem — no boto3.get_object()</span>
<span class="term-prompt">$</span> python3 -c "img = PIL.Image.open('${mountPath}')"`;
    }
  } catch (e) {
    document.getElementById('detail-json').textContent = `Error: ${e.message}`;
  }
}

// ── Event bindings ────────────────────────────────────────────────────────────

function bindEvents() {
  // Sample pack dropdown
  document.getElementById('sample-pack-select').addEventListener('change', e => {
    const pack = samplePacks.find(p => p.id === e.target.value);
    const detail = document.getElementById('sample-pack-detail');
    if (pack) {
      document.getElementById('sp-name').textContent = pack.name;
      document.getElementById('sp-meta').textContent = `${pack.fileCount} files · ${pack.sizeMb} MB`;
      document.getElementById('sp-desc').textContent = pack.description;
      detail.style.display = '';
    } else {
      detail.style.display = 'none';
    }
  });

  // Sample pack load button
  document.getElementById('sp-load-btn').addEventListener('click', async () => {
    const sel = document.getElementById('sample-pack-select');
    const packId = sel.value;
    if (!packId) return;
    const btn = document.getElementById('sp-load-btn');
    btn.textContent = 'Loading...';
    btn.disabled = true;
    try {
      const data = await post('/sample-packs/load', { packId });
      await loadDatasets();
      await openDataset(data.dataset._id);
      sel.value = '';
      document.getElementById('sample-pack-detail').style.display = 'none';
    } catch (err) {
      alert(`Failed to load pack: ${err.message}`);
    } finally {
      btn.textContent = 'Load';
      btn.disabled = false;
    }
  });

  // Dataset sidebar clicks
  document.getElementById('datasets-list').addEventListener('click', e => {
    const item = e.target.closest('.dataset-item');
    if (!item) return;
    openDataset(item.dataset.datasetId);
  });

  // Refresh datasets
  document.getElementById('refresh-datasets-btn').addEventListener('click', loadDatasets);

  // Process button
  document.getElementById('process-btn').addEventListener('click', async () => {
    if (!state.currentDatasetId) return;
    try {
      await post('/process', { datasetId: state.currentDatasetId });
      startPolling();
    } catch (e) {
      alert(`Could not trigger processing: ${e.message}`);
    }
  });

  // Delete dataset
  document.getElementById('delete-dataset-btn').addEventListener('click', async () => {
    if (!state.currentDatasetId) return;
    if (!await showConfirm('Delete this dataset and all its assets?')) return;
    try {
      await del(`/datasets/${state.currentDatasetId}`);
      state.currentDatasetId = null;
      stopPolling();
      document.getElementById('dataset-view').style.display = 'none';
      document.getElementById('empty-state').style.display = '';
      document.getElementById('data-flow').style.display = 'none';
      await loadDatasets();
    } catch (e) {
      alert(`Delete failed: ${e.message}`);
    }
  });

  // Filters
  document.getElementById('filter-type').addEventListener('change', e => {
    state.filterType = e.target.value;
    refreshAssets();
  });
  document.getElementById('filter-status').addEventListener('change', e => {
    state.filterStatus = e.target.value;
    refreshAssets();
  });
  let searchTimer;
  document.getElementById('filter-search').addEventListener('input', e => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.filterSearch = e.target.value;
      refreshAssets();
    }, 300);
  });

  // Load more
  document.getElementById('load-more-btn').addEventListener('click', () => refreshAssets(true));

  // Asset grid clicks (delegated)
  document.getElementById('asset-grid').addEventListener('click', e => {
    const card = e.target.closest('.asset-card');
    if (!card) return;
    openAssetDetail(card.dataset.assetId);
  });

  // Close detail panel
  document.getElementById('detail-close-btn').addEventListener('click', () => {
    document.getElementById('detail-panel').style.display = 'none';
  });
}

// ── Formatters ────────────────────────────────────────────────────────────────

function showConfirm(message) {
  return new Promise(resolve => {
    const overlay = document.getElementById('confirm-modal');
    document.getElementById('confirm-modal-message').textContent = message;
    overlay.style.display = 'flex';

    const okBtn = document.getElementById('confirm-modal-ok');
    const cancelBtn = document.getElementById('confirm-modal-cancel');

    function finish(result) {
      overlay.style.display = 'none';
      okBtn.removeEventListener('click', onOk);
      cancelBtn.removeEventListener('click', onCancel);
      resolve(result);
    }
    function onOk() { finish(true); }
    function onCancel() { finish(false); }

    okBtn.addEventListener('click', onOk);
    cancelBtn.addEventListener('click', onCancel);
  });
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str == null ? '' : String(str);
  return d.innerHTML;
}

// Tagged template literal that auto-escapes all interpolated values.
// Use instead of bare innerHTML assignments with manual esc() calls —
// new interpolations are safe by construction, not by convention.
function safeHtml(strings, ...values) {
  return strings.reduce((acc, str, i) =>
    acc + str + (i < values.length ? esc(values[i]) : ''), '');
}

function fmtBytes(bytes) {
  if (!bytes) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let v = bytes;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

function fmtDuration(seconds) {
  if (!seconds) return '—';
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// ── Start ─────────────────────────────────────────────────────────────────────
init().catch(console.error);
