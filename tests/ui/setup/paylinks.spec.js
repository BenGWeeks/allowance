const {test, expect} = require('@playwright/test');
const {login, getConfig} = require('../auth-helper');
const {getAdminApiKey} = require('../../get_api_key');

async function openPayLinks(page) {
  await login(page);
  await page.goto(getConfig().baseUrl + '/lnurlp/');
  await page.waitForLoadState('networkidle');
  const notice = page.getByRole('button', {name: /I understand/i});
  if (await notice.isVisible()) await notice.click();
  await expect(page.getByRole('button', {name: /New Pay Link/i}),
    'Install Pay Links and enable it for the development account before running its integration tests').toBeVisible();
}

test('Pay Links installation and activation', async ({page}) => {
  await openPayLinks(page);
  const key = await getAdminApiKey(page);
  const response = await page.request.get(getConfig().baseUrl + '/lnurlp/api/v1/links', {headers: {'X-Api-Key': key}});
  expect(response.status()).toBe(200);
  expect(Array.isArray(await response.json())).toBe(true);
});

test('create and delete a disposable pay link', async ({page}) => {
  const config = getConfig();
  if (process.env.ALLOWANCE_UI_TEST_CONFIRM !== config.baseUrl) {
    throw new Error('Set ALLOWANCE_UI_TEST_CONFIRM to the exact dev URL to authorize test writes');
  }
  await openPayLinks(page);
  const key = await getAdminApiKey(page);
  const headers = {'X-Api-Key': key};
  const name = `Playwright pay link ${Date.now()}`;
  let id;
  try {
    await page.getByRole('button', {name: /New Pay Link/i}).click();
    const dialog = page.getByRole('dialog');
    await dialog.getByLabel('Wallet *', {exact: true}).click();
    await page.getByRole('option', {name: config.walletName + ' -', exact: false}).click();
    await dialog.getByLabel('Item description *', {exact: true}).fill(name);
    await dialog.getByLabel('Lightning Address', {exact: true}).fill(`pw${Date.now()}`);
    await dialog.getByLabel('Amount *', {exact: true}).fill('2');
    const createdResponse = page.waitForResponse(response =>
      new URL(response.url()).pathname === '/lnurlp/api/v1/links' && response.request().method() === 'POST');
    await dialog.getByRole('button', {name: 'Create pay link', exact: true}).click();
    const created = await createdResponse;
    expect(created.status()).toBe(201);
    const record = await created.json();
    id = record.id;
    expect(record.description).toBe(name);
    expect(record.min).toBe(2);
    expect(record.max).toBe(2);
    await page.reload();
    await page.waitForLoadState('networkidle');
    const row = page.getByRole('row').filter({hasText: name});
    await expect(row).toBeVisible();
    const deletion = page.waitForResponse(response =>
      new URL(response.url()).pathname === `/lnurlp/api/v1/links/${id}` && response.request().method() === 'DELETE');
    await row.getByRole('button').filter({has: page.locator('.q-icon').filter({hasText: /^cancel$/})}).click();
    await page.getByRole('dialog').getByRole('button', {name: 'OK', exact: true}).click();
    expect((await deletion).status()).toBe(200);
    await expect(row).toHaveCount(0);
    expect((await page.request.get(`${config.baseUrl}/lnurlp/api/v1/links/${id}`, {headers})).status()).toBe(404);
    id = null;
  } finally {
    if (id) {
      const cleanup = await page.request.delete(`${config.baseUrl}/lnurlp/api/v1/links/${id}`, {headers});
      expect([200, 404]).toContain(cleanup.status());
    }
  }
});
