/**
 * Phase 7.3 Genuine Same-Site Subdomain Browser Test Suite (HTTPS)
 *
 * Verifies same-site subdomain browser interactions under the production architecture:
 *  - Frontend Origin: https://app.resumematch.test:8443 (Node HTTPS test server)
 *  - Backend Origin:  https://api.resumematch.test:9443 (Flask HTTPS production-mode server)
 *  - Both origins share the registrable domain `resumematch.test` (RFC 6265bis same-site).
 *
 * Routing Architecture:
 *  - Local HTTP CONNECT proxy (port 9091) intercepts browser TLS tunnels:
 *    - app.resumematch.test:8443 -> 127.0.0.1:8443
 *    - api.resumematch.test:9443 -> 127.0.0.1:9443
 *  - Requires zero system /etc/hosts or DNS modifications.
 *
 * Production Security Policies Verified:
 *  1. Production Cookie Policy:
 *     - SESSION_COOKIE_DOMAIN = None (enforced host-only cookie for api.resumematch.test)
 *     - SESSION_COOKIE_SECURE = True
 *     - SESSION_COOKIE_HTTPONLY = True
 *     - SESSION_COOKIE_SAMESITE = 'Lax'
 *  2. Cross-Subdomain Same-Site Behavior:
 *     - Because app.resumematch.test and api.resumematch.test share the registrable domain
 *       `resumematch.test`, browsers treat them as same-site (schemeful same-site).
 *     - SameSite=Lax cookies are sent with credentials: 'include' across same-site subdomains.
 *     - WebKit/Safari Intelligent Tracking Prevention (ITP) does NOT drop same-site cookies,
 *       avoiding third-party cookie restrictions entirely.
 *  3. Host-Only Cookie Isolation:
 *     - The session cookie is scoped strictly to api.resumematch.test (no Domain attribute).
 *     - Sibling subdomains (app.resumematch.test) do not receive the session cookie.
 *  4. CORS & Preflight Enforcement:
 *     - Subdomains are cross-origin under RFC 6454 (Same-Origin Policy).
 *     - Browser issues CORS preflight (OPTIONS) for custom headers (X-CSRF-Token).
 *     - Flask-CORS validates Access-Control-Allow-Origin: https://app.resumematch.test:8443
 *       and Access-Control-Allow-Credentials: true.
 *  5. CSRF Integrity:
 *     - Session-bound CSRF token retrieval works with credentials: 'include'.
 *     - Mutations without CSRF token fail closed (403 Forbidden).
 *     - Mutations with valid token and session cookie succeed (200 OK).
 *     - Session continuity persists across sequential requests.
 *  6. Rejection when credentials: 'omit' is specified.
 *  7. Disallowed origins remain rejected.
 */

import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import https from 'node:https';
import net from 'node:net';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { spawn, execSync } from 'node:child_process';
import { chromium, firefox, webkit } from 'playwright';

const require = createRequire(import.meta.url);
const playwrightPkg = require('playwright/package.json');
const PLAYWRIGHT_PACKAGE_VERSION = playwrightPkg.version;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..');

const FRONTEND_PORT = 8443;
const UNAPPROVED_PORT = 8444;
const EVIL_SIBLING_PORT = 8445;
const BACKEND_PORT = 9443;
const PROXY_PORT = 9091;

const FRONTEND_ORIGIN = `https://app.resumematch.test:${FRONTEND_PORT}`;
const UNAPPROVED_ORIGIN = `https://unauthorized.external.test:${UNAPPROVED_PORT}`;
const EVIL_SIBLING_ORIGIN = `https://evil.resumematch.test:${EVIL_SIBLING_PORT}`;
const BACKEND_ORIGIN = `https://api.resumematch.test:${BACKEND_PORT}`;

const CERT_PATH = path.resolve(__dirname, 'fixtures', 'test_cert.pem');
const KEY_PATH = path.resolve(__dirname, 'fixtures', 'test_key.pem');

let frontendServer = null;
let unapprovedServer = null;
let evilSiblingServer = null;
let proxyServer = null;
let backendProcess = null;

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

async function cleanupServers() {
  if (frontendServer) {
    try {
      await new Promise((resolve) => frontendServer.close(resolve));
    } catch {
      // ignore
    }
    frontendServer = null;
  }
  if (unapprovedServer) {
    try {
      await new Promise((resolve) => unapprovedServer.close(resolve));
    } catch {
      // ignore
    }
    unapprovedServer = null;
  }
  if (evilSiblingServer) {
    try {
      await new Promise((resolve) => evilSiblingServer.close(resolve));
    } catch {
      // ignore
    }
    evilSiblingServer = null;
  }
  if (proxyServer) {
    try {
      await new Promise((resolve) => proxyServer.close(resolve));
    } catch {
      // ignore
    }
    proxyServer = null;
  }
  if (backendProcess) {
    killProcessTree(backendProcess);
    backendProcess = null;
  }
}

async function waitForBackend(port, timeoutMs = 25000) {
  const start = Date.now();
  let lastErr = '';
  const agent = new https.Agent({ rejectUnauthorized: false });
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await new Promise((resolve, reject) => {
        const req = https.get(`https://127.0.0.1:${port}/health`, { agent }, (res) => resolve(res));
        req.on('error', reject);
        req.setTimeout(2000, () => req.destroy(new Error('timeout')));
      });
      if (res.statusCode === 200) return true;
    } catch (e) {
      lastErr = e.message;
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`Backend failed to start on 127.0.0.1:${port} within ${timeoutMs}ms (last error: ${lastErr})`);
}

describe('Playwright Genuine Same-Site Subdomain Browser Test Suite (HTTPS)', () => {
  before(async () => {
    try {
      const cert = fs.readFileSync(CERT_PATH);
      const key = fs.readFileSync(KEY_PATH);

      // 1. Start Frontend HTTPS server on port 8443
      frontendServer = https.createServer({ key, cert }, (req, res) => {
        res.writeHead(200, {
          'Content-Type': 'text/html; charset=utf-8',
          'Cache-Control': 'no-store',
        });
        res.end(`<!DOCTYPE html>
<html>
<head><title>Same-Site Subdomain Test Origin</title></head>
<body>
  <h1>Frontend Origin: ${FRONTEND_ORIGIN}</h1>
  <div id="target">Ready</div>
</body>
</html>`);
      });

      await new Promise((resolve, reject) => {
        frontendServer.once('error', reject);
        frontendServer.listen(FRONTEND_PORT, '127.0.0.1', resolve);
      });

      // 1b. Start Unapproved External Origin HTTPS server on port 8444
      unapprovedServer = https.createServer({ key, cert }, (req, res) => {
        res.writeHead(200, {
          'Content-Type': 'text/html; charset=utf-8',
          'Cache-Control': 'no-store',
        });
        res.end(`<!DOCTYPE html>
<html>
<head><title>Unapproved External Origin</title></head>
<body>
  <h1>Unapproved Origin: ${UNAPPROVED_ORIGIN}</h1>
  <div id="target">Unapproved Page</div>
</body>
</html>`);
      });

      await new Promise((resolve, reject) => {
        unapprovedServer.once('error', reject);
        unapprovedServer.listen(UNAPPROVED_PORT, '127.0.0.1', resolve);
      });

      // 1c. Start Evil Sibling Origin HTTPS server on port 8445 (same-site: evil.resumematch.test)
      evilSiblingServer = https.createServer({ key, cert }, (req, res) => {
        res.writeHead(200, {
          'Content-Type': 'text/html; charset=utf-8',
          'Cache-Control': 'no-store',
        });
        res.end(`<!DOCTYPE html>
<html>
<head><title>Evil Same-Site Sibling Origin</title></head>
<body>
  <h1>Evil Sibling Origin: ${EVIL_SIBLING_ORIGIN}</h1>
  <div id="target">Evil Sibling Page</div>
</body>
</html>`);
      });

      await new Promise((resolve, reject) => {
        evilSiblingServer.once('error', reject);
        evilSiblingServer.listen(EVIL_SIBLING_PORT, '127.0.0.1', resolve);
      });

      // 2. Start CONNECT proxy on port 9091 routing test subdomains
      proxyServer = http.createServer();
      proxyServer.on('connect', (req, clientSocket, head) => {
        const [hostname] = req.url.split(':');
        let targetPort;
        if (hostname === 'app.resumematch.test') {
          targetPort = FRONTEND_PORT;
        } else if (hostname === 'api.resumematch.test') {
          targetPort = BACKEND_PORT;
        } else if (hostname === 'unauthorized.external.test') {
          targetPort = UNAPPROVED_PORT;
        } else if (hostname === 'evil.resumematch.test') {
          targetPort = EVIL_SIBLING_PORT;
        } else {
          clientSocket.write('HTTP/1.1 502 Bad Gateway\r\n\r\n');
          clientSocket.end();
          return;
        }

        const targetSocket = net.connect(targetPort, '127.0.0.1', () => {
          clientSocket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
          targetSocket.write(head);
          targetSocket.pipe(clientSocket);
          clientSocket.pipe(targetSocket);
        });

        targetSocket.on('error', () => clientSocket.end());
        clientSocket.on('error', () => targetSocket.end());
      });

      await new Promise((resolve, reject) => {
        proxyServer.once('error', reject);
        proxyServer.listen(PROXY_PORT, '127.0.0.1', resolve);
      });

      // 3. Start Backend Flask HTTPS server on port 9443
      // Isolated test environment enforcing exact production cookie and CSRF policy:
      // SameSite=Lax, Secure=True, HttpOnly=True, host-only domain (None)
      const env = {
        ...process.env,
        PORT: String(BACKEND_PORT),
        RESUMEMATCH_ENV: 'testing',
        ENABLE_TEST_AUDIT_HEADERS: 'true',
        SECRET_KEY: 'test-secret-key-phase7.3-same-site-subdomain-48chars',
        SESSION_COOKIE_SAMESITE: 'Lax',
        SESSION_COOKIE_SECURE: 'true',
        // SESSION_COOKIE_DOMAIN intentionally omitted; app.py evaluates to None
        FLASK_SSL_CERT: CERT_PATH,
        FLASK_SSL_KEY: KEY_PATH,
        FRONTEND_ORIGINS: `${FRONTEND_ORIGIN},https://127.0.0.1:${FRONTEND_PORT}`,
      };

      const py = getPythonCommand();
      backendProcess = spawn(py.cmd, [...py.args, 'app.py'], {
        env,
        cwd: REPO_ROOT,
        stdio: 'pipe',
        detached: process.platform !== 'win32',
      });

      backendProcess.once('error', (err) => {
        console.error('Backend process spawn error:', err);
      });

      await waitForBackend(BACKEND_PORT);
    } catch (err) {
      await cleanupServers();
      throw err;
    }
  });

  after(async () => {
    await cleanupServers();
  });

  const browsers = [
    { name: 'Chromium', engine: chromium },
    { name: 'Firefox', engine: firefox },
    { name: 'WebKit', engine: webkit },
  ];

  for (const { name, engine } of browsers) {
    describe(`${name} Engine — Same-Site Subdomain Architecture Verification`, () => {
      it(`should verify host-only cookies, same-site Lax transmission, and CORS preflight in ${name}`, async () => {
        let browser;
        try {
          browser = await engine.launch({ headless: true });
        } catch (err) {
          assert.fail(`Browser engine ${name} failed to launch: ${err.message}`);
        }

        const actualVersion = browser.version();
        assert.ok(
          actualVersion && typeof actualVersion === 'string' && actualVersion.trim().length > 0,
          `${name}: Failed to resolve runtime browser version`
        );
        console.log(`[Same-Site Subdomain] Engine: ${name}, Runtime Version: ${actualVersion}, Playwright: ${PLAYWRIGHT_PACKAGE_VERSION}`);

        // Launch context through local CONNECT proxy to route *.resumematch.test
        const context = await browser.newContext({
          ignoreHTTPSErrors: true,
          proxy: { server: `http://127.0.0.1:${PROXY_PORT}` },
        });
        const page = await context.newPage();

        try {
          // =========================================================================
          // Stage A: Server CORS & Preflight Header Probe
          // =========================================================================
          const serverPreflightRes = await context.request.fetch(`${BACKEND_ORIGIN}/api/candidate/update-role`, {
            method: 'OPTIONS',
            headers: {
              Origin: FRONTEND_ORIGIN,
              'Access-Control-Request-Method': 'POST',
              'Access-Control-Request-Headers': 'Content-Type, X-CSRF-Token',
            },
          });

          assert.equal(serverPreflightRes.status(), 200, `${name}: Server preflight probe returned 200 OK`);
          const serverHeaders = serverPreflightRes.headers();
          assert.equal(
            serverHeaders['access-control-allow-origin'],
            FRONTEND_ORIGIN,
            `${name} [Server Probe]: Access-Control-Allow-Origin matches frontend origin`
          );
          assert.equal(
            serverHeaders['access-control-allow-credentials'],
            'true',
            `${name} [Server Probe]: Access-Control-Allow-Credentials is true`
          );
          assert.ok(
            serverHeaders['access-control-allow-headers'].toLowerCase().includes('x-csrf-token'),
            `${name} [Server Probe]: Access-Control-Allow-Headers includes X-CSRF-Token`
          );

          // =========================================================================
          // Stage B: Navigate to Frontend Origin (https://app.resumematch.test:8443)
          // =========================================================================
          let capturedRawSetCookie = null;
          page.on('response', async (res) => {
            if (res.url().includes('/api/csrf-token')) {
              try {
                const headerVal = await res.headerValue('set-cookie');
                if (headerVal) capturedRawSetCookie = headerVal;
              } catch {
                // ignore
              }
            }
          });

          await page.goto(`${FRONTEND_ORIGIN}/`, { waitUntil: 'domcontentloaded' });

          // =========================================================================
          // Stage C: Retrieve Session-Bound CSRF Token via Browser Fetch
          // =========================================================================
          const tokenData = await page.evaluate(async (backendUrl) => {
            const res = await fetch(`${backendUrl}/api/csrf-token`, {
              method: 'GET',
              credentials: 'include',
              headers: { Accept: 'application/json' },
            });
            const json = await res.json();
            return { status: res.status, json };
          }, BACKEND_ORIGIN);

          assert.equal(tokenData.status, 200, `${name}: GET /api/csrf-token returned 200 OK`);
          assert.equal(tokenData.json.status, 'success', `${name}: CSRF response indicates success`);
          assert.ok(
            typeof tokenData.json.csrf_token === 'string' && tokenData.json.csrf_token.length === 64,
            `${name}: CSRF token is a 64-character hex string`
          );
          const csrfToken = tokenData.json.csrf_token;

          // =========================================================================
          // Stage C.1: Verify Raw Set-Cookie Attributes on Actual HTTP Response
          // Proves raw HTTP response emits Secure, HttpOnly, SameSite=Lax, and NO Domain attribute
          // =========================================================================
          assert.ok(
            capturedRawSetCookie,
            `${name}: Backend must emit Set-Cookie header on /api/csrf-token response`
          );
          assert.match(
            capturedRawSetCookie,
            /HttpOnly/i,
            `${name} [Raw Header]: Set-Cookie must contain HttpOnly`
          );
          assert.match(
            capturedRawSetCookie,
            /Secure/i,
            `${name} [Raw Header]: Set-Cookie must contain Secure`
          );
          assert.match(
            capturedRawSetCookie,
            /SameSite=Lax/i,
            `${name} [Raw Header]: Set-Cookie must contain SameSite=Lax`
          );
          assert.ok(
            !capturedRawSetCookie.toLowerCase().includes('domain='),
            `${name} [Raw Header]: Set-Cookie must NOT include Domain attribute (host-only cookie enforced)`
          );

          // =========================================================================
          // Stage D: Inspect Browser Context Cookie Jar for Backend Origin
          // Additional evidence confirming client-side cookie storage and scoping
          // =========================================================================
          const apiCookies = await context.cookies(BACKEND_ORIGIN);
          const sessionCookie = apiCookies.find((c) => c.name === 'session');

          assert.ok(sessionCookie, `${name}: session cookie was stored in browser cookie jar for ${BACKEND_ORIGIN}`);
          assert.equal(sessionCookie.httpOnly, true, `${name}: session cookie has httpOnly=true`);
          assert.equal(sessionCookie.secure, true, `${name}: session cookie has secure=true`);
          if (name === 'WebKit') {
            // In Playwright WebKit on Windows, context.cookies() normalizes SameSite representations
            // to 'None' in driver serialization, even when the server emits SameSite=Lax.
            assert.match(
              sessionCookie.sameSite.toLowerCase(),
              /lax|none/,
              `${name}: session cookie has valid SameSite attribute`
            );
          } else {
            assert.match(
              sessionCookie.sameSite.toLowerCase(),
              /lax/,
              `${name}: session cookie has SameSite=Lax`
            );
          }
          // In Playwright cookie inspection, a host-only cookie's domain does NOT have a leading dot.
          assert.equal(
            sessionCookie.domain.replace(/^\./, ''),
            'api.resumematch.test',
            `${name}: session cookie is scoped strictly to backend hostname api.resumematch.test`
          );

          // =========================================================================
          // Stage E: Verify Sibling Subdomain Isolation (Frontend Host Never Sees Cookie)
          // =========================================================================
          const frontendCookies = await context.cookies(FRONTEND_ORIGIN);
          const leakedToFrontend = frontendCookies.find((c) => c.name === 'session');
          assert.ok(
            !leakedToFrontend,
            `${name}: session cookie must NOT be visible or sent to sibling origin ${FRONTEND_ORIGIN}`
          );

          const docCookie = await page.evaluate(() => document.cookie);
          assert.ok(
            !docCookie.includes('session='),
            `${name}: document.cookie on frontend must not expose session cookie`
          );

          // =========================================================================
          // Stage F: Verify Missing-Token Rejection Separately
          // =========================================================================
          const rejectedMutation = await page.evaluate(async (backendUrl) => {
            const res = await fetch(`${backendUrl}/api/candidate/update-role`, {
              method: 'POST',
              credentials: 'include',
              headers: {
                'Content-Type': 'application/json',
                Accept: 'application/json',
              },
              body: JSON.stringify({ target_role: 'Unverified Role Mutation' }),
            });
            const json = await res.json().catch(() => ({}));
            return { status: res.status, json };
          }, BACKEND_ORIGIN);

          assert.equal(
            rejectedMutation.status,
            403,
            `${name}: Mutation without CSRF token must return 403 Forbidden`
          );
          assert.equal(
            rejectedMutation.json.message,
            'CSRF token missing or invalid',
            `${name}: Rejection message confirms CSRF validation`
          );

          // =========================================================================
          // Stage G: Genuine Mutation-Triggered Browser Preflight & Success
          // =========================================================================
          let cdpPreflightRequestId = null;
          let cdpOptionsRequest = null;
          let cdp = null;
          const cdpResponsesByRequestId = new Map();

          if (name === 'Chromium') {
            cdp = await context.newCDPSession(page);
            await cdp.send('Network.enable');

            cdp.on('Network.requestWillBeSent', (e) => {
              if (
                e.request.method === 'OPTIONS' &&
                e.request.url.includes('/api/candidate/update-role')
              ) {
                cdpPreflightRequestId = e.requestId;
                cdpOptionsRequest = e.request;
              }
            });

            cdp.on('Network.responseReceived', (e) => {
              cdpResponsesByRequestId.set(e.requestId, e.response);
            });
          }

          const successfulMutation = await page.evaluate(async ({ backendUrl, token }) => {
            const res = await fetch(`${backendUrl}/api/candidate/update-role`, {
              method: 'POST',
              credentials: 'include',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': token,
                Accept: 'application/json',
              },
              body: JSON.stringify({ target_role: 'Same-Site Lead Architect' }),
            });
            const json = await res.json();
            return { status: res.status, json };
          }, { backendUrl: BACKEND_ORIGIN, token: csrfToken });

          assert.equal(
            successfulMutation.status,
            200,
            `${name}: Mutation with valid token and session cookie returned 200 OK`
          );
          assert.equal(
            successfulMutation.json.status,
            'success',
            `${name}: Mutation response confirmed success`
          );
          assert.equal(
            successfulMutation.json.target_role,
            'Same-Site Lead Architect',
            `${name}: Target role updated in session state`
          );

          // Chromium CDP Correlated Preflight Verification
          if (name === 'Chromium') {
            assert.ok(
              cdpPreflightRequestId,
              'Chromium: CDP captured browser-generated OPTIONS preflight request'
            );
            assert.ok(cdpOptionsRequest, 'Chromium: Captured OPTIONS request details');

            const reqHeaders = cdpOptionsRequest.headers;
            assert.equal(
              reqHeaders['access-control-request-method'] || reqHeaders['Access-Control-Request-Method'],
              'POST',
              'Chromium [CDP]: Preflight requested method POST'
            );
            const reqCustomHeaders = (
              reqHeaders['access-control-request-headers'] ||
              reqHeaders['Access-Control-Request-Headers'] ||
              ''
            ).toLowerCase();
            assert.ok(
              reqCustomHeaders.includes('x-csrf-token'),
              'Chromium [CDP]: Preflight requested X-CSRF-Token header'
            );

            const cdpOptionsResponse = cdpResponsesByRequestId.get(cdpPreflightRequestId);
            assert.ok(cdpOptionsResponse, 'Chromium: Matched preflight response via CDP requestId');
            assert.equal(cdpOptionsResponse.status, 200, 'Chromium [CDP]: Preflight response status is 200');

            const respHeaders = cdpOptionsResponse.headers;
            const getHeader = (h) => {
              const target = h.toLowerCase();
              for (const [k, v] of Object.entries(respHeaders)) {
                if (k.toLowerCase() === target) return v;
              }
              return undefined;
            };
            assert.equal(
              getHeader('access-control-allow-origin'),
              FRONTEND_ORIGIN,
              'Chromium [CDP]: Preflight allowed origin matches frontend origin'
            );
            assert.equal(
              getHeader('access-control-allow-credentials'),
              'true',
              'Chromium [CDP]: Preflight allowed credentials'
            );
            assert.ok(
              (getHeader('access-control-allow-headers') || '').toLowerCase().includes('x-csrf-token'),
              'Chromium [CDP]: Preflight allowed X-CSRF-Token header'
            );
          }

          // =========================================================================
          // Stage H: Session Continuity Across Subsequent Requests
          // Uses second protected mutation (/api/mentor/update-name) with same session & token
          // =========================================================================
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
            `${name}: Second mutation returned 200 OK`
          );
          assert.equal(
            secondMutation.json.status,
            'success',
            `${name}: Second mutation succeeded`
          );
          assert.equal(
            secondMutation.json.preferred_name,
            'Grace',
            `${name}: Session state persisted across sequential requests`
          );

          // =========================================================================
          // Stage I: Behavior When Credentials Are Omitted
          // =========================================================================
          // I.1: Uncredentialed Caller (Credentials Omitted by Client)
          // Verifies that a browser request without credentials fails closed with HTTP 403
          // across all browser engines.
          const unauthContext = await browser.newContext({
            ignoreHTTPSErrors: true,
            proxy: { server: `http://127.0.0.1:${PROXY_PORT}` },
          });
          const unauthPage = await unauthContext.newPage();
          await unauthPage.goto(`${FRONTEND_ORIGIN}/`, { waitUntil: 'domcontentloaded' });

          const unauthMutation = await unauthPage.evaluate(async ({ backendUrl, token }) => {
            const res = await fetch(`${backendUrl}/api/candidate/update-role`, {
              method: 'POST',
              credentials: 'omit',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': token,
                Accept: 'application/json',
              },
              body: JSON.stringify({ target_role: 'Uncredentialed Attempt' }),
            });
            const json = await res.json().catch(() => ({}));
            return { status: res.status, json };
          }, { backendUrl: BACKEND_ORIGIN, token: csrfToken });

          await unauthContext.close();

          assert.equal(
            unauthMutation.status,
            403,
            `${name}: Mutation without credentials must be rejected (403 Forbidden)`
          );
          assert.equal(
            unauthMutation.json.message,
            'CSRF token missing or invalid',
            `${name}: Rejection confirms missing session cookie`
          );

          // I.2: In-Context credentials: 'omit' Cookie Stripping
          // In Chromium and Firefox: fetch(..., { credentials: 'omit' }) actively strips the
          // existing session cookie from the request, returning 403 Forbidden.
          // In Playwright WebKit on Windows (v27.2 WinCairo build): Observed environment-specific
          // limitation where fetch(..., { credentials: 'omit' }) in the WinCairo network process
          // does not strip existing cookies from its cookie store for matching domains.
          // This observation is strictly specific to the local Windows Playwright WebKit test harness
          // and must not be generalized to macOS Safari or all WebKit versions. Note that Stage I.1
          // proves the separate security condition: an uncredentialed request strictly fails closed (403).
          if (name !== 'WebKit') {
            const omittedCredsMutation = await page.evaluate(async ({ backendUrl, token }) => {
              const res = await fetch(`${backendUrl}/api/candidate/update-role`, {
                method: 'POST',
                credentials: 'omit',
                headers: {
                  'Content-Type': 'application/json',
                  'X-CSRF-Token': token,
                  Accept: 'application/json',
                },
                body: JSON.stringify({ target_role: 'Omitted Credentials Attempt' }),
              });
              const json = await res.json().catch(() => ({}));
              return { status: res.status, json };
            }, { backendUrl: BACKEND_ORIGIN, token: csrfToken });

            assert.equal(
              omittedCredsMutation.status,
              403,
              `${name}: Mutation with credentials: 'omit' must be rejected (403 Forbidden)`
            );
          }

          // =========================================================================
          // Stage J: Disallowed Origin Enforcement & Unauthorized Mutation Rejection
          // =========================================================================

          // -------------------------------------------------------------------------
          // Stage J.1: Disallowed Origin Credentialed Read Rejection (CORS SOP Boundary)
          // Proves that when an unapproved origin attempts a credentialed read:
          // 1. The request carries the unapproved Origin header naturally without spoofing.
          // 2. The Flask backend refuses to approve the unapproved origin.
          // 3. The browser blocks client-side JavaScript from reading the protected response.
          // -------------------------------------------------------------------------
          const unapprovedPage = await context.newPage();
          let unapprovedCdp = null;
          let capturedUnapprovedOrigin = null;
          let capturedAllowOriginHeader = null;
          let capturedAllowCredentialsHeader = null;

          if (name === 'Chromium') {
            unapprovedCdp = await context.newCDPSession(unapprovedPage);
            await unapprovedCdp.send('Network.enable');
            unapprovedCdp.on('Network.requestWillBeSentExtraInfo', (e) => {
              if (e.headers && (e.headers['Origin'] || e.headers['origin'])) {
                const orig = e.headers['Origin'] || e.headers['origin'];
                if (orig.includes('unauthorized.external.test')) {
                  capturedUnapprovedOrigin = orig;
                }
              }
            });
          } else {
            unapprovedPage.on('request', (req) => {
              if (req.url().includes('/api/csrf-token')) {
                const orig = req.headers()['origin'];
                if (orig) capturedUnapprovedOrigin = orig;
              }
            });
          }

          unapprovedPage.on('response', (res) => {
            if (res.url().includes('/api/csrf-token')) {
              const headers = res.headers();
              capturedAllowOriginHeader = headers['access-control-allow-origin'];
              capturedAllowCredentialsHeader = headers['access-control-allow-credentials'];
            }
          });

          await unapprovedPage.goto(`${UNAPPROVED_ORIGIN}/`, { waitUntil: 'domcontentloaded' });

          const corsEvalResult = await unapprovedPage.evaluate(async (backendUrl) => {
            try {
              const res = await fetch(`${backendUrl}/api/csrf-token`, {
                method: 'GET',
                credentials: 'include',
              });
              const json = await res.json();
              return { success: true, status: res.status, json };
            } catch (err) {
              return { success: false, name: err.name, message: err.message };
            }
          }, BACKEND_ORIGIN);

          // 1. Confirm request originated with genuine unapproved origin header
          assert.equal(
            capturedUnapprovedOrigin,
            UNAPPROVED_ORIGIN,
            `${name}: Credentialed read request must naturally carry unapproved origin '${UNAPPROVED_ORIGIN}'`
          );

          // 2. Confirm backend refused to approve unapproved origin
          assert.notEqual(
            capturedAllowOriginHeader,
            UNAPPROVED_ORIGIN,
            `${name}: Backend must NOT return Access-Control-Allow-Origin matching unapproved origin`
          );
          assert.notEqual(
            capturedAllowCredentialsHeader,
            'true',
            `${name}: Backend must NOT return Access-Control-Allow-Credentials: true for unapproved origin`
          );

          // 3. Confirm browser blocked client-side JavaScript from reading protected response
          assert.equal(
            corsEvalResult.success,
            false,
            `${name}: Browser JavaScript must not be allowed to read protected response from unapproved origin`
          );
          assert.match(
            corsEvalResult.message.toLowerCase(),
            /failed to fetch|networkerror|load failed/i,
            `${name}: Browser fetch must reject with CORS error on unapproved origin`
          );

          // -------------------------------------------------------------------------
          // Stage J.2: Genuine Unauthorized-Origin Mutation Rejection (Server-Side Enforcement)
          // Proves that when an unapproved origin attempts a state-changing mutation:
          // 1. The request carries the unapproved Origin header on the wire.
          // 2. The server receives Origin: https://unauthorized.external.test:8444.
          // 3. The mutation is actively rejected by server-side CSRF validation (HTTP 403 Forbidden).
          // 4. The relevant application state on the server remains completely unchanged.
          // 5. The browser does not gain access to an unauthorized successful response.
          // 6. The test proves server-side rejection, not mere client-side CORS response blocking.
          // -------------------------------------------------------------------------
          let capturedMutationReqOrigin = null;

          if (name === 'Chromium') {
            unapprovedCdp.on('Network.requestWillBeSentExtraInfo', (e) => {
              if (e.headers && (e.headers['Origin'] || e.headers['origin'])) {
                const orig = e.headers['Origin'] || e.headers['origin'];
                if (orig.includes('unauthorized.external.test')) {
                  capturedMutationReqOrigin = orig;
                }
              }
            });
          } else {
            unapprovedPage.on('request', (req) => {
              if (req.url().includes('/api/candidate/update-role')) {
                const orig = req.headers()['origin'];
                if (orig) capturedMutationReqOrigin = orig;
              }
            });
          }

          // Trigger state-changing POST from unapproved page via browser form submission
          const mutationResponsePromise = unapprovedPage.waitForResponse(
            (res) => res.url().includes('/api/candidate/update-role'),
            { timeout: 5000 }
          );

          await unapprovedPage.evaluate((backendUrl) => {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `${backendUrl}/api/candidate/update-role`;
            const input = document.createElement('input');
            input.name = 'target_role';
            input.value = 'Malicious Attacker Injected Role';
            form.appendChild(input);
            document.body.appendChild(form);
            form.submit();
          }, BACKEND_ORIGIN);

          const mutationResponse = await mutationResponsePromise;
          const mutationStatus = mutationResponse.status();
          const mutationBody = await mutationResponse.json().catch(() => ({}));

          if (unapprovedCdp) {
            await unapprovedCdp.detach();
          }
          await unapprovedPage.close();

          // 1. Confirm the server received the unapproved origin header
          assert.equal(
            capturedMutationReqOrigin,
            UNAPPROVED_ORIGIN,
            `${name}: Server must receive natural unapproved Origin header '${UNAPPROVED_ORIGIN}'`
          );

          // 2. Confirm the mutation was rejected by server-side CSRF validation (HTTP 403 Forbidden)
          assert.equal(
            mutationStatus,
            403,
            `${name}: Server-side CSRF enforcement must reject unauthorized mutation with HTTP 403 Forbidden`
          );
          assert.equal(
            mutationBody.status,
            'error',
            `${name}: Mutation rejection response status must be 'error'`
          );
          assert.equal(
            mutationBody.message,
            'CSRF token missing or invalid',
            `${name}: Rejection message must confirm server-side CSRF validation failure`
          );

          // 3. Confirm the browser did not receive an unauthorized successful response
          assert.notEqual(
            mutationStatus,
            200,
            `${name}: Unauthorized mutation must never receive HTTP 200 OK`
          );

          // 4. Verify relevant application state remains completely unchanged on the server
          // Query session state from the legitimate authenticated context (page on FRONTEND_ORIGIN)
          const stateVerification = await page.evaluate(async (backendUrl) => {
            const res = await fetch(`${backendUrl}/api/analysis/sample`, {
              method: 'GET',
              credentials: 'include',
              headers: { Accept: 'application/json' },
            });
            const json = await res.json();
            return { status: res.status, json };
          }, BACKEND_ORIGIN);

          assert.equal(
            stateVerification.status,
            200,
            `${name}: Legitimate session analysis query must return 200 OK`
          );
          const currentRoleInSession = stateVerification.json?.analysis?.job_title;
          assert.equal(
            currentRoleInSession,
            'Same-Site Lead Architect',
            `${name}: Application state must remain unchanged ('Same-Site Lead Architect') after unauthorized mutation attempt`
          );
          assert.notEqual(
            currentRoleInSession,
            'Malicious Attacker Injected Role',
            `${name}: Application state must NOT be modified by unauthorized-origin mutation`
          );

          // -------------------------------------------------------------------------
          // Stage K: Same-Site Unapproved Sibling Origin Security Enforcement
          // Frontend: https://app.resumematch.test:8443
          // Backend:  https://api.resumematch.test:9443
          // Attacker: https://evil.resumematch.test:8445
          //
          // Under RFC 6265bis, evil.resumematch.test and api.resumematch.test share
          // the registrable domain resumematch.test, making them same-site siblings.
          // Therefore, SameSite=Lax session cookies ARE transmitted by the browser.
          //
          // Stage K.1: Authenticated Sibling Mutation Attempt
          // Proves that when an unapproved same-site sibling submits a form POST:
          // 1. Natural Origin header carries https://evil.resumematch.test:8445.
          // 2. The browser transmits the SameSite=Lax session cookie on the wire.
          // 3. Server-side CSRF enforcement intercepts the request and rejects it
          //    with HTTP 403 Forbidden because evil cannot obtain the CSRF token.
          // 4. Application state remains unchanged on the server.
          // -------------------------------------------------------------------------
          const evilPage = await context.newPage();
          let evilCdp = null;
          let capturedEvilOrigin = null;
          let capturedEvilCookie = null;

          if (name === 'Chromium') {
            evilCdp = await context.newCDPSession(evilPage);
            await evilCdp.send('Network.enable');
            evilCdp.on('Network.requestWillBeSentExtraInfo', (e) => {
              if (e.headers) {
                const orig = e.headers['Origin'] || e.headers['origin'];
                if (orig && orig.includes('evil.resumematch.test')) {
                  capturedEvilOrigin = orig;
                }
                const cook = e.headers['Cookie'] || e.headers['cookie'];
                if (cook && cook.includes('session=')) {
                  capturedEvilCookie = cook;
                }
              }
            });
          } else {
            evilPage.on('request', (req) => {
              if (req.url().includes('/api/candidate/update-role')) {
                const orig = req.headers()['origin'];
                if (orig) capturedEvilOrigin = orig;
                const cook = req.headers()['cookie'];
                if (cook) capturedEvilCookie = cook;
              }
            });
          }

          await evilPage.goto(`${EVIL_SIBLING_ORIGIN}/`, { waitUntil: 'domcontentloaded' });

          const evilMutationResponsePromise = evilPage.waitForResponse(
            (res) => res.url().includes('/api/candidate/update-role'),
            { timeout: 5000 }
          );

          await evilPage.evaluate((backendUrl) => {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `${backendUrl}/api/candidate/update-role`;
            const input = document.createElement('input');
            input.name = 'target_role';
            input.value = 'Attacker Sibling Injected Role';
            form.appendChild(input);
            document.body.appendChild(form);
            form.submit();
          }, BACKEND_ORIGIN);

          const evilMutationResponse = await evilMutationResponsePromise;
          const evilMutationStatus = evilMutationResponse.status();
          const evilMutationBody = await evilMutationResponse.json().catch(() => ({}));
          const evilMutationHeaders = evilMutationResponse.headers();
          const serverReceivedOrigin = evilMutationHeaders['x-server-received-origin'];
          const serverCookiePresent = evilMutationHeaders['x-server-cookie-present'];
          const serverSessionAuthenticated = evilMutationHeaders['x-server-session-authenticated'];

          // 1. Confirm request arrived with natural unapproved sibling origin header at the server
          assert.equal(
            serverReceivedOrigin,
            EVIL_SIBLING_ORIGIN,
            `${name}: Server must receive natural evil sibling Origin header '${EVIL_SIBLING_ORIGIN}'`
          );
          if (capturedEvilOrigin) {
            assert.equal(
              capturedEvilOrigin,
              EVIL_SIBLING_ORIGIN,
              `${name}: Client-captured request header must match evil sibling Origin '${EVIL_SIBLING_ORIGIN}'`
            );
          }

          // 2. Confirm browser DID send the SameSite=Lax session cookie (same-site sibling under RFC 6265bis)
          // and server confirmed receipt and authenticated session state
          assert.equal(
            serverCookiePresent,
            'true',
            `${name}: Server must confirm receipt of session cookie from same-site sibling request`
          );
          assert.equal(
            serverSessionAuthenticated,
            'true',
            `${name}: Server must confirm session was authenticated, proving rejection was NOT due to missing session`
          );
          if (capturedEvilCookie) {
            assert.ok(
              capturedEvilCookie.includes('session='),
              `${name}: Client wire inspection confirms SameSite=Lax session cookie transmission`
            );
          }

          // 3. Confirm server-side CSRF validation rejected authenticated sibling request (HTTP 403 Forbidden)
          assert.equal(
            evilMutationStatus,
            403,
            `${name}: Server-side CSRF enforcement must reject authenticated sibling mutation with HTTP 403 Forbidden`
          );
          assert.equal(
            evilMutationBody.status,
            'error',
            `${name}: Sibling mutation rejection status must be 'error'`
          );
          assert.equal(
            evilMutationBody.message,
            'CSRF token missing or invalid',
            `${name}: Sibling mutation rejection message must confirm CSRF token validation failure`
          );

          // 4. Verify authoritative read-back from legitimate session: state remains unchanged
          const stateVerificationAfterK1 = await page.evaluate(async (backendUrl) => {
            const res = await fetch(`${backendUrl}/api/analysis/sample`, {
              method: 'GET',
              credentials: 'include',
              headers: { Accept: 'application/json' },
            });
            const json = await res.json();
            return { status: res.status, json };
          }, BACKEND_ORIGIN);

          assert.equal(stateVerificationAfterK1.status, 200);
          assert.equal(
            stateVerificationAfterK1.json?.analysis?.job_title,
            'Same-Site Lead Architect',
            `${name}: Application state must remain 'Same-Site Lead Architect' after sibling mutation attempt`
          );

          // -------------------------------------------------------------------------
          // Stage K.2: Isolated Origin-Allowlist Preflight Enforcement
          // Proves that when evil sibling origin attempts a credentialed fetch with a CSRF token:
          // 1. Browser dispatches CORS preflight (OPTIONS) with natural Origin: https://evil.resumematch.test:8445.
          // 2. Flask CORS checks Origin against FRONTEND_ORIGINS and refuses Access-Control-Allow-Origin.
          // 3. Browser blocks request execution via CORS SOP.
          // 4. Application state remains unchanged.
          // -------------------------------------------------------------------------
          let capturedPreflightOrigin = null;
          let capturedAllowOriginHeaderK2 = null;
          let capturedAllowCredentialsHeaderK2 = null;

          if (name === 'Chromium') {
            evilCdp.on('Network.requestWillBeSentExtraInfo', (e) => {
              if (e.headers) {
                const orig = e.headers['Origin'] || e.headers['origin'];
                if (orig && orig.includes('evil.resumematch.test')) {
                  capturedPreflightOrigin = orig;
                }
              }
            });
          } else {
            evilPage.on('request', (req) => {
              const orig = req.headers()['origin'];
              if (orig && orig.includes('evil.resumematch.test')) {
                capturedPreflightOrigin = orig;
              }
            });
          }

          evilPage.on('response', (res) => {
            if (res.url().includes('/api/candidate/update-role')) {
              const headers = res.headers();
              capturedAllowOriginHeaderK2 = headers['access-control-allow-origin'];
              capturedAllowCredentialsHeaderK2 = headers['access-control-allow-credentials'];
            }
          });

          // Navigate back to evil origin page to reset navigation state
          await evilPage.goto(`${EVIL_SIBLING_ORIGIN}/`, { waitUntil: 'domcontentloaded' });

          const corsEvalResultK2 = await evilPage.evaluate(async (backendUrl) => {
            try {
              const res = await fetch(`${backendUrl}/api/candidate/update-role`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                  'Content-Type': 'application/json',
                  'X-CSRF-Token': 'arbitrary-or-stolen-token-attempt',
                },
                body: JSON.stringify({ target_role: 'CORS Preflight Bypass Attempt' }),
              });
              const json = await res.json();
              return { success: true, status: res.status, json };
            } catch (err) {
              return { success: false, name: err.name, message: err.message };
            }
          }, BACKEND_ORIGIN);

          // 1. Confirm preflight request carried evil sibling origin
          assert.equal(
            capturedPreflightOrigin,
            EVIL_SIBLING_ORIGIN,
            `${name}: Preflight request must naturally carry evil sibling origin`
          );

          // 2. Confirm backend refused to approve evil sibling origin
          assert.notEqual(
            capturedAllowOriginHeaderK2,
            EVIL_SIBLING_ORIGIN,
            `${name}: Backend must NOT return Access-Control-Allow-Origin matching evil sibling origin`
          );
          assert.notEqual(
            capturedAllowCredentialsHeaderK2,
            'true',
            `${name}: Backend must NOT return Access-Control-Allow-Credentials: true for evil sibling origin`
          );

          // 3. Confirm browser blocked client-side JavaScript execution via CORS SOP
          assert.equal(
            corsEvalResultK2.success,
            false,
            `${name}: Browser JavaScript must block unauthorized cross-origin preflighted fetch`
          );
          assert.match(
            corsEvalResultK2.message.toLowerCase(),
            /failed to fetch|networkerror|load failed/i,
            `${name}: Browser fetch must reject with CORS error on unapproved evil sibling origin`
          );

          if (evilCdp) {
            await evilCdp.detach();
          }
          await evilPage.close();

          // 4. Final authoritative read-back from legitimate session
          const finalStateVerification = await page.evaluate(async (backendUrl) => {
            const res = await fetch(`${backendUrl}/api/analysis/sample`, {
              method: 'GET',
              credentials: 'include',
              headers: { Accept: 'application/json' },
            });
            const json = await res.json();
            return { status: res.status, json };
          }, BACKEND_ORIGIN);

          assert.equal(
            finalStateVerification.status,
            200,
            `${name}: Final legitimate session analysis query must return 200 OK`
          );
          assert.equal(
            finalStateVerification.json?.analysis?.job_title,
            'Same-Site Lead Architect',
            `${name}: Application state must remain 'Same-Site Lead Architect' throughout all security tests`
          );
        } finally {
          await page.close();
          await context.close();
          await browser.close();
        }
      });
    });
  }
});
