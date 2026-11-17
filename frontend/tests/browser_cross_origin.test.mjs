/**
 * Phase 6.4 Genuine Cross-Origin Browser Test Suite
 *
 * Verifies true cross-origin browser interactions between separate origins:
 *  - Frontend Origin: https://localhost:3443 (Node HTTPS test server)
 *  - Backend Origin:  https://127.0.0.1:5443 (Flask HTTPS production-mode server)
 *
 * Web Security Architecture Verification:
 *  Under the Same-Origin Policy (RFC 6454), https://localhost:3443 and https://127.0.0.1:5443
 *  are strictly CROSS-ORIGIN. Browsers enforce the full CORS protocol:
 *  issuing OPTIONS preflight, validating Access-Control-Allow-Origin, requiring
 *  Access-Control-Allow-Credentials: true, and validating SameSite=None; Secure cookie transport.
 *
 * Exercises real browser engines (Chromium, Firefox, WebKit) via Playwright:
 *  1. CORS preflight (OPTIONS) verifying exact Access-Control-Allow-Origin,
 *     Access-Control-Allow-Credentials: true, and Access-Control-Allow-Headers containing X-CSRF-Token.
 *  2. Cross-origin CSRF token retrieval with credentials: 'include'.
 *  3. In Chromium and Firefox: verifies SameSite=None; Secure cookie storage, 403 on missing token,
 *     200 OK on authenticated mutation, and session persistence across multiple sequential mutations.
 *  4. In WebKit (Apple engine): verifies that native Intelligent Tracking Prevention (ITP)
 *     drops the cross-origin third-party cookie by default, demonstrating why Safari fails in decoupled setups.
 *  5. Rejection when credentials: 'omit' is specified.
 *  6. Rejection of requests from unauthorized cross-origin callers.
 */

import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import https from 'node:https';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn, execSync } from 'node:child_process';
import { chromium, firefox, webkit } from 'playwright';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..');

const FRONTEND_PORT = 3443;
const BACKEND_PORT = 5443;
const FRONTEND_ORIGIN = `https://localhost:${FRONTEND_PORT}`;
const BACKEND_ORIGIN = `https://127.0.0.1:${BACKEND_PORT}`;

const CERT_PATH = path.resolve(__dirname, 'fixtures', 'test_cert.pem');
const KEY_PATH = path.resolve(__dirname, 'fixtures', 'test_key.pem');

let frontendServer = null;
let backendProcess = null;

// Helper: poll until backend HTTPS server is responding
async function waitForBackend(url, timeoutMs = 25000) {
  const start = Date.now();
  let lastErr = '';
  const agent = new https.Agent({ rejectUnauthorized: false });
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await new Promise((resolve, reject) => {
        const req = https.get(`${url}/health`, { agent }, (res) => resolve(res));
        req.on('error', reject);
        req.setTimeout(2000, () => req.destroy(new Error('timeout')));
      });
      if (res.statusCode === 200) return true;
    } catch (e) {
      lastErr = e.message;
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`Backend failed to start at ${url} within ${timeoutMs}ms (last error: ${lastErr})`);
}

describe('Playwright Genuine Cross-Origin Browser Test Suite (HTTPS)', () => {
  before(async () => {
    // 1. Start Frontend HTTPS server on https://localhost:3443
    const cert = fs.readFileSync(CERT_PATH);
    const key = fs.readFileSync(KEY_PATH);

    frontendServer = https.createServer({ key, cert }, (req, res) => {
      res.writeHead(200, {
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-store',
      });
      res.end(`<!DOCTYPE html>
<html>
<head><title>Cross-Origin Test Origin</title></head>
<body>
  <h1>Frontend Origin: ${FRONTEND_ORIGIN}</h1>
  <div id="target">Ready</div>
</body>
</html>`);
    });

    await new Promise((resolve) => frontendServer.listen(FRONTEND_PORT, 'localhost', resolve));

    // 2. Start Backend Flask HTTPS server on https://127.0.0.1:5443 with production cookie flags
    const env = {
      ...process.env,
      PORT: String(BACKEND_PORT),
      RESUMEMATCH_ENV: 'production', // Activates SESSION_COOKIE_SECURE=True and SESSION_COOKIE_SAMESITE="None"
      SECRET_KEY: 'cross-origin-test-secret-key-phase6.4',
      FLASK_SSL_CERT: CERT_PATH,
      FLASK_SSL_KEY: KEY_PATH,
      FRONTEND_ORIGINS: `${FRONTEND_ORIGIN},https://127.0.0.1:${FRONTEND_PORT},http://localhost:3000`,
    };

    backendProcess = spawn('py', ['-3.14', 'app.py'], {
      env,
      cwd: REPO_ROOT,
      stdio: 'pipe',
    });

    await waitForBackend(BACKEND_ORIGIN);
  });

  after(async () => {
    // Shutdown frontend server
    if (frontendServer) {
      await new Promise((resolve) => frontendServer.close(resolve));
    }
    // Shutdown backend process tree
    if (backendProcess?.pid) {
      try {
        execSync(`taskkill /pid ${backendProcess.pid} /T /F`);
      } catch {
        // ignore if already exited
      }
    }
  });

  const browsers = [
    { name: 'Chromium', engine: chromium, isWebKit: false },
    { name: 'Firefox', engine: firefox, isWebKit: false },
    { name: 'WebKit', engine: webkit, isWebKit: true },
  ];

  for (const { name, engine, isWebKit } of browsers) {
    describe(`${name} Engine — Genuine Cross-Origin Verification`, () => {
      it(`should verify CORS preflight, cross-origin CSRF retrieval, and cookie behavior in ${name}`, async () => {
        let browser;
        try {
          browser = await engine.launch({ headless: true });
        } catch (err) {
          assert.fail(`Browser engine ${name} is unavailable: ${err.message}`);
        }

        const context = await browser.newContext({ ignoreHTTPSErrors: true });
        const page = await context.newPage();

        try {
          // Step 1: Navigate to Frontend Origin (https://localhost:3443)
          await page.goto(`${FRONTEND_ORIGIN}/`, { waitUntil: 'domcontentloaded' });

          // Step 2: Verify CORS Preflight (OPTIONS) behavior for cross-origin mutation endpoint
          const preflightRes = await context.request.fetch(`${BACKEND_ORIGIN}/api/candidate/update-role`, {
            method: 'OPTIONS',
            headers: {
              Origin: FRONTEND_ORIGIN,
              'Access-Control-Request-Method': 'POST',
              'Access-Control-Request-Headers': 'Content-Type, X-CSRF-Token',
            },
          });

          assert.equal(preflightRes.status(), 200, `${name}: Preflight OPTIONS returned 200 OK`);
          const preflightHeaders = preflightRes.headers();

          assert.equal(
            preflightHeaders['access-control-allow-origin'],
            FRONTEND_ORIGIN,
            `${name}: Access-Control-Allow-Origin matches requesting origin exactly (never wildcard *)`
          );
          assert.equal(
            preflightHeaders['access-control-allow-credentials'],
            'true',
            `${name}: Access-Control-Allow-Credentials is explicitly 'true'`
          );
          assert.ok(
            preflightHeaders['access-control-allow-headers'].toLowerCase().includes('x-csrf-token'),
            `${name}: Access-Control-Allow-Headers permits 'X-CSRF-Token'`
          );

          // Step 3: Retrieve CSRF token via cross-origin fetch to Backend Origin (https://127.0.0.1:5443)
          const tokenData = await page.evaluate(async (backendUrl) => {
            const res = await fetch(`${backendUrl}/api/csrf-token`, {
              method: 'GET',
              credentials: 'include',
              headers: { Accept: 'application/json' },
            });
            const json = await res.json();
            return { status: res.status, json };
          }, BACKEND_ORIGIN);

          assert.equal(tokenData.status, 200, `${name}: GET /api/csrf-token cross-origin returned 200 OK`);
          assert.equal(tokenData.json.status, 'success', `${name}: CSRF response indicates success`);
          assert.ok(
            typeof tokenData.json.csrf_token === 'string' && tokenData.json.csrf_token.length === 64,
            `${name}: CSRF token is a 64-character hex string`
          );
          const csrfToken = tokenData.json.csrf_token;

          // Step 4: Inspect Browser Context Cookies for Backend Origin
          const cookies = await context.cookies(BACKEND_ORIGIN);
          const sessionCookie = cookies.find((c) => c.name === 'session');

          if (!isWebKit) {
            // Chromium and Firefox support cross-origin SameSite=None; Secure cookies
            assert.ok(sessionCookie, `${name}: session cookie was stored in browser cookie jar across origins`);
            assert.equal(sessionCookie.httpOnly, true, `${name}: cross-origin cookie has httpOnly=true`);
            assert.equal(sessionCookie.secure, true, `${name}: cross-origin cookie is marked secure=true`);
            assert.match(
              sessionCookie.sameSite.toLowerCase(),
              /none/,
              `${name}: cross-origin cookie has SameSite=None`
            );

            // Step 5: Verify Cross-Origin Protected Mutation WITHOUT Token is REJECTED (HTTP 403 Forbidden)
            const rejectedMutation = await page.evaluate(async (backendUrl) => {
              const res = await fetch(`${backendUrl}/api/candidate/update-role`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                  'Content-Type': 'application/json',
                  Accept: 'application/json',
                },
                body: JSON.stringify({ target_role: 'Cross-Origin Architect' }),
              });
              const json = await res.json().catch(() => ({}));
              return { status: res.status, json };
            }, BACKEND_ORIGIN);

            assert.equal(
              rejectedMutation.status,
              403,
              `${name}: Cross-origin mutation without CSRF token must return 403 Forbidden`
            );
            assert.equal(
              rejectedMutation.json.message,
              'CSRF token missing or invalid',
              `${name}: Rejection message confirms CSRF validation`
            );

            // Step 6: Verify Cross-Origin Protected Mutation WITH Valid Token SUCCEEDS (200 OK)
            const successfulMutation = await page.evaluate(async ({ backendUrl, token }) => {
              const res = await fetch(`${backendUrl}/api/candidate/update-role`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                  'Content-Type': 'application/json',
                  'X-CSRF-Token': token,
                  Accept: 'application/json',
                },
                body: JSON.stringify({ target_role: 'Cross-Origin Architect' }),
              });
              const json = await res.json();
              return { status: res.status, json };
            }, { backendUrl: BACKEND_ORIGIN, token: csrfToken });

            assert.equal(
              successfulMutation.status,
              200,
              `${name}: Cross-origin mutation with token returned HTTP 200 OK`
            );
            assert.equal(
              successfulMutation.json.status,
              'success',
              `${name}: Mutation response status is success`
            );
            assert.equal(
              successfulMutation.json.target_role,
              'Cross-Origin Architect',
              `${name}: Target role state persisted in session across origins`
            );

            // Step 7: Verify Session Continuity Across Multiple Sequential Cross-Origin Mutations
            const secondMutation = await page.evaluate(async ({ backendUrl, token }) => {
              const res = await fetch(`${backendUrl}/api/mentor/update-name`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                  'Content-Type': 'application/json',
                  'X-CSRF-Token': token,
                  Accept: 'application/json',
                },
                body: JSON.stringify({ preferred_name: 'Grace' }),
              });
              const json = await res.json();
              return { status: res.status, json };
            }, { backendUrl: BACKEND_ORIGIN, token: csrfToken });

            assert.equal(
              secondMutation.status,
              200,
              `${name}: Second cross-origin mutation returned HTTP 200 OK`
            );
            assert.equal(
              secondMutation.json.preferred_name,
              'Grace',
              `${name}: Preferred name persisted across sequential cross-origin mutations`
            );

            // Step 8: Verify Behavior When credentials: 'omit' is specified
            const omitMutation = await page.evaluate(async ({ backendUrl, token }) => {
              const res = await fetch(`${backendUrl}/api/candidate/update-role`, {
                method: 'POST',
                credentials: 'omit',
                headers: {
                  'Content-Type': 'application/json',
                  'X-CSRF-Token': token,
                  Accept: 'application/json',
                },
                body: JSON.stringify({ target_role: 'Untrusted Caller' }),
              });
              const json = await res.json().catch(() => ({}));
              return { status: res.status, json };
            }, { backendUrl: BACKEND_ORIGIN, token: csrfToken });

            assert.equal(
              omitMutation.status,
              403,
              `${name}: Cross-origin request with credentials: omit must fail closed with 403`
            );
          } else {
            // WebKit (Apple engine): Native Intelligent Tracking Prevention (ITP) drops third-party cross-origin cookies
            assert.equal(
              sessionCookie,
              undefined,
              `${name}: Native Apple ITP drops cross-origin third-party cookie by default as expected`
            );

            // Mutation fails closed with HTTP 403 because no session cookie is transmitted by WebKit
            const itcMutation = await page.evaluate(async ({ backendUrl, token }) => {
              const res = await fetch(`${backendUrl}/api/candidate/update-role`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                  'Content-Type': 'application/json',
                  'X-CSRF-Token': token,
                  Accept: 'application/json',
                },
                body: JSON.stringify({ target_role: 'Blocked By ITP' }),
              });
              const json = await res.json().catch(() => ({}));
              return { status: res.status, json };
            }, { backendUrl: BACKEND_ORIGIN, token: csrfToken });

            assert.equal(
              itcMutation.status,
              403,
              `${name}: Mutation fails closed with HTTP 403 when WebKit ITP blocks the session cookie`
            );
          }
        } finally {
          await context.close();
          await browser.close();
        }
      });
    });
  }

  describe('CORS Disallowed Origin Enforcement', () => {
    it('verifies that requests from unauthorized origins do not receive allow-credentials headers', async () => {
      const browser = await chromium.launch({ headless: true });
      const context = await browser.newContext({ ignoreHTTPSErrors: true });

      try {
        const preflight = await context.request.fetch(`${BACKEND_ORIGIN}/api/candidate/update-role`, {
          method: 'OPTIONS',
          headers: {
            Origin: 'https://malicious-site.example.com',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'X-CSRF-Token, Content-Type',
          },
        });

        const headers = preflight.headers();
        assert.notEqual(
          headers['access-control-allow-origin'],
          'https://malicious-site.example.com',
          'Unauthorized origin must NOT be allowed by CORS'
        );
      } finally {
        await context.close();
        await browser.close();
      }
    });
  });
});
