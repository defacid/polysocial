const {test, expect} = require('@playwright/test');

const pixel = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Z3nQAAAAASUVORK5CYII=', 'base64');

test('compose, annotate, schedule, edit, and publish now', async ({page}) => {
  await page.goto('/');
  await expect(page.getByRole('heading', {name: 'Create post'})).toBeVisible();

  for (const platform of ['facebook', 'instagram', 'threads']) {
    await page.locator(`#${platform}`).selectOption('none');
  }
  await page.locator('#bluesky').selectOption('connected');
  await page.locator('#postText').fill('Playwright scheduled post');
  await page.locator('#scheduleTime').fill('2099-01-02T12:30');
  await page.locator('#mediaInput').setInputFiles({name: 'pixel.png', mimeType: 'image/png', buffer: pixel});
  page.once('dialog', dialog => dialog.accept('A single test pixel'));
  await page.getByRole('button', {name: /Add alt text/}).click();
  await page.locator('#postForm button.primary-button').first().click();

  const card = page.locator('.scheduled-post').filter({hasText: 'Playwright scheduled post'});
  await expect(card).toBeVisible();
  await card.getByRole('button', {name: /Edit post/}).click();
  await expect(page.locator('#postText')).toHaveValue('Playwright scheduled post');
  await expect(page.locator('.alt-media')).toHaveClass(/complete/);
  await page.locator('#postForm button.primary-button').first().click();
  await expect(card).toBeVisible();
  await card.getByTitle('Publish this scheduled post now').click();
  await expect(page.locator('.toast')).toContainText('ready to publish now');
});

test('layout remains inside the viewport', async ({page}) => {
  await page.goto('/');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  await page.getByRole('button', {name: /Settings/}).first().click();
  await page.getByRole('button', {name: /^Settings/}).last().click();
  await expect(page.getByRole('heading', {name: 'Accounts & delivery'})).toBeVisible();
});
