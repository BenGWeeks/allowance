const {test, expect} = require('@playwright/test');
const {login, getConfig} = require('../auth-helper');

test.use({serviceWorkers: 'block', timezoneId: 'Europe/London', viewport: {width: 1500, height: 1100}});

test('payment diagnostics explain failures and keep action sizes consistent', async ({page}, testInfo) => {
  await login(page);
  const wallet = {id: 'synthetic-wallet', name: 'Test wallet', adminkey: 'synthetic-key', inkey: 'synthetic-key'};
  const record = {
    id: 'synthetic-allowance', wallet: wallet.id, name: 'Weekly allowance', revision: 0,
    lightning_address: 'recipient@example.invalid', amount: 100, currency: 'sats',
    start_datetime: '2026-09-01T09:00:00Z', next_payment_date: '2026-10-03T22:00:00Z',
    frequency_type: 'weekly', active: true, memo: '', end_datetime: null,
    timezone_name: 'Europe/London', pending_payment_hash: null,
    last_error: 'LNURL host resolves to a private or otherwise disallowed address. Blocked by the public-address policy; contact the server operator.',
    last_error_time: '2026-10-04T10:00:00Z', retry_after: new Date(Date.now() + 3600000).toISOString(), retry_deadline: new Date(Date.now() + 86400000).toISOString()
  };
  let logRequests = 0;
  let retryRequests = 0;
  await page.route('**/allowance/api/v1/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() === 'POST' && path.endsWith('/retry')) {
      retryRequests++;
      expect(request.postDataJSON()).toEqual({scheduled_at: 1791064800, revision: 0, confirmed: true});
      record.retry_after = new Date(Date.now() - 1000).toISOString();
      return route.fulfill({status: 202, contentType: 'application/json', body: JSON.stringify({message: 'Retry queued'})});
    }
    if (request.method() !== 'GET') return route.abort();
    let body;
    if (path.endsWith('/health')) body = {scheduler_ok: true, overdue: 1, pending: 0};
    else if (path.endsWith('/allowance')) body = [record];
    else if (path.endsWith('/occurrences')) {
      logRequests++;
      body = [{id: 'attempt', scheduled_at: 1791064800, completed_at: null, outcome: 'current', current: true,
        can_retry: retryRequests === 0, retry_block_reason: retryRequests ? 'An attempt is already queued.' : null,
        details: {amount: 100, currency: 'sats', lightning_address: record.lightning_address},
        events: [{id: 'log', recorded_at: 1791108000, scheduled_at: 1791064800,
        stage: 'address_lookup', code: 'private_address', message: record.last_error, retry_at: null}]}];
    } else if (path.endsWith('/' + record.id)) body = record;
    else return route.abort();
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
  const row = page.getByRole('row').filter({hasText: 'Weekly allowance'});
  const buttons = row.getByRole('button');
  await expect(buttons).toHaveCount(5);
  const sizes = await buttons.evaluateAll(nodes => nodes.map(node => ({
    button: node.getBoundingClientRect().height,
    icon: node.querySelector('.q-icon').getBoundingClientRect().height
  })));
  expect(new Set(sizes.map(size => size.button)).size).toBe(1);
  expect(new Set(sizes.map(size => size.icon)).size).toBe(1);
  await expect(row.getByRole('button', {name: 'Check payment status', exact: true})).toBeDisabled();
  await row.screenshot({animations: 'disabled', path: testInfo.outputPath('consistent-action-icons.png')});
  await row.getByRole('button', {name: 'Payment history', exact: true}).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByText('private_address', {exact: false})).toBeVisible();
  await expect(dialog.getByRole('button', {name: 'Check payment status', exact: true})).toBeDisabled();
  await expect(dialog.getByText(/Checking payment status never sends/)).toBeVisible();
  await dialog.getByRole('button', {name: 'Refresh history', exact: true}).click();
  await expect.poll(() => logRequests).toBe(2);
  await expect(dialog.getByRole('button', {name: 'Refresh history', exact: true})).toBeEnabled();
  await dialog.locator('.q-card').screenshot({animations: 'disabled', path: testInfo.outputPath('payment-diagnostics.png')});
  await dialog.getByRole('button', {name: 'Retry this payment', exact: true}).click();
  const confirmation = page.getByRole('dialog').filter({hasText: 'Retry this payment?'});
  await expect(confirmation.getByText(/Pay 100 sats to recipient@example.invalid/)).toBeVisible();
  await confirmation.getByRole('button', {name: 'Cancel', exact: true}).click();
  await expect(confirmation).not.toBeVisible();
  expect(retryRequests).toBe(0);
  await dialog.getByRole('button', {name: 'Retry this payment', exact: true}).click();
  await confirmation.locator('.q-card').screenshot({animations: 'disabled', path: testInfo.outputPath('retry-confirmation.png')});
  await confirmation.getByRole('button', {name: 'Retry this payment', exact: true}).click();
  await expect.poll(() => retryRequests).toBe(1);
  await expect(dialog.getByRole('button', {name: 'Retry this payment', exact: true})).toBeDisabled();
  await expect(dialog.getByText('An attempt is already queued.', {exact: true})).toBeVisible();
  await dialog.getByRole('button', {name: 'Edit allowance', exact: true}).click();
  await expect(dialog.getByLabel('Allowance description *', {exact: true})).toHaveValue(record.name);
  await dialog.getByRole('button', {name: 'Cancel', exact: true}).click();
});
