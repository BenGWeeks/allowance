/** Shared browser-test configuration. Process environment overrides .env.local. */
const fs = require('fs');
const path = require('path');

function loadEnv() {
  const file = path.join(__dirname, '../../.env.local');
  if (!fs.existsSync(file)) return {};
  return Object.fromEntries(fs.readFileSync(file, 'utf8').split(/\r?\n/)
    .filter(line => line.trim() && !line.trim().startsWith('#') && line.includes('='))
    .map(line => {
      const index = line.indexOf('=');
      let value = line.slice(index + 1).trim();
      if ((value.startsWith('"') && value.endsWith('"')) ||
          (value.startsWith("'") && value.endsWith("'"))) value = value.slice(1, -1);
      return [line.slice(0, index).trim(), value];
    }));
}

function getConfig() {
  const config = {...loadEnv(), ...process.env};
  for (const key of ['TEST_LNBITS_URL', 'LNBITS_ADMIN_USERNAME', 'LNBITS_ADMIN_PASSWORD']) {
    if (!config[key]) throw new Error(`${key} must be set for browser tests`);
  }
  const url = new URL(config.TEST_LNBITS_URL);
  const loopback = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && loopback)) {
    throw new Error('TEST_LNBITS_URL must use HTTPS except for local loopback HTTP');
  }
  if (url.username || url.password) throw new Error('Do not embed credentials in TEST_LNBITS_URL');
  return {
    baseUrl: config.TEST_LNBITS_URL,
    username: config.LNBITS_ADMIN_USERNAME,
    password: config.LNBITS_ADMIN_PASSWORD,
    walletName: config.RECEIVING_WALLET_NAME,
    payLinkEmail: config.PAYLINK_EMAIL,
    createAmount: config.ALLOWANCE_TEST_CREATE_AMOUNT,
    editAmount: config.ALLOWANCE_TEST_EDIT_AMOUNT
  };
}

async function login(page) {
  const config = getConfig();
  await page.goto(config.baseUrl);
  await page.waitForLoadState('networkidle');
  if (page.url().includes('/first_install')) throw new Error('Complete dev onboarding before running browser tests');
  await page.getByLabel('Username or Email *', {exact: true}).fill(config.username);
  await page.getByLabel('Password *', {exact: true}).fill(config.password);
  const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/auth' && r.request().method() === 'POST');
  await page.getByRole('button', {name: /^login$/i}).click();
  const result = await response;
  if (!result.ok()) throw new Error(`Login failed: HTTP ${result.status()}`);
  await page.waitForURL(/\/wallet(?:\/|\?|$)/);
  await page.waitForLoadState('networkidle');
  const notice = page.getByRole('button', {name: /I understand/i});
  if (await notice.isVisible()) await notice.click();
}

module.exports = {login, getConfig};
