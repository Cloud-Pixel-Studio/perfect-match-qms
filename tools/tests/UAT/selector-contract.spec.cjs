const fs = require('node:fs');
const path = require('node:path');
const { test, expect } = require('@playwright/test');
const {
  customerMenuAction,
  customerRootSection,
  customerRootSections,
  exactVisibleOption,
  openRootMenu,
} = require('./customer-menu.cjs');

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

  test('resolves direct and overflow roots without accepting unrelated text', async ({ page }) => {
    await page.setContent(`
      <nav class="o_main_navbar">
        <a href="#dashboard">Dashboard</a>
        <button type="button" aria-expanded="false" onclick="this.setAttribute('aria-expanded', 'true')">
          <span data-section="configuration">Configuration</span>
        </button>
        <button type="button" aria-label="More Menu" style="display: none">More</button>
      </nav>
      <h1>Configuration</h1>
    `);

    const direct = await customerRootSection(page, 'Configuration');
    expect(direct).toEqual({ label: 'Configuration', direct: true, overflow: false, reachable: true });
    await openRootMenu(page, 'Configuration');
    await expect(page.locator('span[data-section="configuration"]').locator('xpath=..')).toHaveAttribute('aria-expanded', 'true');

    await page.setContent(`
      <nav class="o_main_navbar">
        <a href="#dashboard">Dashboard</a>
        <button type="button" aria-label="More Menu" aria-expanded="false"
                onclick="document.querySelector('.o_popover').style.display = 'block'; this.setAttribute('aria-expanded', 'true')">
          More
        </button>
        <span data-section="configuration" style="display: none">Configuration</span>
      </nav>
      <div class="o_popover" style="display: none">
        <div class="o_more_dropdown_section" onclick="this.setAttribute('data-open', 'true')">Configuration</div>
      </div>
      <h1>Configuration</h1>
      <p>Unrelated Configuration text</p>
    `);

    const roots = await customerRootSections(page);
    expect(roots.filter((root) => root === 'Configuration')).toHaveLength(1);
    expect(roots).not.toContain('Unrelated Configuration text');
    const overflow = await customerRootSection(page, 'Configuration');
    expect(overflow).toEqual({ label: 'Configuration', direct: false, overflow: true, reachable: true });
    await openRootMenu(page, 'Configuration');
    await expect(page.locator('.o_more_dropdown_section')).toHaveAttribute('data-open', 'true');

    await page.setContent('<nav class="o_main_navbar"><h2>Configuration</h2></nav>');
    expect(await customerRootSection(page, 'Configuration')).toEqual({
      label: 'Configuration', direct: false, overflow: false, reachable: false,
    });
  });
});
