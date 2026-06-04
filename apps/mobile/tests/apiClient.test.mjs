import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  ApiRequestError,
  createApiClient,
  getApiBaseUrl,
} from '../src/services/apiClient.js';

test('api client builds URLs from configured base URL and parses JSON responses', async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: 'http://api.example.test/',
    request: async (url, options) => {
      calls.push({ url, options });
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: 'ok' }),
      };
    },
  });

  const result = await client.get('/health');

  assert.deepEqual(result, { status: 'ok' });
  assert.equal(calls[0].url, 'http://api.example.test/health');
  assert.equal(calls[0].options.method, 'GET');
});

test('api client surfaces non-2xx responses as ApiRequestError', async () => {
  const client = createApiClient({
    baseUrl: 'http://api.example.test',
    request: async () => ({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'database unavailable' }),
    }),
  });

  await assert.rejects(() => client.get('/customers/outreach-candidates'), {
    name: 'ApiRequestError',
    status: 500,
    message: /database unavailable/,
  });
});

test('api base URL falls back to localhost backend in H5 development', () => {
  assert.equal(getApiBaseUrl({ env: {}, locationOrigin: 'http://localhost:5176' }), 'http://localhost:8000');
  assert.equal(getApiBaseUrl({ env: { VITE_API_BASE_URL: 'http://api.local' } }), 'http://api.local');
});

test('ApiRequestError keeps endpoint and status for UI fallback decisions', () => {
  const error = new ApiRequestError('failed', { endpoint: '/health', status: 503 });

  assert.equal(error.endpoint, '/health');
  assert.equal(error.status, 503);
});
