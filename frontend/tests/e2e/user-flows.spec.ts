import { test, expect } from '@playwright/test';

/**
 * User Flow Tests für ViableOS
 * Simuliert echte User-Interaktionen
 *
 * Nutze data-testid Attribute in React-Komponenten:
 *   <button data-testid="submit-btn">Absenden</button>
 */

test.describe('User Flows', () => {

  // ============================================================
  // Chat Flow
  // ============================================================
  test('Chat-Interface ist sichtbar', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // TODO: Passe Selektoren an die Chat-Komponente an
    // await expect(page.locator('[data-testid="chat-window"]')).toBeVisible();
    // await expect(page.locator('[data-testid="chat-input"]')).toBeVisible();
  });

  // ============================================================
  // Wizard Flow
  // ============================================================
  test('Wizard ist erreichbar', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // TODO: Navigation zum Wizard
    // await page.click('[data-testid="start-wizard-btn"]');
    // await expect(page.locator('[data-testid="wizard-step-1"]')).toBeVisible();
  });

  // ============================================================
  // API-Interaktion
  // ============================================================
  test('API-Calls zum Backend (Port 8000) funktionieren', async ({ page }) => {
    await page.route('**/api/**', async (route) => {
      const response = await route.fetch();
      const status = response.status();

      expect(status).toBeLessThan(500);

      await route.fulfill({ response });
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  // ============================================================
  // Responsive Design
  // ============================================================
  test('Mobile Ansicht funktioniert', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await page.screenshot({
      path: 'tests/e2e/screenshots/mobile-view.png',
    });
  });
});
