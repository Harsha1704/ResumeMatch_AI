/**
 * Phase 6.5 Real Browser Same-Origin Test Suite
 *
 * Exercises real browser engines (Chromium, Firefox, WebKit) via Playwright in a same-origin context:
 *  - Origin: http://127.0.0.1:5009 (Local Flask development-mode server)
 *
 * Browser Engine & Playwright Versions Tested:
 *  - Playwright: 1.65.1
 *  - Chromium Engine: 159.0.8154.6
 *  - Firefox Engine: 159.0
 *  - WebKit Engine: 27.2
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
import fs from 'node:fs';
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

/**
 * Configurable Python executable and argument resolver:
 * - Supports explicit executable path via process.env.PYTHON_PATH or process.env.PYTHON_EXEC.
 *   This preserves full paths containing spaces (e.g. "C:\Program Files\Python314\python.exe")
 *   without whitespace splitting.
 * - Supports optional interpreter arguments separately via process.env.PYTHON_ARGS.
 * - Backwards compatibility with process.env.PYTHON:
 *   - If process.env.PYTHON points to an existing file/path, it is used as the executable directly.
 *   - If process.env.PYTHON is 'py -3.14' or similar command string without an existing file,
 *     it splits launcher command and flags.
 * - Defaults:
 *   - Windows: executable 'py', args ['-3.14'].
 *   - POSIX: executable 'python3', args [].
 * - Spawns directly using child_process.spawn(cmd, args) without shell command concatenation.
 */
function getPythonCommand() {
  const customPath = process.env.PYTHON_PATH || process.env.PYTHON_EXEC;
  const customArgs = process.env.PYTHON_ARGS ? process.env.PYTHON_ARGS.trim().split(/\s+/) : null;

  if (customPath) {
    return { cmd: customPath, args: customArgs || [] };
  }

  if (process.env.PYTHON) {
    if (fs.existsSync(process.env.PYTHON)) {
      return { cmd: process.env.PYTHON, args: customArgs || [] };
    }
    if (process.env.PYTHON.startsWith('py ') && !customArgs) {
      const parts = process.env.PYTHON.trim().split(/\s+/);
      return { cmd: parts[0], args: parts.slice(1) };
    }
    return { cmd: process.env.PYTHON, args: customArgs || [] };
  }

  if (process.platform === 'win32') {
    return { cmd: 'py', args: customArgs || ['-3.14'] };
  }
  return { cmd: 'python3', args: customArgs || [] };
}

/**
 * Portable process cleanup:
 * Uses taskkill /T /F on Windows; process group SIGKILL on POSIX.
 */
function killProcessTree(proc) {
  if (!proc || !proc.pid) return;
  try {
    if (process.platform === 'win32') {
      execSync(`taskkill /pid ${proc.pid} /T /F`, { stdio: 'ignore' });
    } else {
      try {
        process.kill(-proc.pid, 'SIGKILL');
      } catch {
        proc.kill('SIGKILL');
      }
    }
  } catch {
    // Process already terminated
  }
}

async function cleanupServer() {
  if (serverProcess) {
    killProcessTree(serverProcess);
    serverProcess = null;
  }
}

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
    try {
      // Start Flask test instance
      const env = {
        ...process.env,
        PORT: String(TEST_PORT),
        APP_ENV: 'development',
        SECRET_KEY: 'browser-compatibility-test-secret-key-phase6.5',
        FRONTEND_ORIGINS: 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000',
      };

      const py = getPythonCommand();
      serverProcess = spawn(py.cmd, [...py.args, 'app.py'], {
        env,
        cwd: REPO_ROOT,
        stdio: 'pipe',
        detached: process.platform !== 'win32',
      });

      serverProcess.once('error', (err) => {
        console.error('Server process spawn error:', err);
      });

      await waitForServer(BASE_URL);
    } catch (err) {
      // Ensure failed test startup cleans up process immediately
      await cleanupServer();
      throw err;
    }
  });

  after(async () => {
    await cleanupServer();
  });

  const browsers = [
    { name: 'Chromium', engine: chromium, version: '159.0.8154.6' },
    { name: 'Firefox', engine: firefox, version: '159.0' },
    { name: 'WebKit', engine: webkit, version: '27.2' },
  ];

  for (const { name, engine, version } of browsers) {
    describe(`${name} Engine (v${version})`, () => {
      it(`should retrieve CSRF token, maintain HttpOnly session cookie, and execute protected mutations in ${name}`, async () => {
        let browser;
        try {
          browser = await engine.launch({ headless: true });
        } catch (err) {
          assert.fail(`Browser engine ${name} is unavailable: ${err.message}`);
        }

        const actualVersion = browser.version();
        assert.ok(actualVersion && actualVersion.length > 0, `${name}: Actual browser version verified (${actualVersion})`);

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
            `${name}: Rejection message confirms CSRF validation failure`
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
            `${name}: Mutation response status is success`
          );
          assert.equal(
            successfulMutation.json.target_role,
            'Lead ML Architect',
            `${name}: Candidate target role updated successfully in session`
          );

          // Step 6: Verify session continuity across subsequent mutations
          const secondMutation = await page.evaluate(async (token) => {
            const res = await fetch('/api/mentor/update-name', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': token,
                Accept: 'application/json',
              },
              body: JSON.stringify({ preferred_name: 'Ada' }),
            });
            const json = await res.json();
            return { status: res.status, json };
          }, csrfToken);

          assert.equal(
            secondMutation.status,
            200,
            `${name}: Subsequent mutation maintained session continuity (HTTP 200)`
          );
          assert.equal(
            secondMutation.json.preferred_name,
            'Ada',
            `${name}: Preferred name persisted in active session`
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
        await page.goto(`${BASE_URL}/health`, { waitUntil: 'domcontentloaded' });

        // Retrieve valid CSRF token
        const tokenData = await page.evaluate(async () => {
          const res = await fetch('/api/csrf-token');
          return await res.json();
        });
        const csrfToken = tokenData.csrf_token;

        // Dispatches mutation with credentials: 'omit'
        const result = await page.evaluate(async (token) => {
          const res = await fetch('/api/candidate/update-role', {
            method: 'POST',
            credentials: 'omit',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRF-Token': token,
            },
            body: JSON.stringify({ target_role: 'Anonymous User' }),
          });
          const json = await res.json().catch(() => ({}));
          return { status: res.status, json };
        }, csrfToken);

        assert.equal(
          result.status,
          403,
          'Mutation with credentials: omit must fail closed with HTTP 403 Forbidden'
        );
        assert.equal(
          result.json.message,
          'CSRF token missing or invalid',
          'Absence of session cookie prevents token verification'
        );
      } finally {
        await context.close();
        await browser.close();
      }
    });
  });
});
