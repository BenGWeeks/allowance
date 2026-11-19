const {test, expect} = require('@playwright/test');
const {login, getConfig} = require('../auth-helper');

test.use({serviceWorkers: 'block', timezoneId: 'Europe/London', viewport: {width: 1500, height: 1100}});

test('show the next payment clearly and retry a failed payment with edited details', async ({page}, testInfo) => {
  await login(page);
  const week = 7 * 86400;
  const next = Math.floor(Date.now() / 1000 / 3600) * 3600 + 2 * 86400 + 7200;
  const due = next - week;
  const lookupError = 'Lightning address lookup failed.';
  const wallet = {id: 'synthetic-wallet', name: 'Test wallet', adminkey: 'synthetic-key', inkey: 'synthetic-key'};
  const record = {
    id: 'synthetic-allowance', wallet: wallet.id, name: 'Weekly allowance', revision: 7,
    lightning_address: 'new@example.invalid', amount: 100, currency: 'sats',
    start_datetime: new Date((due - 4 * week) * 1000).toISOString(), next_payment_date: new Date(next * 1000).toISOString(),
    frequency_type: 'weekly', active: true, memo: '', end_datetime: null,
    timezone_name: 'Europe/London', pending_payment_hash: null,
    last_error: lookupError, last_error_time: new Date((due + 86400) * 1000).toISOString(),
    retry_count: 0, retry_after: null, retry_deadline: null, retry_resume_date: null
  };
  const recorded = {amount: 100, currency: 'sats', lightning_address: 'old@example.invalid'};
  const current = {amount: 100, currency: 'sats', lightning_address: record.lightning_address};
  const events = [{id: 'lookup', recorded_at: due + 60, scheduled_at: due, stage: 'address_lookup', code: 'address_lookup_failed', message: lookupError, retry_at: null}];
  let retryRequests = 0;
  await page.route('**/allowance/api/v1/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() === 'POST' && path.endsWith('/retry')) {
      retryRequests++;
      expect(request.postDataJSON()).toEqual({scheduled_at: due, revision: 7, confirmed: true, use_current_details: true});
      Object.assign(record, {revision: 8, next_payment_date: new Date(due * 1000).toISOString(), retry_after: new Date(Date.now() - 1000).toISOString(),
        retry_deadline: new Date(Date.now() + 80000000).toISOString(), retry_resume_date: new Date(next * 1000).toISOString()});
      return route.fulfill({status: 202, contentType: 'application/json', body: JSON.stringify({message: 'Retry queued for this payment. The regular schedule is preserved.'})});
    }
    if (request.method() !== 'GET') return route.abort();
    let body;
    if (path.endsWith('/health')) body = {scheduler_ok: true, overdue: 0, pending: 0};
    else if (path.endsWith('/allowance')) body = [record];
    else if (path.endsWith('/occurrences')) {
      body = retryRequests ? [
        {id: 'attempt', scheduled_at: due, completed_at: null, outcome: 'current', current: true, can_retry: false, details_changed: false, retry_block_reason: 'An earlier payment is already being retried.', details: current, events}
      ] : [
        {id: 'next', scheduled_at: next, completed_at: null, outcome: 'current', current: true, can_retry: false, details_changed: false, retry_block_reason: 'This payment is not due yet.', details: current, events: []},
        {id: 'attempt', scheduled_at: due, completed_at: due + 86400, outcome: 'failed', can_retry: true, details_changed: true, retry_block_reason: null, details: recorded, events}
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

  // The upcoming payment is labelled as such, with a countdown, and offers no retry.
  const upcoming = dialog.getByRole('row').filter({hasText: 'Next payment'});
  await expect(upcoming).toHaveCount(1);
  await expect(upcoming.getByText('in 2 days', {exact: true})).toBeVisible();
  await expect(dialog.getByText('last payment failed', {exact: false})).toHaveCount(0);
  await page.mouse.move(0, 0);
  await card.screenshot({animations: 'disabled', path: testInfo.outputPath('history-next-payment.png')});
  await upcoming.getByRole('button', {name: /^Details for/}).click();
  await expect(dialog.getByText('Next payment', {exact: true}).first()).toBeVisible();
  await expect(dialog.locator('[data-cy="schedule-note"]')).toHaveText(/^in 2 days · your local time \((GMT|BST|UTC)[^)]*\)$/);
  await expect(dialog.getByText('Not attempted yet.', {exact: true})).toBeVisible();
  await expect(dialog.getByText('The previous payment failed. Open it in the payment history to retry it.', {exact: true})).toBeVisible();
  await expect(dialog.getByText('This payment is not due yet.', {exact: true})).toHaveCount(0);
  await expect(dialog.getByRole('button', {name: 'Retry this payment', exact: true})).toHaveCount(0);
  await expect(dialog.getByRole('button', {name: 'Check payment status', exact: true})).toHaveCount(0);
  await expect(dialog.getByRole('button', {name: 'Edit allowance', exact: true})).toBeEnabled();
  await page.mouse.move(0, 0);
  await card.screenshot({animations: 'disabled', path: testInfo.outputPath('next-payment-details.png')});
  await page.setViewportSize({width: 390, height: 844});
  expect(await card.evaluate(node => node.scrollWidth <= node.clientWidth)).toBe(true);
  await page.setViewportSize({width: 1500, height: 1100});
  await dialog.getByRole('button', {name: 'Back to payment history', exact: true}).click();

  // The failed payment was scheduled with the old address; retrying pays the current one.
  await dialog.getByRole('row').filter({hasText: 'Failed'}).getByRole('button', {name: /^Details for/}).click();
  await expect(dialog.getByText('old@example.invalid', {exact: true})).toBeVisible();
  await expect(dialog.locator('[data-cy="details-changed"]')).toHaveText('The allowance has been edited since. Paying this now sends 100 sats to new@example.invalid.');
  await expect(dialog.locator('[data-cy="schedule-note"]')).toHaveText(/^Shown in your local time/);
  await page.mouse.move(0, 0);
  await card.screenshot({animations: 'disabled', path: testInfo.outputPath('edited-payment-details.png')});
  const retry = card.getByRole('button', {name: 'Retry this payment', exact: true});
  await retry.click();
  const confirmation = page.getByRole('dialog').filter({hasText: 'Retry this payment?'});
  await expect(confirmation.getByText(/Pay 100 sats to new@example\.invalid for the payment scheduled/)).toBeVisible();
  await expect(confirmation.getByText(/this payment was scheduled as 100 sats to old@example\.invalid\. The current details above are used\./)).toBeVisible();
  await confirmation.locator('.q-card').screenshot({animations: 'disabled', path: testInfo.outputPath('retry-confirmation.png')});
  await confirmation.getByRole('button', {name: 'Cancel', exact: true}).click();
  await expect(confirmation).not.toBeVisible();
  expect(retryRequests).toBe(0);
  await retry.click();
  await confirmation.getByRole('button', {name: 'Retry this payment', exact: true}).click();
  await expect.poll(() => retryRequests).toBe(1);
  await expect(confirmation).not.toBeVisible();
  await expect(dialog.getByText('new@example.invalid', {exact: true})).toBeVisible();
  await expect(dialog.locator('[data-cy="details-changed"]')).toHaveCount(0);
  await expect(retry).toBeDisabled();
  expect(retryRequests).toBe(1);
});
