const {spawnSync} = require('node:child_process');
const path = require('node:path');
const scenarios = {
  allowance: ['ui/crud/allowance.spec.js', 'monthly allowance through the UI'],
  minutely: ['ui/crud/allowance.spec.js', 'minutely allowance through the UI'],
  hourly: ['ui/crud/allowance.spec.js', 'hourly allowance through the UI'],
  account: ['ui/setup/environment.spec.js', 'authenticated development account'],
  wallet: ['ui/setup/environment.spec.js', 'configured receiving wallet'],
  extension: ['ui/setup/environment.spec.js', 'Allowance installation and activation'],
  page: ['ui/setup/environment.spec.js', 'Allowance page and currencies'],
  paylinks: ['ui/setup/paylinks.spec.js', 'Pay Links installation and activation'],
  paylink: ['ui/setup/paylinks.spec.js', 'create and delete a disposable pay link']
};

function runScenario(name) {
  const scenario = scenarios[name];
  if (!scenario) throw new Error(`Unknown browser scenario: ${name}`);
  console.log(`Running browser scenario: ${scenario[1]}. Test records are removed after verification.`);
  const tests = path.resolve(__dirname, '..');
  const result = spawnSync(process.execPath, [require.resolve('@playwright/test/cli'),
    'test', scenario[0], '--grep', scenario[1], '--config', path.join(tests, 'playwright.config.js'),
    '--workers=1', '--reporter=line'], {cwd: tests, stdio: 'inherit'});
  if (result.error) throw result.error;
  process.exitCode = result.status === null ? 1 : result.status;
}
module.exports = {runScenario};
