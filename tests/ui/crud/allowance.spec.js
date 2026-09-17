const {test, expect} = require('@playwright/test');
const {login, getConfig} = require('../auth-helper');
const {getAdminApiKey} = require('../../get_api_key');

test('create, edit, reload and delete a monthly allowance through the UI', async ({page}, testInfo) => {
  const config = getConfig();
  if (process.env.ALLOWANCE_UI_TEST_CONFIRM !== config.baseUrl) {
    throw new Error('Set ALLOWANCE_UI_TEST_CONFIRM to the exact dev URL to authorize test writes');
  }
  if (!config.payLinkEmail) throw new Error('PAYLINK_EMAIL must be set');
  for (const amount of [config.createAmount, config.editAmount]) {
    if (!amount || !Number.isSafeInteger(Number(amount)) || Number(amount) <= 0) {
      throw new Error('Set ALLOWANCE_TEST_CREATE_AMOUNT and ALLOWANCE_TEST_EDIT_AMOUNT to positive integer sats');
    }
  }
  const name = `Playwright allowance ${Date.now()}`;
  const updatedName = `${name} edited`;
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await login(page);
  const key = await getAdminApiKey(page);
  expect(key).toBeTruthy();
  const headers = {'X-Api-Key': key};
  let createdId;
  try {
    await page.goto(`${config.baseUrl}/allowance/`);
    await page.waitForLoadState('networkidle');
    const notice = page.getByRole('button', {name: /I understand/i});
    if (await notice.isVisible()) await notice.click();
    await page.getByRole('button', {name: /New Allowance/i}).click();
    const dialog = page.getByRole('dialog');
    await dialog.getByLabel('Allowance description *', {exact: true}).fill(name);
    await dialog.getByLabel('Recipient lightning address *', {exact: true}).fill(config.payLinkEmail);
    await dialog.getByLabel('Amount *', {exact: true}).fill(config.createAmount);
    await dialog.getByLabel('Message (optional)', {exact: true}).fill('Playwright create');
    await dialog.getByLabel('Frequency *', {exact: true}).click();
    await page.getByRole('option', {name: 'Monthly', exact: true}).click();
    // Leave the default future start; inactive allowances cannot send payments.
    await dialog.getByRole('switch', {name: 'Active', exact: true}).click();
    const createdResponse = page.waitForResponse(r => new URL(r.url()).pathname === '/allowance/api/v1/allowance' && r.request().method() === 'POST');
    await dialog.getByRole('button', {name: /^Create Allowance$/i}).click();
    const created = await createdResponse;
    expect(created.status(), await created.text()).toBe(201);
    const original = await created.json();
    createdId = original.id;
    expect(original.active).toBe(false);
    expect(original.memo).toBe('Playwright create');
    expect(original.frequency_type).toBe('monthly');
    await expect(page.getByRole('row').filter({hasText: name})).toBeVisible();
    await page.screenshot({path: testInfo.outputPath('created.png'), fullPage: true});

    let row = page.getByRole('row').filter({hasText: name});
    await row.getByRole('button', {name: 'Edit allowance', exact: true}).click();
    await expect(dialog.getByLabel('Start date & time *', {exact: true})).toBeDisabled();
    await expect(dialog.locator('.q-select').filter({hasText: 'Frequency *'})).toHaveClass(/disabled/);
    await dialog.getByLabel('Allowance description *', {exact: true}).fill(updatedName);
    await dialog.getByLabel('Amount *', {exact: true}).fill(config.editAmount);
    await dialog.getByLabel('Message (optional)', {exact: true}).fill('Playwright edited');
    const updatedResponse = page.waitForResponse(r => r.url().endsWith(`/allowance/api/v1/allowance/${createdId}`) && r.request().method() === 'PUT');
    await dialog.getByRole('button', {name: /^Update Allowance$/i}).click();
    const updated = await updatedResponse;
    expect(updated.status(), await updated.text()).toBe(200);
    await page.reload();
    row = page.getByRole('row').filter({hasText: updatedName});
    await expect(row).toBeVisible();
    const persistedResponse = await page.request.get(`${config.baseUrl}/allowance/api/v1/allowance/${createdId}`, {headers});
    expect(persistedResponse.status()).toBe(200);
    const persisted = await persistedResponse.json();
    expect(persisted.name).toBe(updatedName);
    expect(persisted.amount).toBe(Number(config.editAmount));
    expect(persisted.memo).toBe('Playwright edited');
    expect(persisted.active).toBe(false);
    expect(persisted.start_datetime).toBe(original.start_datetime);
    expect(persisted.next_payment_date).toBe(original.next_payment_date);
    await page.screenshot({path: testInfo.outputPath('edited.png'), fullPage: true});

    await row.getByRole('button', {name: 'Delete allowance', exact: true}).click();
    const deletedResponse = page.waitForResponse(r => r.url().endsWith(`/allowance/api/v1/allowance/${createdId}`) && r.request().method() === 'DELETE');
    await page.getByRole('dialog').getByRole('button', {name: /^OK$/i}).click();
    expect((await deletedResponse).status()).toBe(200);
    await page.reload();
    await expect(page.getByRole('row').filter({hasText: updatedName})).toHaveCount(0);
    expect((await page.request.get(`${config.baseUrl}/allowance/api/v1/allowance/${createdId}`, {headers})).status()).toBe(404);
    createdId = null;
    await page.screenshot({path: testInfo.outputPath('deleted.png'), fullPage: true});
    expect(errors).toEqual([]);
  } finally {
    // Remove only this run's record if a browser assertion fails midway.
    if (createdId) {
      const cleanup = await page.request.delete(`${config.baseUrl}/allowance/api/v1/allowance/${createdId}`, {headers});
      expect([200, 404]).toContain(cleanup.status());
    }
  }
});
