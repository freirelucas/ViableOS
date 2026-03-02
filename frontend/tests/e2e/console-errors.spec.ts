import { test, expect, type ConsoleMessage } from '@playwright/test';

/**
 * Browser-Konsolen-Überwachung für ViableOS
 * Fängt alle Errors, Warnings und Failed Requests ab
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

test.describe('Browser-Konsole Monitoring', () => {

  test('Startseite: Keine console.error Ausgaben', async ({ page }) => {
    const messages = await collectConsoleMessages(page, '/');

    const errors = messages.filter(m => m.type === 'error');

    if (errors.length > 0) {
      console.log('\n Console Errors gefunden:');
      errors.forEach(e => console.log(`   -> ${e.text}`));
    }

    expect(errors, `${errors.length} Console Error(s) gefunden`).toHaveLength(0);
  });

  test('Startseite: Console Warnings prüfen', async ({ page }) => {
    const messages = await collectConsoleMessages(page, '/');

    const warnings = messages.filter(m => m.type === 'warning');

    if (warnings.length > 0) {
      console.log('\n Console Warnings gefunden:');
      warnings.forEach(w => console.log(`   -> ${w.text}`));
    }

    test.info().annotations.push({
      type: 'warnings',
      description: `${warnings.length} Warning(s) gefunden`,
    });
  });

  test('Keine 404 oder 500 API-Responses', async ({ page }) => {
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
      console.log('\n Fehlerhafte HTTP Responses:');
      badResponses.forEach(r => console.log(`   -> ${r}`));
    }

    expect(badResponses).toHaveLength(0);
  });

  test('Screenshot der Startseite für visuellen Check', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await page.screenshot({
      path: 'tests/e2e/screenshots/homepage.png',
      fullPage: true,
    });
  });
});
