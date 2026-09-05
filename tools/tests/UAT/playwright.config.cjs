const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: '.',
  testMatch: '**/*.spec.cjs',
  timeout: 120_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list'], ['json', { outputFile: process.env.M31_JSON_REPORT || 'evidence/playwright.json' }]],
  use: {
    baseURL: process.env.M31_BASE_URL || 'http://127.0.0.1:18220',
    browserName: 'chromium',
    channel: process.env.M31_BROWSER_CHANNEL || 'chrome',
    headless: process.env.M31_HEADLESS !== 'false',
    ignoreHTTPSErrors: false,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  outputDir: process.env.M31_OUTPUT_DIR || 'evidence/test-output',
});
