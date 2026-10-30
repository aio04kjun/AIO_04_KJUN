export class ApiError extends Error {
  constructor(status, code, message, details = []) { super(message); this.status = status; this.code = code; this.details = details; }
}
let csrfPromise, refreshPromise, generation = 0;

async function raw(path, options = {}) {
  let response;
  try { response = await fetch(`/api/v1${path}`, { credentials: 'same-origin', cache: 'no-store', ...options }); }
  catch { throw new ApiError(503, 'NETWORK_ERROR', '연결을 확인하고 다시 시도해 주세요.'); }
  let result;
  try { result = await response.json(); }
  catch { throw new ApiError(502, 'INVALID_RESPONSE', '서버 응답을 확인할 수 없습니다.'); }
  if (!response.ok) {
    const error = result.error || {};
    throw new ApiError(response.status, error.code || 'REQUEST_FAILED', error.message || '요청을 처리하지 못했습니다.', error.details || []);
  }
  return result;
}
async function csrf() {
  if (!csrfPromise) csrfPromise = raw('/auth/csrf').then(r => r.data.csrf_token).catch(e => { csrfPromise = null; throw e; });
  return csrfPromise;
}
async function refresh() {
  if (!refreshPromise) refreshPromise = (async () => {
    const token = await csrf();
    await raw('/auth/refresh', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token }, body: '{}' });
    generation++;
  })().finally(() => { refreshPromise = null; });
  return refreshPromise;
}
export async function api(path, { method = 'GET', body, refreshSession = true } = {}) {
  const started = generation;
  const write = method !== 'GET';
  const send = async () => raw(path, { method, ...(write ? {
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': await csrf() }, body: JSON.stringify(body ?? {})
  } : {}) });
  try { return await send(); }
  catch (error) {
    if (error.code === 'CSRF_FAILED' && write) { csrfPromise = null; return send(); }
    if (error.status === 401 && refreshSession && !path.startsWith('/auth/')) {
      if (generation === started) await refresh();
      return send();
    }
    throw error;
  }
}
