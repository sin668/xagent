export class ApiRequestError extends Error {
  constructor(message, { endpoint, status } = {}) {
    super(message);
    this.name = 'ApiRequestError';
    this.endpoint = endpoint || 'Unknown';
    this.status = status || 0;
  }
}

function normalizeBaseUrl(baseUrl) {
  return String(baseUrl || '').replace(/\/+$/, '');
}

function joinUrl(baseUrl, endpoint) {
  const normalizedEndpoint = String(endpoint || '').startsWith('/') ? endpoint : `/${endpoint}`;
  return `${normalizeBaseUrl(baseUrl)}${normalizedEndpoint}`;
}

function resolveRequest() {
  if (typeof fetch === 'function') {
    return (url, options) => fetch(url, options);
  }

  if (globalThis.uni?.request) {
    return (url, options) =>
      new Promise((resolve, reject) => {
        globalThis.uni.request({
          url,
          method: options.method,
          data: options.body ? JSON.parse(options.body) : undefined,
          header: options.headers,
          success(response) {
            resolve({
              ok: response.statusCode >= 200 && response.statusCode < 300,
              status: response.statusCode,
              json: async () => response.data,
            });
          },
          fail: reject,
        });
      });
  }

  throw new ApiRequestError('No request implementation is available.');
}

export function getApiBaseUrl({ env = import.meta.env || {}, locationOrigin = globalThis.location?.origin } = {}) {
  if (env.VITE_API_BASE_URL) {
    return env.VITE_API_BASE_URL;
  }

  if (locationOrigin && /localhost|127\.0\.0\.1/.test(locationOrigin)) {
    return 'http://localhost:8000';
  }

  return '/api';
}

export function createApiClient({ baseUrl = getApiBaseUrl(), request = resolveRequest() } = {}) {
  async function send(endpoint, { method = 'GET', body } = {}) {
    const response = await request(joinUrl(baseUrl, endpoint), {
      method,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: body == null ? undefined : JSON.stringify(body),
    });
    const payload = await response.json();

    if (!response.ok) {
      const detail = payload?.detail || payload?.message || `HTTP ${response.status}`;
      throw new ApiRequestError(String(detail), { endpoint, status: response.status });
    }

    return payload;
  }

  return {
    get(endpoint) {
      return send(endpoint);
    },
    post(endpoint, body) {
      return send(endpoint, { method: 'POST', body });
    },
  };
}

export const apiClient = createApiClient();
