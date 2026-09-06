const ACTION_SELECTOR = [
  '[role="menuitem"]:not(:has([role="menuitem"], a, button))',
  'a:not(:has([role="menuitem"], a, button))',
  'button:not(:has([role="menuitem"], a, button))',
].join(', ');

function escapedText(text) {
  return text.replace(/[.*+?^\${}()|[\]\\]/g, '\\$&');
}

function escapedAttribute(text) {
  return text.replace(/["\\]/g, '\\$&');
}

function exactVisibleOption(page, label) {
  const exactLabel = new RegExp(`^\\s*${escapedText(label)}\\s*$`);
  return page.locator('[role="option"]:visible').filter({ hasText: exactLabel }).first();
}

function visibleNavigationMenu(page) {
  return page.locator('[role="menu"]:visible, .dropdown-menu:visible').last();
}

async function customerMenuAction(page, label, xmlidFragment) {
  const exactLabel = new RegExp(`^\\s*${escapedText(label)}\\s*$`);
  let actions = visibleNavigationMenu(page).locator(ACTION_SELECTOR).filter({ hasText: exactLabel });
  if (xmlidFragment) {
    const xmlid = escapedAttribute(xmlidFragment);
    const scoped = visibleNavigationMenu(page)
      .locator('[data-menu-xmlid*="' + xmlid + '"]')
      .filter({ hasText: exactLabel });
    if (await scoped.count()) actions = scoped;
  }
  return actions.first();
}

async function openRootMenu(page, label) {
  const exactLabel = new RegExp(`^\\s*${escapedText(label)}\\s*$`);
  const root = page.locator('span[data-section]:visible').filter({ hasText: exactLabel }).first();
  await root.waitFor({ state: 'visible' });
  const button = root.locator('xpath=..');
  await button.hover();
  await page.waitForTimeout(250);
  if ((await button.getAttribute('aria-expanded')) !== 'true') await button.click();
  await page.waitForTimeout(250);
}

async function customerMenuEntries(page) {
  return visibleNavigationMenu(page).locator(ACTION_SELECTOR).evaluateAll((nodes) => nodes.map((node) => {
    const dataAttributes = {};
    for (const attribute of node.attributes) {
      if (attribute.name.startsWith('data-')) dataAttributes[attribute.name] = attribute.value;
    }
    return {
      tagName: node.tagName.toLowerCase(),
      role: node.getAttribute('role'),
      text: node.textContent.trim().replace(/\s+/g, ' '),
      href: node.getAttribute('href'),
      xmlid: node.getAttribute('data-menu-xmlid'),
      dataAttributes,
    };
  }).filter((entry) => entry.text));
}

async function openCustomerMenuAction(page, entry, waitForApp) {
  if (entry.href) {
    await page.goto(new URL(entry.href, page.url()).toString());
  } else {
    await openRootMenu(page, entry.root);
    await (await customerMenuAction(page, entry.text, entry.xmlid)).click();
  }
  if (waitForApp) await waitForApp(page);
  return page.url();
}

module.exports = {
  ACTION_SELECTOR,
  customerMenuAction,
  customerMenuEntries,
  exactVisibleOption,
  openCustomerMenuAction,
  openRootMenu,
};
