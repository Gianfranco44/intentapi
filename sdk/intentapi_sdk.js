/**
 * IntentAPI JavaScript SDK
 *
 * Usage:
 *   import IntentAPI from './intentapi_sdk.js';
 *   const client = new IntentAPI('intent_your_key', 'https://your-app.onrender.com');
 *   const result = await client.run('Send an email to john@example.com saying hello');
 */

class IntentAPI {
  constructor(apiKey, baseUrl = 'http://localhost:8000') {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.headers = {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      'User-Agent': 'IntentAPI-JS-SDK/1.0',
    };
  }

  async _request(method, path, body = null, params = null) {
    let url = `${this.baseUrl}${path}`;
    if (params) {
      const qs = new URLSearchParams(params).toString();
      url += `?${qs}`;
    }

    const options = { method, headers: this.headers };
    if (body) options.body = JSON.stringify(body);

    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(`[${response.status}] ${data.detail || data.error || 'Unknown error'}`);
    }
    return data;
  }

  // ── Core ──────────────────────────────────────

  async run(intent, { context = null, requireApproval = false } = {}) {
    const payload = { intent, dry_run: false, require_approval: requireApproval };
    if (context) payload.context = context;
    return this._request('POST', '/api/v1/intent', payload);
  }

  async plan(intent, context = null) {
    const payload = { intent, dry_run: true };
    if (context) payload.context = context;
    return this._request('POST', '/api/v1/intent', payload);
  }

  async approve(executionId) {
    return this._request('POST', `/api/v1/intent/${executionId}/approve`);
  }

  // ── Executions ────────────────────────────────

  async executions(limit = 20, offset = 0) {
    return this._request('GET', '/api/v1/executions', null, { limit, offset });
  }

  async execution(executionId) {
    return this._request('GET', `/api/v1/executions/${executionId}`);
  }

  // ── Connectors ────────────────────────────────

  async connectors() {
    return this._request('GET', '/api/v1/connectors/available');
  }

  async myConnectors() {
    return this._request('GET', '/api/v1/connectors/mine');
  }

  async configureConnector(connectorType, config) {
    return this._request('POST', '/api/v1/connectors/configure', {
      connector_type: connectorType, config,
    });
  }

  // ── Account ───────────────────────────────────

  async me() { return this._request('GET', '/api/auth/me'); }
  async usage() { return this._request('GET', '/api/v1/usage'); }
  async plans() { return this._request('GET', '/api/v1/plans'); }
}

// Auth helper for initial setup
class IntentAPIAuth {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  async register(email, password, name = null) {
    const payload = { email, password };
    if (name) payload.name = name;
    const r = await fetch(`${this.baseUrl}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return r.json();
  }

  async login(email, password) {
    const r = await fetch(`${this.baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    return r.json();
  }

  async createApiKey(accessToken, name = 'SDK Key') {
    const r = await fetch(`${this.baseUrl}/api/auth/api-keys?name=${encodeURIComponent(name)}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${accessToken}` },
    });
    return r.json();
  }

  async quickSetup(email, password, name = null) {
    let auth;
    try {
      auth = await this.register(email, password, name);
    } catch {
      auth = await this.login(email, password);
    }

    if (!auth.access_token) throw new Error('Failed to get access token');

    const keyData = await this.createApiKey(auth.access_token);
    if (!keyData.key) throw new Error('Failed to create API key');

    return new IntentAPI(keyData.key, this.baseUrl);
  }
}

// Export for both Node.js and browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { IntentAPI, IntentAPIAuth };
}

export { IntentAPI, IntentAPIAuth };
export default IntentAPI;
