const { test, expect } = require('@playwright/test');
const { customerMenuAction } = require('./customer-menu.cjs');

test.describe('customer menu semantic selector contract', () => {
  test('accepts supported actionable menu markup and rejects unrelated text', async ({ page }) => {
    const cases = [
      '<a role="menuitem" href="/odoo/action-267">New Implementation</a>',
      '<button role="menuitem" type="button">New Implementation</button>',
      '<button type="button"><span>New Implementation</span></button>',
    ];

    for (const markup of cases) {
      await page.setContent(`<div role="menu">${markup}</div>`);
      const action = await customerMenuAction(page, 'New Implementation');
      await expect(action).toHaveCount(1);
      await expect(action).toBeVisible();
    }

    await page.setContent('<div role="menu"><div>New Implementation</div></div>');
    await expect(await customerMenuAction(page, 'New Implementation')).toHaveCount(0);
  });
});
