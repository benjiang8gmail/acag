import { expect, test, type Page } from '@playwright/test';

// The Phase 6 journeys from the spec (§12), adapted to the open-browsing design:
// sign-in is only asked for when refreshing.

const firstRun = async (page: Page, jur = 'Victoria') => {
  await page.goto('/');
  await page.getByRole('radio', { name: new RegExp(jur) }).click();
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('This fortnight in 30 seconds');
};

test('(a) brief → top item → source in 3 clicks or fewer', async ({ page }) => {
  await firstRun(page);
  const src = page.getByRole('link', { name: 'Open in Hansard ↗' }).first();
  await expect(src).toBeVisible();
  await expect(src).toHaveAttribute('href', /parliament\.vic\.gov\.au/);
});

test('(b) refresh → sign in → progress → summary → new items', async ({ page }, info) => {
  test.skip(!process.env.E2E_PASSWORD, 'set E2E_PASSWORD to run the refresh journey');
  test.skip(info.project.name !== 'desktop', 'the scan is shared server state; run it once');
  await firstRun(page);
  await page.getByRole('button', { name: /Updated/ }).first().click();
  await page.getByRole('button', { name: /Sign in to refresh|Refresh with/ }).click();
  const dialog = page.getByRole('dialog', { name: 'Sign in to refresh' });
  if (await dialog.isVisible()) {
    await dialog.getByLabel('Password').fill('wrong');
    await dialog.getByRole('button', { name: 'Sign in and refresh' }).click();
    await expect(dialog.getByRole('alert')).toHaveText('Username or password is incorrect.');
    await dialog.getByLabel('Password').fill(process.env.E2E_PASSWORD!);
    await dialog.getByRole('button', { name: 'Sign in and refresh' }).click();
  }
  await expect(page.getByText(/parliaments sat · .* new items/).first()).toBeVisible({ timeout: 15000 });
  await page.getByRole('button', { name: 'Show me' }).first().click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Explore');
  await expect(page.getByText('Treasurer relies on VAGO findings in budget update')).toBeVisible();
});

test('(c) Auditors-General → filter by side → open a mention', async ({ page }) => {
  await page.goto('/?view=mentions&jur=VIC');
  await page.getByRole('button', { name: 'Opposition', exact: true }).click();
  await expect(page).toHaveURL(/side=opposition/);
  await page.getByRole('button', { name: 'Details' }).first().click();
  await expect(page.getByText('AI summary — check the source')).toBeVisible();
});

test('(d) report → its mentions → source', async ({ page }) => {
  await page.goto('/?view=mentions&jur=VIC&tab=reports');
  await page.getByRole('button', { name: /Emergency department wait times/ }).click();
  await expect(page.getByRole('link', { name: 'Open in Hansard ↗' }).first()).toBeVisible();
});

test('(e) gaps → evidence → independence note', async ({ page }) => {
  await page.goto('/?view=gaps&jur=VIC');
  await page.getByRole('button', { name: 'Evidence and score' }).first().click();
  await expect(page.getByText(/Why this score/)).toBeVisible();
  await expect(page.getByRole('dialog').getByText(/Each Auditor-General sets their own program/)).toBeVisible();
});

test('(f) search → filter → results', async ({ page }) => {
  await page.goto('/?view=explore&jur=VIC');
  await page.getByRole('textbox', { name: 'Search Hansard' }).fill('consultant');
  await page.getByRole('button', { name: 'Only Victoria' }).click();
  await expect(page).toHaveURL(/q=consultant&scope=all/);
  await expect(page.getByRole('status').filter({ hasText: /results? across 9 parliaments/ })).toBeVisible();
});

test('(g) all 9 jurisdictions on the map and in the switcher', async ({ page }, info) => {
  await firstRun(page);
  if (info.project.name === 'desktop') {
    for (const n of ['Cth', 'NSW', 'Vic', 'Qld', 'SA', 'WA', 'Tas', 'ACT', 'NT']) await expect(page.locator('.ausmap').getByText(n, { exact: true })).toBeVisible();
  }
  await page.getByRole('button', { name: /^Jurisdiction:/ }).click();
  for (const n of ['Commonwealth', 'New South Wales', 'Victoria', 'Queensland', 'South Australia', 'Western Australia', 'Tasmania', 'Australian Capital Territory', 'Northern Territory']) {
    await expect(page.getByRole('menuitemradio', { name: new RegExp(n) })).toBeVisible();
  }
});

test('shared link opens the exact view and offers to switch back', async ({ page }) => {
  await firstRun(page);
  await page.goto('/?view=gaps&jur=NSW&sector=health');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Potential gaps in the forward program');
  await expect(page.getByText(/Opened from a shared link/)).toBeVisible();
  await page.getByRole('button', { name: 'Switch to Victoria' }).click();
  await expect(page).toHaveURL(/jur=VIC/);
});

test('sector filter applies everywhere and travels in the link', async ({ page }) => {
  await firstRun(page);
  await page.getByRole('button', { name: /All sectors/ }).first().click();
  await page.getByRole('menuitemradio', { name: /^Local government/ }).click();
  await expect(page).toHaveURL(/sector=local-government/);
  await expect(page.locator('.kicker')).toContainText('Local government');
});
