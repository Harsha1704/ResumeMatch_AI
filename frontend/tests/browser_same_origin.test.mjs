/**
 * Phase 6.4 Real Browser Same-Origin Test Suite
 *
 * Exercises real browser engines (Chromium, Firefox, WebKit) via Playwright in a same-origin context:
 *  - Origin: http://127.0.0.1:5009 (Local Flask development-mode server)
 *
 * Verifies:
 *  1. Live CSRF token retrieval via browser fetch.
 *  2. HttpOnly session cookie persistence in browser cookie jar.
 *  3. Protected mutation without token is rejected with HTTP 403 Forbidden.
 *  4. Protected mutation with valid token succeeds with HTTP 200 OK.
 *  5. Session continuity across sequential mutations.
 *  6. Demonstrates that credentials: 'omit' drops cookies and causes session-backed mutations to fail.
 */

import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawn, execSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium, firefox, webkit } from 'playwright';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..');

const TEST_PORT = 5009;
const BASE_URL = `http://127.0.0.1:${TEST_PORT}`;
let serverProcess = null;

// Helper: poll until server is ready
async function waitForServer(url, timeoutMs = 25000) {
  const start = Date.now();
  let lastErr = '';
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${url}/health`);
      if (res.ok) return true;
    } catch (e) {
      lastErr = e.message;
    }
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  throw new Error(`Server failed to start at ${url} within ${timeoutMs}ms (last error: ${lastErr})`);
}

describe('Playwright Real Browser Same-Origin Suite (HTTP)', () => {
  before(async () => {
    // Start Flask test instance
    const env = {
      ...process.env,
      PORT: String(TEST_PORT),
      APP_ENV: 'development',
      SECRET_KEY: 'browser-compatibility-test-secret-key-phase6.3',
      FRONTEND_ORIGINS: 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000',
    };

    serverProcess = spawn('py', ['-3.14', 'app.py'], {
      env,
      cwd: REPO_ROOT,
      stdio: 'pipe',
    });

    await waitForServer(BASE_URL);
  });

  after(async () => {
    if (serverProcess?.pid) {
      try {
        execSync(`taskkill /pid ${serverProcess.pid} /T /F`);
      } catch {
        // Process may already have terminated
      }
    }
  });

  const browsers = [
    { name: 'Chromium', engine: chromium },
    { name: 'Firefox', engine: firefox },
    { name: 'WebKit', engine: webkit },
  ];

  for (const { name, engine } of browsers) {
    describe(`${name} Engine`, () => {
      it(`should retrieve CSRF token, maintain HttpOnly session cookie, and execute protected mutations in ${name}`, async () => {
        let browser;
        try {
          browser = await engine.launch({ headless: true });
        } catch (err) {
          assert.fail(`Browser engine ${name} is unavailable: ${err.message}`);
        }

        const context = await browser.newContext();
        const page = await context.newPage();

        try {
          // Step 1: Navigate to base origin to establish security origin
          await page.goto(`${BASE_URL}/health`, { waitUntil: 'domcontentloaded' });

          // Step 2: Retrieve CSRF token via real browser fetch
          const tokenData = await page.evaluate(async () => {
            const res = await fetch('/api/csrf-token', {
              headers: { Accept: 'application/json' },
            });
            const json = await res.json();
            return { status: res.status, json };
          });

          assert.equal(tokenData.status, 200, `${name}: GET /api/csrf-token returned HTTP 200`);
          assert.equal(tokenData.json.status, 'success', `${name}: CSRF response status is success`);
          assert.ok(
            typeof tokenData.json.csrf_token === 'string' && tokenData.json.csrf_token.length === 64,
            `${name}: CSRF token is a valid 64-character hex string`
          );
          const csrfToken = tokenData.json.csrf_token;

          // Step 3: Inspect browser context cookies for session cookie and attributes
          const cookies = await context.cookies(BASE_URL);
          const sessionCookie = cookies.find((c) => c.name === 'session');

          assert.ok(sessionCookie, `${name}: 'session' cookie is present in browser cookie jar`);
          assert.equal(sessionCookie.httpOnly, true, `${name}: session cookie has httpOnly=true`);
          assert.ok(sessionCookie.value.length > 0, `${name}: session cookie value is non-empty`);
          // In development mode, Flask session cookie sameSite is 'Lax'
          assert.match(
            sessionCookie.sameSite.toLowerCase(),
            /lax|none/,
            `${name}: session cookie has valid sameSite attribute`
          );

          // Step 4: Verify protected mutation without CSRF token is REJECTED (403 Forbidden)
          const rejectedMutation = await page.evaluate(async () => {
            const res = await fetch('/api/candidate/update-role', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Accept: 'application/json',
              },
              body: JSON.stringify({ target_role: 'Lead ML Architect' }),
            });
            const json = await res.json().catch(() => ({}));
            return { status: res.status, json };
          });

          assert.equal(
            rejectedMutation.status,
            403,
            `${name}: Mutation without CSRF token must return HTTP 403 Forbidden`
          );
          assert.equal(
            rejectedMutation.json.message,
            'CSRF token missing or invalid',
            `${name}: Rejection message confirms CSRF validation`
          );

          // Step 5: Verify protected mutation with valid CSRF token SUCCEEDS (200 OK)
          const successfulMutation = await page.evaluate(async (token) => {
            const res = await fetch('/api/candidate/update-role', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': token,
                Accept: 'application/json',
              },
              body: JSON.stringify({ target_role: 'Lead ML Architect' }),
            });
            const json = await res.json();
            return { status: res.status, json };
          }, csrfToken);

          assert.equal(
            successfulMutation.status,
            200,
            `${name}: Mutation with valid CSRF token returned HTTP 200 OK`
          );
          assert.equal(
            successfulMutation.json.status,
            'success',
            `${name}: Mutation response indicates success`
          );
          assert.equal(
            successfulMutation.json.target_role,
            'Lead ML Architect',
            `${name}: Target role state updated correctly in session`
          );

          // Step 6: Verify session continuity across a second protected mutation
          const secondMutation = await page.evaluate(async (token) => {
            const res = await fetch('/api/mentor/update-name', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': token,
                Accept: 'application/json',
              },
              body: JSON.stringify({ preferred_name: 'Elena' }),
            });
            const json = await res.json();
            return { status: res.status, json };
          }, csrfToken);

          assert.equal(
            secondMutation.status,
            200,
            `${name}: Second mutation in same session returned HTTP 200 OK`
          );
          assert.equal(
            secondMutation.json.preferred_name,
            'Elena',
            `${name}: Candidate name updated across persistent session`
          );
        } finally {
          await context.close();
          await browser.close();
        }
      });
    });
  }

  describe('Empirical Cross-Origin Cookie Behavior', () => {
    it('demonstrates that credentials: omit drops cookies and fails session-backed mutations', async () => {
      const browser = await chromium.launch({ headless: true });
      const context = await browser.newContext();
      const page = await context.newPage();

      try {
        await page.goto(`${BASE_URL}/health`);

        // Obtain token
        const tokenRes = await page.evaluate(async () => {
          const r = await fetch('/api/csrf-token');
          return r.json();
        });
        const token = tokenRes.csrf_token;

        // Make mutation with credentials: 'omit'
        const omitRes = await page.evaluate(async (tok) => {
          const r = await fetch('/api/candidate/update-role', {
            method: 'POST',
            credentials: 'omit',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRF-Token': tok,
            },
            body: JSON.stringify({ target_role: 'Staff Engineer' }),
          });
          const json = await r.json().catch(() => ({}));
          return { status: r.status, json };
        }, token);

        // When session cookie is omitted by browser, backend has empty session -> 403 CSRF missing or invalid
        assert.equal(
          omitRes.status,
          403,
          'Browser omitting session cookie results in HTTP 403 Forbidden'
        );
        assert.equal(
          omitRes.json.message,
          'CSRF token missing or invalid',
          'Omitting credentials drops session context in real browser'
        );
      } finally {
        await context.close();
        await browser.close();
      }
    });
  });
});
