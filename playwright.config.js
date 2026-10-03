const {defineConfig, devices} = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: {timeout: 5_000},
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['line'], ['html', {open: 'never'}]] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:5511',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {name: 'chromium', use: {...devices['Desktop Chrome']}},
    {name: 'mobile', use: {...devices['Pixel 7']}},
  ],
  webServer: {
    command: 'node e2e/reset-data.js && python3 server.py --bind 127.0.0.1 --port 5511',
    env: {...process.env, POLYSOCIAL_DATA_DIR: '.e2e-data'},
    url: 'http://127.0.0.1:5511/api/status',
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
