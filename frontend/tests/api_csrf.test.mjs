/**
 * frontend/tests/api_csrf.test.mjs
 * Unit tests for frontend CSRF token retrieval, fail-closed abortion,
 * caching, and header attachment in `frontend/src/services/api.ts`.
 */

import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { api, getCsrfToken, clearCsrfToken } from '../src/services/api.ts';

// Track fetch calls
let fetchCalls = [];
const originalFetch = globalThis.fetch;

beforeEach(() => {
  fetchCalls = [];
  clearCsrfToken();
});

test('1. Mutation aborts fail-closed before endpoint fetch if CSRF token retrieval fails', async () => {
  globalThis.fetch = async (url, options = {}) => {
    fetchCalls.push({ url, options });
    if (url.includes('/api/csrf-token')) {
      return {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ status: 'error', message: 'CSRF service unavailable' }),
      };
    }
    // If the mutation endpoint is called, it would fail the test requirement
    return {
      ok: true,
      status: 200,
      json: async () => ({ status: 'success' }),
    };
  };

  try {
    await assert.rejects(
      async () => {
        await api.updateCandidateName('Alice');
      },
      (err) => {
        assert.match(err.message, /Failed to retrieve CSRF token|CSRF token could not be established/);
        return true;
      }
    );

    // Verify that /api/mentor/update-name was NEVER invoked
    const mutationCalls = fetchCalls.filter((c) => c.url.includes('/api/mentor/update-name'));
    assert.strictEqual(mutationCalls.length, 0, 'Mutation endpoint MUST NOT be called when CSRF token retrieval fails');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('2. Successful token retrieval attaches X-CSRF-Token and credentials: include', async () => {
  const TEST_TOKEN = 'mock_crypto_csrf_token_abcdef123456';

  globalThis.fetch = async (url, options = {}) => {
    fetchCalls.push({ url, options });
    if (url.includes('/api/csrf-token')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: 'success', csrf_token: TEST_TOKEN }),
      };
    }
    if (url.includes('/api/mentor/update-name')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: 'success', preferred_name: 'Bob', mentor_title: "Bob's Career Mentor" }),
      };
    }
    throw new Error(`Unexpected endpoint: ${url}`);
  };

  try {
    const result = await api.updateCandidateName('Bob');
    assert.strictEqual(result.status, 'success');
    assert.strictEqual(result.preferred_name, 'Bob');

    // Verify /api/csrf-token was called with credentials: 'include'
    const csrfCall = fetchCalls.find((c) => c.url.includes('/api/csrf-token'));
    assert.ok(csrfCall, 'Must fetch /api/csrf-token');
    assert.strictEqual(csrfCall.options.credentials, 'include');

    // Verify /api/mentor/update-name was called with X-CSRF-Token and credentials: 'include'
    const mutCall = fetchCalls.find((c) => c.url.includes('/api/mentor/update-name'));
    assert.ok(mutCall, 'Must call mutation endpoint');
    assert.strictEqual(mutCall.options.headers['X-CSRF-Token'], TEST_TOKEN);
    assert.strictEqual(mutCall.options.credentials, 'include');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('3. Token caching avoids redundant /api/csrf-token fetches on subsequent mutations', async () => {
  const TEST_TOKEN = 'cached_token_777';
  let csrfFetchCount = 0;

  globalThis.fetch = async (url, options = {}) => {
    fetchCalls.push({ url, options });
    if (url.includes('/api/csrf-token')) {
      csrfFetchCount++;
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: 'success', csrf_token: TEST_TOKEN }),
      };
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({ status: 'success' }),
    };
  };

  try {
    // First mutation fetches token
    await api.updateCandidateName('Carol');
    assert.strictEqual(csrfFetchCount, 1);

    // Second mutation uses cached token
    await api.updateCandidateRole('Site Reliability Engineer');
    assert.strictEqual(csrfFetchCount, 1, 'Second mutation must reuse cached CSRF token without refetching');

    // Third mutation uses cached token
    await api.confirmEducation('Master of Science');
    assert.strictEqual(csrfFetchCount, 1, 'Third mutation must reuse cached CSRF token without refetching');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('4. HTTP 403 Forbidden clears cached token and does not automatically replay mutation', async () => {
  const INITIAL_TOKEN = 'expired_token_001';
  const FRESH_TOKEN = 'fresh_token_002';
  let csrfFetchCount = 0;
  let mutationAttemptCount = 0;

  globalThis.fetch = async (url, options = {}) => {
    fetchCalls.push({ url, options });
    if (url.includes('/api/csrf-token')) {
      csrfFetchCount++;
      const tok = csrfFetchCount === 1 ? INITIAL_TOKEN : FRESH_TOKEN;
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: 'success', csrf_token: tok }),
      };
    }
    if (url.includes('/api/mentor/reset-progress')) {
      mutationAttemptCount++;
      // Reject with 403 Forbidden
      return {
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({ status: 'error', message: 'CSRF token missing or invalid' }),
      };
    }
    throw new Error(`Unexpected endpoint: ${url}`);
  };

  try {
    await assert.rejects(
      async () => {
        await api.resetMentorProgress();
      },
      (err) => {
        assert.match(err.message, /CSRF token missing or invalid|Security check failed/);
        return true;
      }
    );

    // Verify mutation was called exactly ONCE (no automatic replay that could duplicate side effects)
    assert.strictEqual(mutationAttemptCount, 1, 'Must not automatically replay mutation after 403');

    // Verify that cached token was cleared: a subsequent call will request /api/csrf-token again
    const token = await getCsrfToken();
    assert.strictEqual(token, FRESH_TOKEN);
    assert.strictEqual(csrfFetchCount, 2, 'Token cache was cleared on 403, allowing fresh re-acquisition');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('5. analyzeResume multipart upload aborts fail-closed if CSRF retrieval fails', async () => {
  globalThis.fetch = async (url, options = {}) => {
    fetchCalls.push({ url, options });
    if (url.includes('/api/csrf-token')) {
      return {
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
        json: async () => ({ error: 'Down' }),
      };
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({ status: 'success' }),
    };
  };

  try {
    const fakeFormData = { append: () => {} };
    await assert.rejects(
      async () => {
        await api.analyzeResume(fakeFormData);
      },
      (err) => {
        assert.match(err.message, /Failed to retrieve CSRF token|CSRF token could not be established/);
        return true;
      }
    );

    // Verify /api/analyze was NOT called
    const analyzeCalls = fetchCalls.filter((c) => c.url.includes('/api/analyze'));
    assert.strictEqual(analyzeCalls.length, 0, 'POST /api/analyze MUST NOT be called when CSRF token retrieval fails');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('6. analyzeResume multipart upload attaches X-CSRF-Token and credentials on success', async () => {
  const TEST_TOKEN = 'upload_token_999';

  globalThis.fetch = async (url, options = {}) => {
    fetchCalls.push({ url, options });
    if (url.includes('/api/csrf-token')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: 'success', csrf_token: TEST_TOKEN }),
      };
    }
    if (url.includes('/api/analyze')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: 'success', analysis_id: 'aid_123', data: {} }),
      };
    }
    throw new Error(`Unexpected endpoint: ${url}`);
  };

  try {
    const fakeFormData = { append: () => {} };
    const res = await api.analyzeResume(fakeFormData);
    assert.strictEqual(res.status, 'success');
    assert.strictEqual(res.analysis_id, 'aid_123');

    const analyzeCall = fetchCalls.find((c) => c.url.includes('/api/analyze'));
    assert.ok(analyzeCall);
    assert.strictEqual(analyzeCall.options.headers['X-CSRF-Token'], TEST_TOKEN);
    assert.strictEqual(analyzeCall.options.credentials, 'include');
  } finally {
    globalThis.fetch = originalFetch;
  }
});
