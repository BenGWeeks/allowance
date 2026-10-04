const {test, expect} = require('@playwright/test');
const {login, getConfig} = require('../auth-helper');
const {getAdminApiKey} = require('../../get_api_key');
const {accountHeaders} = require('./account-headers');

async function openAllowance(page) {
  await login(page);
  await page.goto(getConfig().baseUrl + '/allowance/');
  await page.waitForLoadState('networkidle');
  await expect(page.getByRole('button', {name: /New Allowance/i})).toBeVisible();
  const notice = page.getByRole('button', {name: /I understand/i});
  if (await notice.isVisible()) await notice.click();
}

test('authenticated development account', async ({page}) => {
  await login(page);
  const response = await page.request.get(getConfig().baseUrl + '/api/v1/auth', {headers: await accountHeaders(page)});
  expect(response.status()).toBe(200);
  const account = await response.json();
  expect(account.id).toBeTruthy();
});

test('configured receiving wallet', async ({page}) => {
  await login(page);
  const key = await getAdminApiKey(page);
  expect(key, 'Configure exactly one existing development wallet').toBeTruthy();
  const response = await page.request.get(getConfig().baseUrl + '/api/v1/wallet', {headers: {'X-Api-Key': key}});
  expect(response.status()).toBe(200);
  expect((await response.json()).name).toBe(getConfig().walletName);
});

test('Allowance installation and activation', async ({page}) => {
  await openAllowance(page);
  const key = await getAdminApiKey(page);
  const health = await page.request.get(getConfig().baseUrl + '/allowance/api/v1/health', {headers: {'X-Api-Key': key}});
  expect(health.status()).toBe(200);
  expect((await health.json()).scheduler_ok).toBe(true);
});

test('Allowance page and currencies', async ({page}) => {
  await openAllowance(page);
  await page.getByRole('button', {name: /New Allowance/i}).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Currency', {exact: true}).click();
  await expect(page.getByRole('option', {name: /sats/i})).toBeVisible();
  await expect(page.getByRole('option', {name: /GBP/})).toBeVisible();
  await page.keyboard.press('Escape');
  await dialog.getByRole('button', {name: 'Cancel', exact: true}).click();
  await expect(dialog).toHaveCount(0);
});
