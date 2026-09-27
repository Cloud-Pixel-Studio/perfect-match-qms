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

function directRootCandidates(page) {
  return customerNavbar(page).locator('a:visible, button:visible');
}

function directNavigationItem(page, label) {
  return directRootCandidates(page)
    .filter({ hasText: exactLabel(label) })
    .filter({ hasNotText: MORE_MENU_NAME })
    .first();
}

function moreMenuButton(page) {
  return customerNavbar(page)
    .locator(`button[title="${MORE_MENU_NAME}"], button[aria-label="${MORE_MENU_NAME}"]`)
    .first();
}

function visibleOverflowRoot(page, label) {
  return page.locator([
    '.o-dropdown--menu:visible .o_more_dropdown_section',
    '.o_popover:visible .o_more_dropdown_section',
    '.o-popover:visible .o_more_dropdown_section',
    '[role="menu"]:visible .o_more_dropdown_section',
    '.dropdown-menu:visible .o_more_dropdown_section',
  ].join(', ')).filter({ hasText: exactLabel(label) }).first();
}

async function openMoreMenu(page) {
  const button = moreMenuButton(page);
  await button.waitFor({ state: 'visible' });
  const hasExpansionState = (await button.getAttribute('aria-expanded')) !== null;
  const hasOverflowMarkup = await page.locator('.o_more_dropdown_section').count() > 0;
  if (!hasExpansionState && !hasOverflowMarkup) return false;
  await page.keyboard.press('Escape').catch(() => {});
  await page.waitForTimeout(100);
  await button.click({ timeout: 5_000 });
  await page.locator('.o_more_dropdown_section:visible').first().waitFor({ state: 'visible', timeout: 5_000 });
  return true;
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
  if (!(await openMoreMenu(page))) {
    return { label, direct: false, overflow: false, reachable: false };
  }
  const overflow = visibleOverflowRoot(page, label);
  const overflowVisible = await overflow.isVisible().catch(() => false);
  return { label, direct: false, overflow: overflowVisible, reachable: overflowVisible };
}

async function customerRootSections(page) {
  const directLabels = await customerNavbar(page).locator('span[data-section]:visible, a:visible, button:visible').evaluateAll((nodes) => {
    const root = nodes[0]?.closest('nav.o_main_navbar, .o_main_navbar');
    const visible = (node) => Boolean(node.offsetWidth || node.offsetHeight || node.getClientRects().length);
    const normalized = (node) => node.textContent.trim().replace(/\s+/g, ' ');
    return [...new Set(nodes
      .filter((node) => node.closest('nav.o_main_navbar, .o_main_navbar') === root)
      .filter(visible)
      .filter((node) => !node.matches('[aria-label="More Menu"], [aria-label*="Messages"], [aria-label*="Notifications"]'))
      .filter((node) => node.matches('span[data-section]') || !node.closest('[role="menu"], .dropdown-menu, .o_popover'))
      .filter((node) => !node.querySelector('a, button'))
      .map(normalized)
      .filter(Boolean)
      .filter((label) => label !== 'More Menu'))];
  });
  const more = moreMenuButton(page);
  let overflowLabels = [];
  if (await more.isVisible().catch(() => false)) {
    if (!(await openMoreMenu(page))) return directLabels;
    overflowLabels = await page.locator([
      '.o-dropdown--menu:visible .o_more_dropdown_section',
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

async function boundedHover(target, label) {
  try {
    await target.hover({ timeout: 5_000 });
  } catch (error) {
    const diagnostics = await target.evaluate((node) => ({
      tag: node.tagName.toLowerCase(),
      text: node.textContent.trim().replace(/\s+/g, ' ').slice(0, 120),
      visible: Boolean(node.offsetWidth || node.offsetHeight || node.getClientRects().length),
      ariaExpanded: node.getAttribute('aria-expanded'),
      viewport: { width: window.innerWidth, height: window.innerHeight },
      rect: (() => {
        const rect = node.getBoundingClientRect();
        return { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) };
      })(),
      computed: (() => {
        const style = getComputedStyle(node);
        return { display: style.display, visibility: style.visibility, pointerEvents: style.pointerEvents, zIndex: style.zIndex };
      })(),
      topAtCenter: (() => {
        const rect = node.getBoundingClientRect();
        const top = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
        return top ? { tag: top.tagName.toLowerCase(), text: top.textContent.trim().replace(/\s+/g, ' ').slice(0, 120) } : null;
      })(),
      overlays: [...document.querySelectorAll('[role="dialog"], .modal, .o_popover, .o-dropdown--menu, .dropdown-menu')]
        .filter((candidate) => {
          const style = getComputedStyle(candidate);
          return style.display !== 'none' && style.visibility !== 'hidden';
        })
        .slice(0, 8)
        .map((candidate) => ({ tag: candidate.tagName.toLowerCase(), text: candidate.textContent.trim().replace(/\s+/g, ' ').slice(0, 100) })),
    })).catch(() => ({ unavailable: true }));
    throw new Error(`Timed out hovering ${label}: ${JSON.stringify(diagnostics)}; ${error.message}`);
  }
}

async function interactionSnapshot(page, target) {
  return target.evaluate((node) => {
    const rect = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    const center = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
    const visibleOverlay = (candidate) => {
      const candidateStyle = getComputedStyle(candidate);
      return candidateStyle.display !== 'none'
        && candidateStyle.visibility !== 'hidden'
        && candidateStyle.opacity !== '0';
    };
    return {
      tag: node.tagName.toLowerCase(),
      text: node.textContent.trim().replace(/\s+/g, ' ').slice(0, 120),
      role: node.getAttribute('role'),
      dataSection: node.getAttribute('data-section'),
      xmlid: node.getAttribute('data-menu-xmlid'),
      ariaExpanded: node.getAttribute('aria-expanded'),
      visible: Boolean(node.offsetWidth || node.offsetHeight || node.getClientRects().length),
      rect: { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) },
      computed: {
        display: style.display,
        visibility: style.visibility,
        opacity: style.opacity,
        pointerEvents: style.pointerEvents,
        zIndex: style.zIndex,
      },
      topAtCenter: center ? {
        tag: center.tagName.toLowerCase(),
        text: center.textContent.trim().replace(/\s+/g, ' ').slice(0, 120),
      } : null,
      overlays: [...document.querySelectorAll('[role="dialog"], .modal, .o_popover, .o-dropdown--menu, .dropdown-menu')]
        .filter(visibleOverlay)
        .slice(0, 8)
        .map((candidate) => {
          const candidateRect = candidate.getBoundingClientRect();
          const candidateStyle = getComputedStyle(candidate);
          return {
            tag: candidate.tagName.toLowerCase(),
            text: candidate.textContent.trim().replace(/\s+/g, ' ').slice(0, 160),
            rect: { x: Math.round(candidateRect.x), y: Math.round(candidateRect.y), width: Math.round(candidateRect.width), height: Math.round(candidateRect.height) },
            zIndex: candidateStyle.zIndex,
          };
        }),
    };
  });
}

async function logInteraction(page, label, phase, target) {
  const snapshot = await interactionSnapshot(page, target).catch((error) => ({ error: error.name }));
  console.log(`M31_CONFIGURATION_INTERACTION=${JSON.stringify({ label, phase, viewport: page.viewportSize(), snapshot })}`);
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
    await logInteraction(page, label, 'locator-visible', button);
    console.log(`M31_CONFIGURATION_OPERATION=${JSON.stringify({ label, operation: 'hover', timeoutMs: 5000 })}`);
    await boundedHover(button, `root ${label}`);
    await logInteraction(page, label, 'after-hover', button);
    await page.waitForTimeout(250);
    const ariaBefore = await button.getAttribute('aria-expanded');
    console.log(`M31_CONFIGURATION_OPERATION=${JSON.stringify({ label, operation: 'aria-before-click', ariaExpanded: ariaBefore })}`);
    if (ariaBefore !== 'true') {
      console.log(`M31_CONFIGURATION_OPERATION=${JSON.stringify({ label, operation: 'playwright-click', timeoutMs: 5000 })}`);
      await button.click({ timeout: 5_000 });
    }
    await page.waitForTimeout(250);
    await logInteraction(page, label, 'after-click', button);
    console.log(`M31_CONFIGURATION_OPERATION=${JSON.stringify({ label, operation: 'dropdown-dom', menus: await page.locator('[role="menu"]:visible, .o-dropdown--menu:visible, .o_popover:visible, .o-popover:visible, .dropdown-menu:visible').evaluateAll((nodes) => nodes.slice(-4).map((node) => ({ tag: node.tagName.toLowerCase(), text: node.textContent.trim().replace(/\s+/g, ' ').slice(0, 240), role: node.getAttribute('role'), className: node.className }))).catch(() => []) })}`);
    return 'DIRECT';
  }

  const directItem = directNavigationItem(page, label);
  if (await directItem.isVisible().catch(() => false)) {
    const tagName = await directItem.evaluate((node) => node.tagName.toLowerCase());
    if (tagName === 'a') {
      await directItem.click({ timeout: 5_000 });
      await page.waitForTimeout(250);
      return 'DIRECT_ACTION';
    }
    await boundedHover(directItem, `direct ${label}`);
    await page.waitForTimeout(250);
    if ((await directItem.getAttribute('aria-expanded')) !== 'true') {
      await directItem.click({ timeout: 5_000 });
    }
    await page.waitForTimeout(250);
    return 'DIRECT_MENU';
  }

  const more = moreMenuButton(page);
  await more.waitFor({ state: 'visible', timeout: 5_000 });
  await openMoreMenu(page);
  const overflow = visibleOverflowRoot(page, label);
  await overflow.waitFor({ state: 'visible', timeout: 5_000 });
  await overflow.click({ timeout: 5_000 });
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
    await page.goto(new URL(entry.href, page.url()).toString(), { waitUntil: 'commit', timeout: 15_000 });
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
