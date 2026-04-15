import { test, expect } from '@playwright/test';

/**
 * User Flow Tests for ViableOS
 * Simulates real user interactions
 *
 * Use data-testid attributes in React components:
 *   <button data-testid="submit-btn">Submit</button>
 */

test.describe('User Flows', () => {

  // ============================================================
  // Chat Flow
  // ============================================================
  test('Chat interface is visible', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // TODO: Adjust selectors to match the chat component
    // await expect(page.locator('[data-testid="chat-window"]')).toBeVisible();
    // await expect(page.locator('[data-testid="chat-input"]')).toBeVisible();
  });

  // ============================================================
  // Wizard Flow
  // ============================================================
  test('Wizard is reachable', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // TODO: Navigate to wizard
    // await page.click('[data-testid="start-wizard-btn"]');
    // await expect(page.locator('[data-testid="wizard-step-1"]')).toBeVisible();
  });

  // ============================================================
  // API Interaction
  // ============================================================
  test('API calls to backend (port 8000) work', async ({ page }) => {
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
  test('Mobile view works', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await page.screenshot({
      path: 'tests/e2e/screenshots/mobile-view.png',
    });
  });
});
