import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

// Fluent's focus-trap sentinels (tabster dummies) are hidden <i tabindex=0> elements that redirect focus; axe flags them as a false positive.
const axe = (page: import('@playwright/test').Page) => new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).exclude('[data-tabster-dummy]');

// SC3: WCAG 2.2 AA with no serious or critical axe findings.
const PAGES = ['brief', 'compare', 'mentions', 'developments', 'gaps', 'explore'];

for (const view of PAGES) {
  test(`no serious or critical axe findings: ${view}`, async ({ page }) => {
    await page.goto(`/?view=${view}&jur=VIC`);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const r = await axe(page).analyze();
    const bad = r.violations.filter(v => v.impact === 'serious' || v.impact === 'critical');
    expect(bad.map(v => `${v.id}: ${v.nodes.slice(0, 3).map(n => n.target.join(' ')).join(' | ')}`)).toEqual([]);
  });
}

test('no serious or critical axe findings: first run', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Which jurisdiction are you from?')).toBeVisible();
  const r = await axe(page).analyze();
  expect(r.violations.filter(v => v.impact === 'serious' || v.impact === 'critical').map(v => v.id)).toEqual([]);
});
