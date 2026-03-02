import { test, expect } from '@playwright/test';

/**
 * Smoke Tests: Prüft ob ViableOS grundsätzlich funktioniert
 * Diese Tests sollten nach JEDER Änderung laufen
 */

test.describe('App Smoke Tests', () => {
  test('Startseite lädt erfolgreich', async ({ page }) => {
    const response = await page.goto('/');

    expect(response?.status()).toBeLessThan(400);

    await page.waitForLoadState('networkidle');

    const root = page.locator('#root');
    await expect(root).toBeVisible();
  });

  test('Keine kritischen Netzwerk-Fehler', async ({ page }) => {
    const failedRequests: string[] = [];

    page.on('requestfailed', (request) => {
      failedRequests.push(`${request.method()} ${request.url()} - ${request.failure()?.errorText}`);
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    if (failedRequests.length > 0) {
      console.error('Fehlgeschlagene Requests:', failedRequests);
    }
    expect(failedRequests).toHaveLength(0);
  });

  test('Keine unbehandelten JavaScript-Fehler', async ({ page }) => {
    const jsErrors: string[] = [];

    page.on('pageerror', (error) => {
      jsErrors.push(error.message);
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await page.waitForTimeout(2000);

    if (jsErrors.length > 0) {
      console.error('JavaScript Fehler:', jsErrors);
    }
    expect(jsErrors).toHaveLength(0);
  });

  test('Seite hat einen Titel', async ({ page }) => {
    await page.goto('/');
    const title = await page.title();
    expect(title).toBeTruthy();
    expect(title).not.toBe('');
  });
});
