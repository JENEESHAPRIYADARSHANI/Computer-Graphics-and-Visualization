// Thin fetch wrapper around api.py. Every call takes the shared db path,
// which App.jsx holds as state and passes into every repository call.

async function asJson(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore, keep statusText
    }
    throw new Error(detail);
  }
  return res.json();
}

export function startProcessSheet({ imageFile, xmlFile, dbPath }) {
  const form = new FormData();
  form.append('image', imageFile);
  if (xmlFile) form.append('xml', xmlFile);
  form.append('db_path', dbPath);
  return fetch('/api/process', { method: 'POST', body: form }).then(asJson);
}

export function getProcessStatus(jobId) {
  return fetch(`/api/process/${jobId}`).then(asJson);
}

export function getStudents(dbPath) {
  return fetch(`/api/students?db=${encodeURIComponent(dbPath)}`).then(asJson);
}

export function getOverview(dbPath) {
  return fetch(`/api/overview?db=${encodeURIComponent(dbPath)}`).then(asJson);
}

export function chartUrl(studentIndex, dbPath) {
  return `/api/chart/${encodeURIComponent(studentIndex)}?db=${encodeURIComponent(dbPath)}&t=${Date.now()}`;
}

export function getInvestigate(studentIndex, dbPath) {
  return fetch(`/api/investigate/${encodeURIComponent(studentIndex)}?db=${encodeURIComponent(dbPath)}`).then(asJson);
}

export function matchImageUrl(studentIndex, sheetA, sheetB, dbPath) {
  const params = new URLSearchParams({ sheet_a: sheetA, sheet_b: sheetB, db: dbPath, t: Date.now() });
  return `/api/investigate/${encodeURIComponent(studentIndex)}/match-image?${params}`;
}

export function deleteSheet({ sheetId, jobId, dbPath }) {
  const params = new URLSearchParams({ db: dbPath });
  if (jobId) params.set('job_id', jobId);
  return fetch(`/api/sheet/${encodeURIComponent(sheetId)}?${params}`, { method: 'DELETE' }).then(asJson);
}

// Full reset: every upload, every processed sheet, every DB row for dbPath.
export function resetAll(dbPath) {
  const params = new URLSearchParams({ db: dbPath });
  return fetch(`/api/reset?${params}`, { method: 'DELETE' }).then(asJson);
}
