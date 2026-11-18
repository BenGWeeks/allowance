const {test, expect} = require('@playwright/test');
const {login, getConfig} = require('../auth-helper');

test.use({serviceWorkers: 'block', timezoneId: 'Europe/London', viewport: {width: 1500, height: 1100}});

test('cancel an older retry so the allowance can be edited', async ({page}, testInfo) => {
  await login(page);
  const week = 7 * 86400;
  const due = Math.floor(Date.now() / 1000 / 3600) * 3600 - 4 * 86400;
  const resume = new Date((due + week) * 1000).toISOString();
  const lookupError = 'Lightning address lookup failed.';
  const wallet = {id: 'synthetic-wallet', name: 'Test wallet', adminkey: 'synthetic-key', inkey: 'synthetic-key'};
  const record = {
    id: 'synthetic-allowance', wallet: wallet.id, name: 'Weekly allowance', revision: 4,
    lightning_address: 'recipient@example.invalid', amount: 100, currency: 'sats',
    start_datetime: new Date((due - 4 * week) * 1000).toISOString(), next_payment_date: new Date(due * 1000).toISOString(),
    frequency_type: 'weekly', active: true, memo: '', end_datetime: null,
    timezone_name: 'Europe/London', pending_payment_hash: null,
    last_error: lookupError, last_error_time: new Date(Date.now() - 600000).toISOString(),
    retry_count: 5, retry_after: new Date(Date.now() + 1800000).toISOString(),
    retry_deadline: new Date(Date.now() + 80000000).toISOString(), retry_resume_date: resume
  };
  const details = {amount: 100, currency: 'sats', lightning_address: record.lightning_address};
  const events = [
    {id: 'request', recorded_at: due + 340000, scheduled_at: due, stage: 'retry', code: 'manual_retry_requested', message: 'User requested a retry of this scheduled payment.', retry_at: due + 340000},
    {id: 'lookup', recorded_at: due + 340060, scheduled_at: due, stage: 'address_lookup', code: 'address_lookup_failed', message: lookupError, retry_at: null}
  ];
  let cancelRequests = 0;
  await page.route('**/allowance/api/v1/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() === 'POST' && path.endsWith('/retry/cancel')) {
      cancelRequests++;
      expect(request.postDataJSON()).toEqual({revision: 4});
      Object.assign(record, {revision: 5, next_payment_date: resume, retry_count: 0, retry_after: null, retry_deadline: null, retry_resume_date: null});
      events.push({id: 'cancel', recorded_at: due + 340120, scheduled_at: due, stage: 'retry', code: 'manual_retry_cancelled', message: 'User cancelled the requested retry. Nothing was sent.', retry_at: null});
      return route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify({message: 'Retry cancelled. Nothing was sent and the regular schedule is preserved.'})});
    }
    if (request.method() !== 'GET') return route.abort();
    let body;
    if (path.endsWith('/health')) body = {scheduler_ok: true, overdue: cancelRequests ? 0 : 1, pending: 0};
    else if (path.endsWith('/allowance')) body = [record];
    else if (path.endsWith('/occurrences')) {
      body = cancelRequests ? [
        {id: 'next', scheduled_at: due + week, completed_at: null, outcome: 'current', current: true, can_retry: false, retry_block_reason: 'There is no confirmed-unsent failure eligible for retry.', details, events: []},
        {id: 'attempt', scheduled_at: due, completed_at: due + 86400, outcome: 'failed', can_retry: true, retry_block_reason: null, details, events}
      ] : [
        {id: 'attempt', scheduled_at: due, completed_at: null, outcome: 'current', current: true, can_retry: false, retry_block_reason: 'An earlier payment is already being retried.', details, events}
      ];
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
  await row.getByRole('button', {name: 'Payment history', exact: true}).click();
  const dialog = page.getByRole('dialog');
  const card = dialog.locator('[data-cy="payment-history-card"]');
  await dialog.getByRole('button', {name: /^Details for/}).click();
  await expect(dialog.getByText('An earlier payment is already being retried.', {exact: true})).toBeVisible();
  await page.mouse.move(0, 0);
  await card.screenshot({animations: 'disabled', path: testInfo.outputPath('retry-details.png')});
  const cancel = dialog.getByRole('button', {name: 'Cancel retry', exact: true});
  await expect(cancel).toBeEnabled();
  await expect(dialog.getByRole('button', {name: 'Retry this payment', exact: true})).toBeDisabled();

  await page.setViewportSize({width: 390, height: 844});
  await expect(cancel).toBeVisible();
  expect(await card.evaluate(node => node.scrollWidth <= node.clientWidth)).toBe(true);
  await page.mouse.move(0, 0);
  await card.screenshot({animations: 'disabled', path: testInfo.outputPath('retry-details-mobile.png')});
  await page.setViewportSize({width: 1500, height: 1100});

  await cancel.click();
  const confirmation = page.getByRole('dialog').filter({hasText: 'Cancel this retry?'});
  await expect(confirmation.getByText(/nothing is sent/)).toBeVisible();
  await confirmation.getByRole('button', {name: 'Keep retrying', exact: true}).click();
  await expect(confirmation).not.toBeVisible();
  expect(cancelRequests).toBe(0);
  await cancel.click();
  await confirmation.locator('.q-card').screenshot({animations: 'disabled', path: testInfo.outputPath('cancel-confirmation.png')});
  await confirmation.getByRole('button', {name: 'Cancel retry', exact: true}).click();
  await expect.poll(() => cancelRequests).toBe(1);
  await expect(confirmation).not.toBeVisible();

  await expect(cancel).toHaveCount(0);
  await expect(dialog.getByRole('button', {name: /^Details for/})).toHaveCount(2);
  await page.mouse.move(0, 0);
  await card.screenshot({animations: 'disabled', path: testInfo.outputPath('history-after-cancel.png')});
  await dialog.getByRole('button', {name: /^Details for/}).nth(1).click();
  await expect(dialog.getByText('manual_retry_cancelled', {exact: false})).toBeVisible();
  await expect(cancel).toHaveCount(0);
  await dialog.getByRole('button', {name: 'Back to payment history', exact: true}).click();
  await dialog.getByRole('button', {name: 'Edit allowance', exact: true}).click();
  await expect(dialog.getByLabel('Recipient lightning address *', {exact: true})).toHaveValue(record.lightning_address);
  await dialog.getByRole('button', {name: 'Cancel', exact: true}).click();
  expect(cancelRequests).toBe(1);
});
