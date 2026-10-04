const {expect} = require('@playwright/test');
const {getConfig} = require('../auth-helper');
async function accountHeaders(page) {
  const config = getConfig();
  const response = await page.request.post(config.baseUrl + '/api/v1/auth', {
    data: {username: config.username, password: config.password}
  });
  expect(response.status()).toBe(200);
  const {access_token: token} = await response.json();
  expect(token).toBeTruthy();
  return {Authorization: `Bearer ${token}`};
}
module.exports = {accountHeaders};
