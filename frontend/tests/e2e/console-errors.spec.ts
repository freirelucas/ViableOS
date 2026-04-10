import { test, expect, type ConsoleMessage } from '@playwright/test';

/**
 * Browser console monitoring for ViableOS
 * Catches all errors, warnings, and failed requests
 */

async function collectConsoleMessages(page: any, url: string) {
  const messages: { type: string; text: string }[] = [];

  page.on('console', (msg: ConsoleMessage) => {
    messages.push({
      type: msg.type(),
      text: msg.text(),
    });
  });

  await page.goto(url);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(3000);

  return messages;
}

test.describe('Browser Console Monitoring', () => {

  test('Homepage: No console.error output', async ({ page }) => {
    const messages = await collectConsoleMessages(page, '/');

    const errors = messages.filter(m => m.type === 'error');

    if (errors.length > 0) {
      console.log('\n Console errors found:');
      errors.forEach(e => console.log(`   -> ${e.text}`));
    }

    expect(errors, `${errors.length} console error(s) found`).toHaveLength(0);
  });

  test('Homepage: Check console warnings', async ({ page }) => {
    const messages = await collectConsoleMessages(page, '/');

    const warnings = messages.filter(m => m.type === 'warning');

    if (warnings.length > 0) {
      console.log('\n Console warnings found:');
      warnings.forEach(w => console.log(`   -> ${w.text}`));
    }

    test.info().annotations.push({
      type: 'warnings',
      description: `${warnings.length} warning(s) found`,
    });
  });

  test('No 404 or 500 API responses', async ({ page }) => {
    const badResponses: string[] = [];

    page.on('response', (response: any) => {
      const status = response.status();
      if (status >= 400) {
        badResponses.push(`${status} ${response.url()}`);
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    if (badResponses.length > 0) {
      console.log('\n Bad HTTP responses:');
      badResponses.forEach(r => console.log(`   -> ${r}`));
    }

    expect(badResponses).toHaveLength(0);
  });

  test('Screenshot of homepage for visual check', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await page.screenshot({
      path: 'tests/e2e/screenshots/homepage.png',
      fullPage: true,
    });
  });
});
