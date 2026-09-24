const {test, expect} = require('@playwright/test');
const {login, getConfig} = require('../auth-helper');

test.use({timezoneId: 'Europe/London', viewport: {width: 1280, height: 1100}});

test('daily and one-off options, timezone and legacy memo editing', async ({page}, testInfo) => {
  await login(page);
  const wallet = {id: 'synthetic-wallet', name: 'Family wallet', adminkey: 'synthetic-key', inkey: 'synthetic-key'};
  const record = {
    id: 'synthetic-allowance', wallet: wallet.id, name: 'Weekly allowance', revision: 0,
    lightning_address: 'recipient@example.invalid', amount: 100, currency: 'sats',
    start_datetime: '2026-09-01T09:00:00Z', next_payment_date: '2026-10-01T09:00:00Z',
    frequency_type: 'weekly', active: false, memo: null, end_datetime: null,
    timezone_name: 'Europe/London'
  };
  let edited;
  await page.route('**/allowance/api/v1/**', async route => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    let body;
    if (request.method() === 'PUT') {
      edited = request.postDataJSON();
      body = {...record, ...edited};
    } else if (request.method() !== 'GET') return route.abort();
    else if (pathname.endsWith('/health')) body = {scheduler_ok: true, overdue: 0, pending: 0};
    else if (pathname.endsWith('/allowance')) body = [record];
    else return route.continue();
    return route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
  });
  await page.goto(getConfig().baseUrl + '/allowance/');
  await page.waitForLoadState('networkidle');
  const notice = page.getByRole('button', {name: /I understand/i});
  if (await notice.isVisible()) await notice.click();
  await page.evaluate(({wallet, record}) => {
    const root = document.querySelector('[data-cy="allowance-extension"]');
    const vm = [window.app, window.app?._instance?.proxy, window.app?._container?._vnode?.component?.proxy, root.__vueParentComponent?.proxy].find(value => typeof value?.getAllowances === 'function');
    vm.g.user.wallets = [wallet];
    vm.allowances = [record];
  }, {wallet, record});
  const dialog = page.getByRole('dialog');
  await page.getByRole('button', {name: /New Allowance/i}).click();
  await expect(dialog.getByText('Schedule timezone: Europe/London', {exact: true})).toBeVisible();
  await dialog.getByLabel('Frequency *', {exact: true}).click();
  await expect(page.getByRole('option', {name: 'Daily', exact: true})).toBeVisible();
  await expect(page.getByRole('option', {name: 'Once', exact: true})).toBeVisible();
  await page.getByRole('option', {name: 'Daily', exact: true}).click();
  await expect(page.getByRole('option', {name: 'Daily', exact: true})).toHaveCount(0);
  await dialog.getByLabel('Allowance description *', {exact: true}).fill('Daily allowance');
  await dialog.getByLabel('Recipient lightning address *', {exact: true}).fill('recipient@example.invalid');
  await dialog.getByLabel('Amount *', {exact: true}).fill('100');
  await dialog.locator('.q-card').screenshot({animations: 'disabled', path: testInfo.outputPath('local-time-schedule.png')});
  await dialog.getByRole('button', {name: 'Cancel', exact: true}).click();
  await page.getByRole('row').filter({hasText: 'Weekly allowance'}).getByRole('button', {name: 'Edit allowance', exact: true}).click();
  await expect(dialog.getByLabel('Message (optional)', {exact: true})).toHaveValue('');
  await expect(dialog.locator('.q-select').filter({hasText: 'Wallet to send funds from *'})).toHaveClass(/disabled/);
  await dialog.locator('.q-card').screenshot({animations: 'disabled', path: testInfo.outputPath('legacy-allowance-edit.png')});
  const saved = page.waitForResponse(response => response.request().method() === 'PUT');
  await dialog.getByRole('button', {name: 'Update Allowance', exact: true}).click();
  expect((await saved).status()).toBe(200);
  expect(edited.memo).toBe('');
  expect(edited.wallet).toBe(wallet.id);
});
