const fs = require('node:fs');
const path = require('node:path');
const { test, expect } = require('@playwright/test');
const { customerMenuAction, exactVisibleOption } = require('./customer-menu.cjs');

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

  test('selects an exact configured organization without the legacy fixture', async ({ page }) => {
    await page.setContent(`
      <div role="listbox">
        <div role="option" aria-selected="false" onclick="this.setAttribute('aria-selected', 'true')">Acme Runtime Contract Test, Inc.</div>
        <div role="option" aria-selected="false">Acme Runtime Contract Test, Inc. Extended</div>
      </div>
    `);

    const option = exactVisibleOption(page, 'Acme Runtime Contract Test, Inc.');
    await expect(option).toHaveCount(1);
    await option.click();
    await expect(option).toHaveAttribute('aria-selected', 'true');
    await expect(exactVisibleOption(page, 'M31 Fictional Customer')).toHaveCount(0);

    const source = fs.readFileSync(path.join(__dirname, 'customer-browser.spec.cjs'), 'utf8');
    expect(source).toContain("required('M31_ORGANIZATION_NAME')");
    expect(source).not.toContain('M31 Fictional Customer');
  });
});
