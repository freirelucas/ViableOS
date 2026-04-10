import { test, expect } from '@playwright/test';

/**
 * Smoke Tests: Checks that ViableOS fundamentally works
 * These tests should run after EVERY change
 */

test.describe('App Smoke Tests', () => {
  test('Homepage loads successfully', async ({ page }) => {
    const response = await page.goto('/');

    expect(response?.status()).toBeLessThan(400);

    await page.waitForLoadState('networkidle');

    const root = page.locator('#root');
    await expect(root).toBeVisible();
  });

  test('No critical network errors', async ({ page }) => {
    const failedRequests: string[] = [];

    page.on('requestfailed', (request) => {
      failedRequests.push(`${request.method()} ${request.url()} - ${request.failure()?.errorText}`);
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    if (failedRequests.length > 0) {
      console.error('Failed requests:', failedRequests);
    }
    expect(failedRequests).toHaveLength(0);
  });

  test('No unhandled JavaScript errors', async ({ page }) => {
    const jsErrors: string[] = [];

    page.on('pageerror', (error) => {
      jsErrors.push(error.message);
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await page.waitForTimeout(2000);

    if (jsErrors.length > 0) {
      console.error('JavaScript errors:', jsErrors);
    }
    expect(jsErrors).toHaveLength(0);
  });

  test('Page has a title', async ({ page }) => {
    await page.goto('/');
    const title = await page.title();
    expect(title).toBeTruthy();
    expect(title).not.toBe('');
  });
});
