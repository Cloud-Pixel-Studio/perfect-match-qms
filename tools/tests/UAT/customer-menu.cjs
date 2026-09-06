const ACTION_SELECTOR = [
  '[role="menuitem"]:not(:has([role="menuitem"], a, button))',
  'a:not(:has([role="menuitem"], a, button))',
  'button:not(:has([role="menuitem"], a, button))',
].join(', ');
const CUSTOMER_NAVBAR_SELECTOR = 'nav.o_main_navbar, .o_main_navbar';
const MORE_MENU_NAME = 'More Menu';

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

function exactLabel(label) {
  return new RegExp(`^\\s*${escapedText(label)}\\s*$`);
}

function customerNavbar(page) {
  return page.locator(CUSTOMER_NAVBAR_SELECTOR).first();
}

function directRoot(page, label) {
  return customerNavbar(page)
    .locator('span[data-section]:visible')
    .filter({ hasText: exactLabel(label) })
    .first();
}

function directNavigationItem(page, label) {
  return customerNavbar(page)
    .locator('a:visible, button:visible')
    .filter({ hasText: exactLabel(label) })
    .filter({ hasNotText: MORE_MENU_NAME })
    .first();
}

function moreMenuButton(page) {
  return customerNavbar(page).getByRole('button', { name: MORE_MENU_NAME, exact: true }).first();
}

function visibleOverflowRoot(page, label) {
  return page.locator([
    '.o_popover:visible .o_more_dropdown_section',
    '.o-popover:visible .o_more_dropdown_section',
    '[role="menu"]:visible .o_more_dropdown_section',
    '.dropdown-menu:visible .o_more_dropdown_section',
  ].join(', ')).filter({ hasText: exactLabel(label) }).first();
}

async function openMoreMenu(page) {
  const button = moreMenuButton(page);
  await button.waitFor({ state: 'visible' });
  if ((await button.getAttribute('aria-expanded')) !== 'true') await button.click();
  await page.waitForTimeout(250);
}

async function customerRootSection(page, label) {
  const direct = directRoot(page, label);
  if (await direct.isVisible().catch(() => false)) {
    return { label, direct: true, overflow: false, reachable: true };
  }

  const directItem = directNavigationItem(page, label);
  if (await directItem.isVisible().catch(() => false)) {
    return { label, direct: true, overflow: false, reachable: true };
  }

  const more = moreMenuButton(page);
  if (!(await more.isVisible().catch(() => false))) {
    return { label, direct: false, overflow: false, reachable: false };
  }
  await openMoreMenu(page);
  const overflow = visibleOverflowRoot(page, label);
  const overflowVisible = await overflow.isVisible().catch(() => false);
  return { label, direct: false, overflow: overflowVisible, reachable: overflowVisible };
}

async function customerRootSections(page) {
  const directLabels = await customerNavbar(page).locator('span[data-section]').evaluateAll((nodes) => [
    ...new Set(nodes.map((node) => node.textContent.trim().replace(/\s+/g, ' ')).filter(Boolean)),
  ]);
  const more = moreMenuButton(page);
  let overflowLabels = [];
  if (await more.isVisible().catch(() => false)) {
    await openMoreMenu(page);
    overflowLabels = await page.locator([
      '.o_popover:visible .o_more_dropdown_section',
      '.o-popover:visible .o_more_dropdown_section',
      '[role="menu"]:visible .o_more_dropdown_section',
      '.dropdown-menu:visible .o_more_dropdown_section',
    ].join(', ')).evaluateAll((nodes) => [
      ...new Set(nodes.map((node) => node.textContent.trim().replace(/\s+/g, ' ')).filter(Boolean)),
    ]);
    await page.keyboard.press('Escape');
    await page.waitForTimeout(150);
  }
  return [...new Set([...directLabels, ...overflowLabels])];
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
  const root = directRoot(page, label);
  if (await root.isVisible().catch(() => false)) {
    const button = root.locator('xpath=..');
    await button.hover();
    await page.waitForTimeout(250);
    if ((await button.getAttribute('aria-expanded')) !== 'true') await button.click();
    await page.waitForTimeout(250);
    return 'DIRECT';
  }

  await openMoreMenu(page);
  const overflow = visibleOverflowRoot(page, label);
  await overflow.waitFor({ state: 'visible' });
  await overflow.click();
  await page.waitForTimeout(250);
  return 'OVERFLOW';
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
  customerRootSection,
  customerRootSections,
  openCustomerMenuAction,
  openRootMenu,
};
