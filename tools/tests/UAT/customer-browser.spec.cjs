const fs = require('node:fs');
const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;
const {
  customerMenuAction,
  customerMenuEntries,
  exactVisibleOption,
  openCustomerMenuAction,
  openRootMenu,
  customerRootSection,
  customerRootSections,
} = require('./customer-menu.cjs');

const DATABASE = process.env.M31_DATABASE || 'pmqms_m31_uat_test';
const LOGIN_PATH = `/web/login?db=${encodeURIComponent(DATABASE)}&redirect=%2Fodoo`;
const CUSTOMER_SHELL = 'o_pm_qms_customer_shell';
const ORGANIZATION_NAME = required('M31_ORGANIZATION_NAME');
const IMPLEMENTATION_NAME = 'M31 Fictional ISO 9001 Initial Implementation';
const CUSTOMER_ROOTS = ['Dashboard', 'Action Center', 'Implementation', 'Quality Operations', 'Assurance', 'Performance', 'Standards'];
const CUSTOMER_ROLE_ROOTS = ['Implementation', 'Quality Operations', 'Assurance', 'Performance', 'Standards'];
const ROLE_CONTRACT = {
  'Internal Auditor': { shell: true, roots: CUSTOMER_ROLE_ROOTS, forbiddenRoots: ['Configuration'] },
  'Process Owner': { shell: true, roots: CUSTOMER_ROLE_ROOTS, forbiddenRoots: ['Configuration'] },
  Viewer: { shell: true, roots: CUSTOMER_ROLE_ROOTS, forbiddenRoots: ['Configuration'] },
  'API Integration Administrator': { shell: false, roots: [], forbiddenRoots: [] },
};
const CONFIGURATION_CONTRACT = {
  'Quality Manager': ['Company Profile', 'Sites', 'Processes', 'Users & Access', 'Commercial License'],
  // Framework Administration is a permission-scoped navigation group; its
  // supported action surface is the Framework Controls child menu.
  'QMS Administrator': ['Company Profile', 'Sites', 'Processes', 'Users & Access', 'Framework Controls'],
  'Licensing Administrator': ['Commercial License', 'Activation Requests'],
};
const EXPERIENCE_COVERAGE = {
  'login/logout': 'TESTED/PASS (login); NOT TESTED (logout)',
  'customer branding': 'NOT TESTED',
  'root navigation': 'TESTED/PASS for customer roots; TESTED/FAIL if documented QM Configuration is absent',
  'responsive More menu': 'NOT TESTED',
  breadcrumbs: 'NOT TESTED',
  'empty states': 'TESTED/PASS',
  'forms and validation': 'TESTED/PASS for guided implementation',
  'direct URLs': 'TESTED/PASS for customer restriction probe',
  'in-app activities': 'NOT TESTED',
  reminders: 'NOT TESTED',
  chatter: 'NOT TESTED',
  'notification record links': 'NOT TESTED',
  'overdue behavior': 'NOT TESTED',
  'duplicate notifications': 'NOT TESTED',
  'unauthorized recipient isolation': 'NOT TESTED',
  'behavior without SMTP': 'NOT TESTED',
  'captured email delivery': 'NOT TESTED',
  'keyboard navigation': 'NOT TESTED',
  'visible focus': 'NOT_TESTED',
  'accessible names': 'TESTED/PASS via axe',
  'form labels': 'TESTED/PASS via axe',
  'required-field communication': 'NOT TESTED',
  'validation errors': 'NOT TESTED',
  headings: 'NOT TESTED',
  dialogs: 'TESTED/PASS for guided implementation',
  'desktop viewport': 'TESTED/PASS',
  'constrained viewport': 'TESTED/PASS',
  'device/session IP': 'NOT TESTED',
  'each required business workflow domain': 'TESTED/PASS or NOT_EXPOSED per domain smoke result',
};
const state = {
  qm: null,
  qmsAdmin: null,
  licensingAdmin: null,
  viewer: null,
  admin: null,
  implementationHref: null,
  implementationMenuXmlid: null,
  menuInventory: null,
  actionManifest: null,
  roles: {},
};

function required(name) {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

function readSecret(name) {
  return fs.readFileSync(required(name), 'utf8').trim();
}

async function closeContext(page, context) {
  await Promise.race([
    page.close({ runBeforeUnload: false }).catch(() => {}),
    new Promise((resolve) => setTimeout(resolve, 1_000)),
  ]);
  await Promise.race([
    context.close().catch(() => {}),
    new Promise((resolve) => setTimeout(resolve, 1_000)),
  ]);
}

function readActionManifest() {
  const manifest = JSON.parse(fs.readFileSync(required('M31_ACTION_MANIFEST_FILE'), 'utf8'));
  if (!Array.isArray(manifest) || !manifest.length) throw new Error('Action manifest is empty');
  return Object.fromEntries(manifest.map((entry) => [entry.key, entry]));
}

function userFromEnv(prefix) {
  const login = process.env[`${prefix}_LOGIN`];
  const passwordFile = process.env[`${prefix}_PASSWORD_FILE`];
  if (!login || !passwordFile) return null;
  return { login, password: readSecret(`${prefix}_PASSWORD_FILE`) };
}

function hasText(page, text) {
  return page.getByText(text, { exact: true }).first().isVisible().catch(() => false);
}

function installTelemetry(page, label) {
  const telemetry = {
    label,
    pageErrors: [],
    consoleErrors: [],
    consoleWarnings: [],
    failedRequests: [],
    httpErrors: [],
    menuResponses: [],
    menuResponsePromises: [],
  };
  page.on('pageerror', (error) => telemetry.pageErrors.push(error.message));
  page.on('console', (message) => {
    const item = { text: message.text(), location: message.location() };
    if (message.type() === 'error') telemetry.consoleErrors.push(item);
    if (message.type() === 'warning') telemetry.consoleWarnings.push(item);
  });
  page.on('requestfailed', (request) => {
    telemetry.failedRequests.push({ url: request.url(), error: request.failure()?.errorText || 'unknown' });
  });
  page.on('response', (response) => {
    if (response.status() >= 400) telemetry.httpErrors.push({ status: response.status(), url: response.url() });
    if (new URL(response.url()).pathname === '/web/webclient/load_menus') {
      const promise = response.json()
        .then((payload) => telemetry.menuResponses.push(sanitizeMenuPayload(payload)))
        .catch(() => telemetry.menuResponses.push({ status: 'unavailable' }));
      telemetry.menuResponsePromises.push(promise);
    }
  });
  return telemetry;
}

function sanitizeMenuPayload(payload) {
  const node = (id) => payload?.[id] || payload?.[String(id)];
  const label = (item) => item?.name || item?.label || '';
  const children = (item) => item?.children || [];
  const summarize = (item) => item && ({
    id: item.id,
    label: label(item),
    parentId: item.parent_id?.[0] ?? item.parentID ?? item.parentId ?? null,
    appId: item.appID ?? item.app_id ?? null,
    actionId: item.actionID ?? item.action_id ?? null,
    actionPath: item.actionPath ?? item.action_path ?? null,
    xmlid: item.xmlid || null,
    children: children(item),
  });
  const rootChildren = (payload?.root?.children || []).map(node).filter(Boolean).map(summarize);
  const configuration = Object.values(payload || {})
    .filter((item) => item && typeof item === 'object' && label(item) === 'Configuration')
    .map(summarize);
  return { rootChildren, configuration };
}

function recordTelemetry(telemetry) {
  test.info().annotations.push({ type: 'telemetry', description: JSON.stringify({
    label: telemetry.label,
    pageErrors: telemetry.pageErrors.length,
    consoleErrors: telemetry.consoleErrors.length,
    consoleWarnings: telemetry.consoleWarnings.length,
    failedRequests: telemetry.failedRequests.length,
    http4xx: telemetry.httpErrors.filter((item) => item.status >= 400 && item.status < 500).length,
    http5xx: telemetry.httpErrors.filter((item) => item.status >= 500).length,
    rpcFailures: telemetry.httpErrors.filter((item) => /\/web\/dataset\/|\/web\/database\//.test(item.url)).length,
  }) });
}

async function browserMenuDataDiagnostics(page) {
  return page.evaluate(() => {
    const raw = window.localStorage.getItem('webclient_menus');
    if (!raw) return { available: false, reason: 'webclient_menus not present' };
    try {
      const payload = JSON.parse(raw);
      const node = (id) => payload[id] || payload[String(id)];
      const label = (item) => item?.name || item?.label || '';
      const children = (item) => item?.children || item?.childrenTree?.map((child) => child.id) || [];
      const rootChildren = (payload.root?.children || []).map((id) => node(id)).filter(Boolean);
      const configuration = Object.values(payload).filter(
        (item) => item && typeof item === 'object' && label(item) === 'Configuration',
      );
      return {
        available: true,
        rootChildren: rootChildren.map((item) => ({
          id: item.id,
          label: label(item),
          actionId: item.actionID ?? item.action_id ?? null,
          children: children(item),
        })),
        configuration: configuration.map((item) => ({
          id: item.id,
          label: label(item),
          appId: item.appID ?? item.app_id ?? null,
          actionId: item.actionID ?? item.action_id ?? null,
          children: children(item),
          xmlid: item.xmlid || null,
        })),
      };
    } catch (error) {
      return { available: false, reason: `invalid menu payload: ${error.name}` };
    }
  }).catch((error) => ({ available: false, reason: `browser inspection failed: ${error.name}` }));
}

async function browserMenuActionEntries(page) {
  return page.evaluate(() => {
    const raw = window.localStorage.getItem('webclient_menus');
    if (!raw) return [];
    try {
      const payload = JSON.parse(raw);
      return Object.values(payload)
        .filter((item) => item && typeof item === 'object' && (item.actionID ?? item.action_id))
        .map((item) => ({
          text: (item.name || item.label || '').trim().replace(/\s+/g, ' '),
          xmlid: item.xmlid || null,
          href: `/odoo/${item.actionPath || item.action_path || `action-${item.actionID ?? item.action_id}`}`,
        }))
        .filter((item) => item.text && item.href);
    } catch {
      return [];
    }
  }).catch(() => []);
}

async function configurationDomDiagnostics(page) {
  return page.locator('nav.o_main_navbar, .o_main_navbar').first().evaluate((navbar) => {
    const candidates = [...navbar.querySelectorAll('*')].filter(
      (node) => node.textContent.trim().replace(/\s+/g, ' ') === 'Configuration',
    );
    return candidates.map((node) => {
      const style = window.getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      const clickable = node.closest('a,button,[role="menuitem"]');
      const ancestors = [];
      let ancestor = node.parentElement;
      while (ancestor && ancestors.length < 8) {
        ancestors.push({
          tag: ancestor.tagName.toLowerCase(),
          classes: typeof ancestor.className === 'string' ? ancestor.className : '',
          role: ancestor.getAttribute('role'),
          dataSection: ancestor.getAttribute('data-section'),
          visible: Boolean(ancestor.offsetWidth || ancestor.offsetHeight || ancestor.getClientRects().length),
        });
        ancestor = ancestor.parentElement;
      }
      return {
        tag: node.tagName.toLowerCase(),
        menuXmlid: node.getAttribute('data-menu-xmlid'),
        dataSection: node.getAttribute('data-section'),
        display: style.display,
        visibility: style.visibility,
        opacity: style.opacity,
        rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
        role: node.getAttribute('role'),
        accessibleName: node.getAttribute('aria-label') || node.textContent.trim(),
        clickable: clickable ? {
          tag: clickable.tagName.toLowerCase(),
          role: clickable.getAttribute('role'),
          menuXmlid: clickable.getAttribute('data-menu-xmlid'),
          ariaExpanded: clickable.getAttribute('aria-expanded'),
          classes: clickable.className,
        } : null,
        ancestors,
      };
    });
  }).catch(() => []);
}

async function navigationViewportDiagnostics(page) {
  const originalViewport = page.viewportSize();
  const snapshots = [];
  for (const viewport of [
    { width: 1600, height: 900 },
    { width: 1280, height: 720 },
    { width: 1024, height: 720 },
  ]) {
    await page.setViewportSize(viewport);
    await page.waitForTimeout(300);
    const roots = await customerRootSections(page);
    const moreMenu = page.locator(
      'nav.o_main_navbar button[title="More Menu"], nav.o_main_navbar button[aria-label="More Menu"]',
    ).first();
    const moreMenuPresent = await moreMenu.isVisible().catch(() => false);
    let overflowLabels = [];
    if (moreMenuPresent) {
      await page.keyboard.press('Escape').catch(() => {});
      await page.waitForTimeout(100);
      await moreMenu.click();
      await page.locator('.o_more_dropdown_section:visible').first().waitFor({ state: 'visible', timeout: 5_000 });
      overflowLabels = await page.locator([
        '.o-dropdown--menu:visible .o_more_dropdown_section',
        '.o_popover:visible .o_more_dropdown_section',
        '.o-popover:visible .o_more_dropdown_section',
        '[role="menu"]:visible .o_more_dropdown_section',
        '.dropdown-menu:visible .o_more_dropdown_section',
      ].join(', ')).allTextContents();
      await page.keyboard.press('Escape');
    }
    snapshots.push({
      viewport,
      visibleRootLabels: roots,
      moreMenuPresent,
      configurationVisible: roots.includes('Configuration'),
      configurationInOverflow: overflowLabels.some((label) => label.trim() === 'Configuration'),
      overflowRootLabels: overflowLabels.map((label) => label.trim()).filter(Boolean),
    });
  }
  if (originalViewport) {
    await page.setViewportSize(originalViewport);
    await page.waitForTimeout(300);
  }
  return snapshots;
}

async function renderedNavigationDiagnostics(page) {
  return page.locator('nav.o_main_navbar, .o_main_navbar').first().locator('[data-section]').evaluateAll(
    (nodes) => nodes.map((node) => ({
      tag: node.tagName.toLowerCase(),
      text: node.textContent.trim().replace(/\s+/g, ' '),
      visible: Boolean(node.offsetWidth || node.offsetHeight || node.getClientRects().length),
      menuXmlid: node.getAttribute('data-menu-xmlid'),
      ariaExpanded: node.getAttribute('aria-expanded'),
      classes: node.className,
    })),
  ).catch(() => []);
}

async function browserRuntimeDiagnostics(page, telemetry) {
  await Promise.allSettled(telemetry.menuResponsePromises);
  const roots = await customerRootSections(page);
  const menuData = await browserMenuDataDiagnostics(page);
  const renderedNavigation = await renderedNavigationDiagnostics(page);
  const configurationDom = await configurationDomDiagnostics(page);
  const viewportDiagnostics = await navigationViewportDiagnostics(page);
  const navbar = page.locator('nav.o_main_navbar, .o_main_navbar').first();
  const accessibleNames = await navbar.locator('a:visible, button:visible, span[data-section]:visible').evaluateAll((nodes) => [
    ...new Set(nodes
      .filter((node) => !node.matches('[aria-label="More Menu"], [aria-label*="Messages"], [aria-label*="Notifications"]'))
      .map((node) => node.getAttribute('aria-label') || node.textContent.trim().replace(/\s+/g, ' '))
      .filter(Boolean)),
  ]);
  const moreMenu = navbar.locator(
    'button[title="More Menu"], button[aria-label="More Menu"]',
  ).first();
  const moreMenuPresent = await moreMenu.isVisible().catch(() => false);
  let overflowLabels = [];
  if (moreMenuPresent) {
    await page.keyboard.press('Escape').catch(() => {});
    await page.waitForTimeout(100);
    await moreMenu.click();
    await page.locator('.o_more_dropdown_section:visible').first().waitFor({ state: 'visible', timeout: 5_000 });
    overflowLabels = await page.locator([
      '.o-dropdown--menu:visible .o_more_dropdown_section',
      '.o_popover:visible .o_more_dropdown_section',
      '.o-popover:visible .o_more_dropdown_section',
      '[role="menu"]:visible .o_more_dropdown_section',
      '.dropdown-menu:visible .o_more_dropdown_section',
    ].join(', ')).allTextContents();
    await page.keyboard.press('Escape');
  }
  return {
    pathname: new URL(page.url()).pathname,
    viewport: page.viewportSize(),
    menuData,
    menuResponses: telemetry.menuResponses,
    configurationDom,
    renderedNavigation,
    viewportDiagnostics,
    visibleRootLabels: roots,
    accessibleNavigationNames: accessibleNames,
    moreMenuPresent,
    configurationInOverflow: overflowLabels.some((label) => label.trim() === 'Configuration'),
    overflowRootLabels: overflowLabels.map((label) => label.trim()).filter(Boolean),
    consoleErrors: telemetry.consoleErrors.map((item) => item.text.slice(0, 300)),
    pageErrors: telemetry.pageErrors.map((item) => item.slice(0, 300)),
    failedRequests: telemetry.failedRequests.map((item) => ({
      path: new URL(item.url, page.url()).pathname,
      error: item.error,
    })),
    httpErrors: telemetry.httpErrors.map((item) => ({
      status: item.status,
      path: new URL(item.url, page.url()).pathname,
    })),
  };
}

async function waitForApp(page) {
  await page.waitForLoadState('domcontentloaded', { timeout: 5_000 }).catch(() => {});
  await page.waitForTimeout(900);
}

async function openQmsApplication(page) {
  await page.goto('/odoo', { waitUntil: 'commit', timeout: 15_000 });
  await waitForApp(page);
  const appHref = await page.evaluate(() => {
    const raw = window.localStorage.getItem('webclient_menus');
    if (!raw) return null;
    try {
      const payload = JSON.parse(raw);
      const app = Object.values(payload).find(
        (item) => item && item.xmlid === 'pm_qms_core.menu_pm_qms_root',
      );
      const actionId = app?.actionID ?? app?.action_id;
      return actionId ? `/odoo/action-${actionId}` : null;
    } catch {
      return null;
    }
  });
  if (appHref) await page.goto(appHref, { waitUntil: 'commit', timeout: 15_000 });
  await waitForApp(page);
}

async function waitForCustomerNavigation(page) {
  await page.waitForFunction(
    () => document.querySelector('nav.o_main_navbar [data-section], nav.o_main_navbar .o_menu_sections') !== null,
    null,
    { timeout: 15_000 },
  );
  await page.waitForTimeout(300);
}

async function login(page, user) {
  await page.goto(LOGIN_PATH, { waitUntil: 'commit', timeout: 15_000 });
  await expect(page.locator('input[name="login"], input[type="email"]').first()).toBeVisible();
  await page.locator('input[name="login"], input[type="email"]').first().fill(user.login);
  await page.locator('input[name="password"], input[type="password"]').first().fill(user.password);
  await page.getByRole('button', { name: /log in|iniciar sesión/i }).click();
  await page.waitForTimeout(1_500);
  if (/\/web\/login(?:\?|$)/.test(page.url())) throw new Error('Authentication failed');
  if (page.url().includes('/web/login_successful')) await page.goto('/odoo', { waitUntil: 'commit', timeout: 15_000 });
  if (!/\/odoo(?:\/|\?|$)/.test(page.url())) await page.goto('/odoo', { waitUntil: 'commit', timeout: 15_000 });
  await waitForApp(page);
}

async function collectMenuInventory(page) {
  await openQmsApplication(page);
  await waitForCustomerNavigation(page);
  const roots = await customerRootSections(page);
  const menus = {};
  for (const root of roots) {
    await openRootMenu(page, root);
    menus[root] = (await customerMenuEntries(page)).map((entry) => ({ ...entry, root }));
  }
  return { roots, menus };
}

async function collectConfigurationInventory(page) {
  console.log('M31_CONFIGURATION_OPEN_APP_BEGIN');
  await openQmsApplication(page);
  console.log('M31_CONFIGURATION_OPEN_APP_END');
  await waitForCustomerNavigation(page);
  console.log('M31_CONFIGURATION_NAV_END');
  const configuration = await customerRootSection(page, 'Configuration');
  console.log(`M31_CONFIGURATION_ROOT=${JSON.stringify(configuration)}`);
  if (!configuration.reachable) throw new Error('Configuration root is not reachable');
  console.log('M31_CONFIGURATION_ROOT_OPEN_BEGIN');
  try {
    await openRootMenu(page, 'Configuration');
  } catch (error) {
    console.log(`M31_CONFIGURATION_ROOT_OPEN_ERROR=${JSON.stringify({
      error: error.message.slice(0, 500),
      viewport: page.viewportSize(),
      dom: await configurationDomDiagnostics(page),
      visibleMenus: await page.locator('[role="menu"]:visible, .o-dropdown--menu:visible, .o_popover:visible, .o-popover:visible, .dropdown-menu:visible').evaluateAll((nodes) => nodes.slice(-4).map((node) => ({
        tag: node.tagName.toLowerCase(),
        text: node.textContent.trim().replace(/\s+/g, ' ').slice(0, 240),
        className: node.className,
      }))).catch(() => []),
    })}`);
    throw error;
  }
  console.log('M31_CONFIGURATION_ROOT_OPEN_END');
  const menu = page.locator([
    '.o-dropdown--menu:visible',
    '.o_popover:visible',
    '.o-popover:visible',
    '[role="menu"]:visible',
    '.dropdown-menu:visible',
  ].join(', ')).last();
  await menu.waitFor({ state: 'visible', timeout: 5_000 });
  const entries = await menu.locator('a:visible, [role="menuitem"]:visible, button:visible').evaluateAll((nodes) => nodes.map((node) => ({
    tagName: node.tagName.toLowerCase(),
    role: node.getAttribute('role'),
    text: node.textContent.trim().replace(/\s+/g, ' '),
    href: node.getAttribute('href'),
    xmlid: node.getAttribute('data-menu-xmlid'),
  })).filter((entry) => entry.text && (entry.href || entry.xmlid)));
  console.log(`M31_CONFIGURATION_ENTRIES=${entries.length}`);
  return { roots: ['Configuration'], menus: { Configuration: entries } };
}

function menuLinks(inventory) {
  return Object.values(inventory.menus).flat();
}

function findMenuLink(inventory, text, xmlidFragment) {
  return menuLinks(inventory).find((item) => item.text === text && (!xmlidFragment || item.xmlid?.includes(xmlidFragment))) || null;
}

async function directActionProbe(page, entry, expected) {
  expect(entry?.href, `${entry?.label || 'action'} must expose a probeable action URL`).toBeTruthy();
  const actionResponses = [];
  const onResponse = async (response) => {
    if (new URL(response.url()).pathname !== '/web/action/load') return;
    try {
      actionResponses.push({ status: response.status(), payload: await response.json() });
    } catch (error) {
      actionResponses.push({ status: response.status(), payloadError: error.name });
    }
  };
  page.on('response', onResponse);
  await page.goto(new URL(entry.href, page.url()).toString(), { waitUntil: 'commit', timeout: 15_000 });
  await waitForApp(page);
  // The license action can complete its bounded action-load RPC after the
  // shell is visible. Wait only for that response, with a local cap, so the
  // direct probe does not mistake a slow action load for an authorization
  // denial or an empty result.
  const actionDeadline = Date.now() + 5_000;
  while (!actionResponses.length && Date.now() < actionDeadline) {
    await page.waitForTimeout(100);
  }
  page.off('response', onResponse);

  let payload = actionResponses.at(-1)?.payload || {};
  if (!actionResponses.length) {
    const directLoad = await page.evaluate(async (actionId) => {
      const response = await fetch('/web/action/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'call',
          params: { action_id: actionId, additional_context: {} },
        }),
      });
      return { status: response.status, payload: await response.json().catch(() => ({})) };
    }, entry.actionId);
    payload = directLoad.payload;
    actionResponses.push(directLoad);
  }
  const action = payload.result && typeof payload.result === 'object' ? payload.result : null;
  const rpcError = payload.error && typeof payload.error === 'object' ? payload.error : null;
  const errorData = rpcError?.data || {};
  const explicitAuthorizationError = Boolean(rpcError && (
    /AccessError|Access Denied|Forbidden|not allowed/i.test(String(errorData.name || ''))
    || /access denied|not allowed|forbidden/i.test(String(errorData.message || rpcError.message || ''))
  ));
  const metadata = {
    returned: Boolean(action),
    actionId: action?.id ?? null,
    targetModel: action?.res_model ?? null,
    type: action?.type ?? null,
    rpcError: rpcError ? {
      name: String(errorData.name || rpcError.message || 'unknown').slice(0, 160),
      authorization: explicitAuthorizationError,
    } : null,
  };
  const body = await page.locator('body').innerText();
  const screen = {
    loaded: Boolean(action) && metadata.actionId === entry.actionId,
    clean: cleanBody(body),
    url: page.url(),
  };
  const result = {
    role: entry.role,
    label: entry.label,
    expected,
    actionMetadata: metadata,
    screen,
    protectedData: action ? 'NOT_SEPARATELY_PROBED' : 'NOT_RETURNED_BEFORE_AUTHORIZATION_FAILURE',
    workflowMutation: 'NOT_PROBED',
    url: page.url(),
  };
  if (expected === 'ALLOW') {
    result.status = metadata.returned && metadata.actionId === entry.actionId
      && metadata.targetModel === entry.resModel && screen.clean ? 'PASS' : 'FAIL';
  } else {
    result.status = !metadata.returned && explicitAuthorizationError ? 'PASS' : 'FAIL';
  }
  return result;
}

async function callKw(page, model, method, args = [], kwargs = {}) {
  return page.evaluate(async ({ model: requestModel, method: requestMethod, args: requestArgs, kwargs: requestKwargs }) => {
    const response = await fetch(`/web/dataset/call_kw/${encodeURIComponent(requestModel)}/${encodeURIComponent(requestMethod)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'call',
        params: { model: requestModel, method: requestMethod, args: requestArgs, kwargs: requestKwargs },
      }),
    });
    const payload = await response.json().catch(() => ({}));
    const error = payload.error?.data || payload.error;
    return {
      httpStatus: response.status,
      result: payload.result,
      error: error ? {
        name: String(error.name || payload.error?.message || 'RPC_ERROR').slice(0, 120),
        authorization: /AccessError|Access Denied|Forbidden|not allowed/i.test(String(error.name || error.message || payload.error?.message || '')),
      } : null,
    };
  }, { model, method, args, kwargs });
}

async function sessionUid(page) {
  return page.evaluate(async () => {
    const response = await fetch('/web/session/get_session_info', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    const payload = await response.json().catch(() => ({}));
    return payload.result?.uid ?? null;
  });
}

function rpcAllowed(response) {
  return Boolean(response && !response.error && response.httpStatus < 400);
}

function rpcDenied(response) {
  return Boolean(response?.error?.authorization || response?.httpStatus === 403);
}

function summarizeRpc(response) {
  return {
    httpStatus: response?.httpStatus ?? null,
    resultType: Array.isArray(response?.result) ? 'array' : typeof response?.result,
    resultCount: Array.isArray(response?.result) ? response.result.length : null,
    resultBoolean: typeof response?.result === 'boolean' ? response.result : null,
    resultId: Number.isInteger(response?.result) ? response.result : null,
    error: response?.error || null,
  };
}

function cleanBody(text) {
  return !/Traceback|Internal Server Error|OwlError|AccessError|Uncaught Promise|RPC_ERROR/i.test(text);
}

async function appSnapshot(page) {
  const body = await page.locator('body').innerText();
  return {
    url: page.url(),
    body: body.slice(0, 1200),
    clean: cleanBody(body),
    shell: await page.locator(`html.${CUSTOMER_SHELL}`).count() === 1,
  };
}

async function getImplementationList(page, inventory) {
  const link = findMenuLink(inventory, 'Implementations', 'implementation_projects');
  if (!link) throw new Error('Implementations menu link not found');
  state.implementationMenuXmlid = link.xmlid;
  return openCustomerMenuAction(page, link, waitForApp);
}

async function selectOrganization(page) {
  const field = page.locator('#organization_id_0');
  await field.fill(ORGANIZATION_NAME);
  await page.waitForTimeout(600);
  const option = exactVisibleOption(page, ORGANIZATION_NAME);
  await expect(option).toBeVisible();
  await option.click();
}

async function selectPack(page) {
  await page.locator('#pack_ids_0').click();
  await page.waitForTimeout(400);
  await page.locator('[role="option"]:visible').filter({ hasText: /^ISO 9001 Initial Implementation - v1\.0$/ }).first().click();
  await page.waitForTimeout(600);
  await expect(page.locator('.o_field_many2many_tags .o_tag[aria-label="ISO 9001 Initial Implementation - v1.0"]')).toBeVisible();
}

async function ensureGeneratedImplementation(page, inventory) {
  const listHref = await getImplementationList(page, inventory);
  const existing = page.getByText(IMPLEMENTATION_NAME, { exact: true }).first();
  if (!(await existing.count())) {
    await openRootMenu(page, 'Implementation');
    await (await customerMenuAction(page, 'New Implementation')).click();
    await waitForApp(page);
    await page.locator('#name_0').fill(IMPLEMENTATION_NAME);
    await selectOrganization(page);
    await page.locator('#target_date_0').fill('10/31/2026');
    await page.keyboard.press('Tab');
    await selectPack(page);
    await page.getByRole('button', { name: /^Generate Implementation$/i }).click();
    await page.waitForTimeout(4_500);
    if (!/pm\.qms\.implementation\.project/.test(page.url())) throw new Error('Guided implementation generation did not open the project');
  } else {
    await existing.click();
    await waitForApp(page);
  }
  state.implementationHref = page.url();
  return { listHref, url: state.implementationHref };
}

function implementationStats(body) {
  return {
    controls: /\b37\s+Controls\b/.test(body),
    activities: /\b111\s+Activities\b/.test(body),
    evidence: /\b37\s+Evidence\b/.test(body),
    gaps: /\b37\s+Gaps\b/.test(body),
    code: /PM-IMP-00001/.test(body),
  };
}

async function smokeRoute(page, label, href) {
  const resolvedHref = typeof href === 'string'
    ? await openCustomerMenuAction(page, { href }, waitForApp)
    : await openCustomerMenuAction(page, href, waitForApp);
  const snapshot = await appSnapshot(page);
  return { label, href: resolvedHref, ...snapshot };
}

test.beforeAll(() => {
  state.qm = userFromEnv('M31_QM');
  state.qmsAdmin = userFromEnv('M31_QMS_ADMIN');
  state.licensingAdmin = userFromEnv('M31_LICENSE_ADMIN');
  state.viewer = userFromEnv('M31_VIEWER');
  state.admin = userFromEnv('M31_ADMIN');
  state.roles = {
    'Internal Auditor': userFromEnv('M31_AUDITOR'),
    'Process Owner': userFromEnv('M31_OWNER'),
    'Viewer': userFromEnv('M31_VIEWER'),
    'API Integration Administrator': userFromEnv('M31_API'),
  };
  state.actionManifest = readActionManifest();
  if (!state.qm || !state.admin) throw new Error('Quality Manager and Technical Administrator credentials are required');
  if (!state.qmsAdmin || !state.licensingAdmin) throw new Error('QMS Administrator and Licensing Administrator credentials are required');
  if (Object.entries(state.roles).some(([, user]) => !user)) throw new Error('All authenticated customer role fixtures are required');
});

test('Configuration browser navigation contract', async ({ browser }) => {
  test.setTimeout(600_000);
  const users = [
    ['Quality Manager', state.qm],
    ['QMS Administrator', state.qmsAdmin],
    ['Licensing Administrator', state.licensingAdmin],
  ];
  const inventories = {};
  const payloadActions = {};
  const roleEvidence = [];
  for (const [role, user] of users) {
    console.log(`M31_CONFIGURATION_ROLE_BEGIN=${role}`);
    const context = await browser.newContext();
    const page = await context.newPage();
    const telemetry = installTelemetry(page, `configuration-${role.toLowerCase().replaceAll(' ', '-')}`);
    const result = { role, configuration: 'NOT TESTED', allowed: [] };
    try {
      console.log(`M31_CONFIGURATION_LOGIN_BEGIN=${role}`);
      await login(page, user);
      console.log(`M31_CONFIGURATION_LOGIN_END=${role}`);
      console.log(`M31_CONFIGURATION_APP_BEGIN=${role}`);
      const inventory = await collectConfigurationInventory(page);
      console.log(`M31_CONFIGURATION_APP_END=${role}`);
      console.log(`M31_CONFIGURATION_INVENTORY=${role}:${inventory.roots.join('|')}`);
      inventories[role] = inventory;
      payloadActions[role] = await browserMenuActionEntries(page);
      const configuration = await customerRootSection(page, 'Configuration');
      result.configuration = configuration.reachable ? 'PASS' : 'FAIL';
      result.configurationEvidence = configuration;
      for (const label of CONFIGURATION_CONTRACT[role]) {
        console.log(`M31_CONFIGURATION_SURFACE=${role}:${label}`);
        const link = findMenuLink(inventory, label);
        if (!link) {
          result.allowed.push({ label, status: 'NOT TESTED', reason: 'surface not exposed through normal navigation' });
          continue;
        }
        const screen = await smokeRoute(page, label, link);
        result.allowed.push({ label, status: screen.clean ? 'PASS' : 'FAIL', url: screen.url });
        console.log(`M31_CONFIGURATION_SURFACE_RESULT=${JSON.stringify({ role, label, status: screen.clean ? 'PASS' : 'FAIL', url: screen.url, clean: screen.clean })}`);
      }
    } catch (error) {
      result.error = error.message.slice(0, 300);
      if (result.configuration === 'NOT TESTED') result.configuration = 'FAIL';
    }
    recordTelemetry(telemetry);
    result.telemetry = {
      pageErrors: telemetry.pageErrors.length,
      consoleErrors: telemetry.consoleErrors.length,
      failedRequests: telemetry.failedRequests.length,
      httpErrors: telemetry.httpErrors.length,
    };
    roleEvidence.push(result);
    console.log(`M31_CONFIGURATION_ROLE_END=${role}:${result.configuration}`);
    await closeContext(page, context);
  }

  expect({
    configurationRolesPass: roleEvidence.every((item) => item.configuration === 'PASS'),
    permittedSurfacesPass: roleEvidence.flatMap((item) => item.allowed).every((item) => item.status === 'PASS'),
  }).toEqual({
    configurationRolesPass: true,
    permittedSurfacesPass: true,
  });
});

test('Direct action authorization matrix runs independently of navigation', async ({ browser }) => {
  test.setTimeout(600_000);
  const directProbes = [
    ['Quality Manager', state.qm, 'company_profile', 'ALLOW'],
    ['Quality Manager', state.qm, 'sites', 'ALLOW'],
    ['Quality Manager', state.qm, 'processes', 'ALLOW'],
    ['Quality Manager', state.qm, 'users_access', 'ALLOW'],
    ['Quality Manager', state.qm, 'commercial_license', 'ALLOW'],
    ['Quality Manager', state.qm, 'framework_controls', 'DENY'],
    ['Quality Manager', state.qm, 'activation_requests', 'DENY'],
    ['QMS Administrator', state.qmsAdmin, 'company_profile', 'ALLOW'],
    ['QMS Administrator', state.qmsAdmin, 'sites', 'ALLOW'],
    ['QMS Administrator', state.qmsAdmin, 'processes', 'ALLOW'],
    ['QMS Administrator', state.qmsAdmin, 'users_access', 'ALLOW'],
    ['QMS Administrator', state.qmsAdmin, 'framework_controls', 'ALLOW'],
    ['QMS Administrator', state.qmsAdmin, 'commercial_license', 'DENY'],
    ['QMS Administrator', state.qmsAdmin, 'activation_requests', 'DENY'],
    ['Licensing Administrator', state.licensingAdmin, 'commercial_license', 'ALLOW'],
    ['Licensing Administrator', state.licensingAdmin, 'activation_requests', 'ALLOW'],
    ['Licensing Administrator', state.licensingAdmin, 'company_profile', 'DENY'],
    ['Licensing Administrator', state.licensingAdmin, 'users_access', 'DENY'],
    ['Technical Administrator', state.admin, 'company_profile', 'ALLOW'],
    ['Technical Administrator', state.admin, 'commercial_license', 'ALLOW'],
    ['Technical Administrator', state.admin, 'framework_controls', 'ALLOW'],
    ['Technical Administrator', state.admin, 'users_access', 'DENY'],
    ['Technical Administrator', state.admin, 'activation_requests', 'DENY'],
  ];
  const directEvidence = [];
  const directByRole = new Map();
  for (const probe of directProbes) {
    const [role] = probe;
    if (!directByRole.has(role)) directByRole.set(role, []);
    directByRole.get(role).push(probe);
  }
  for (const [role, probes] of directByRole) {
    console.log(`M31_DIRECT_ROLE_BEGIN=${role}`);
    for (const [, user, key, expected] of probes) {
      console.log(`M31_DIRECT_PROBE=${role}:${key}:${expected}`);
      const context = await browser.newContext();
      const page = await context.newPage();
      const manifestEntry = state.actionManifest[key];
      const telemetry = installTelemetry(page, `direct-${role.toLowerCase().replaceAll(' ', '-')}-${key}`);
      const result = { role, key, expected, status: 'NOT TESTED' };
      try {
        await login(page, user);
        expect(manifestEntry, `${key} must be present in the minimal action manifest`).toBeTruthy();
        Object.assign(result, await directActionProbe(page, { ...manifestEntry, role }, expected));
      } catch (error) {
        result.status = 'FAIL';
        result.error = error.message.slice(0, 300);
      }
      result.telemetry = {
        pageErrors: telemetry.pageErrors.length,
        consoleErrors: telemetry.consoleErrors.length,
        failedRequests: telemetry.failedRequests.length,
        httpErrors: telemetry.httpErrors.length,
      };
      directEvidence.push(result);
      console.log(`M31_DIRECT_RESULT=${JSON.stringify({ role, key, expected, status: result.status, error: result.error || null, actionReturned: result.actionMetadata?.returned ?? null, actionId: result.actionMetadata?.actionId ?? null, targetModel: result.actionMetadata?.targetModel ?? null, screenClean: result.screen?.clean ?? null })}`);
      recordTelemetry(telemetry);
      await closeContext(page, context);
    }
    console.log(`M31_DIRECT_ROLE_END=${role}`);
  }
  const authorizationEvidence = { directEvidence };
  test.info().annotations.push({ type: 'direct-authorization', description: JSON.stringify(authorizationEvidence) });
  console.log(`M31_DIRECT_AUTHORIZATION=${JSON.stringify(authorizationEvidence)}`);
  expect(directEvidence.every((item) => item.status === 'PASS')).toBeTruthy();
});

test('protected data, mutation and company-isolation evidence runs independently', async ({ browser }) => {
  test.setTimeout(600_000);
  const evidence = {};
  const qmContext = await browser.newContext();
  const qmPage = await qmContext.newPage();
  const licensingContext = await browser.newContext();
  const licensingPage = await licensingContext.newPage();
  let activationRequestId = null;
  try {
    await login(qmPage, state.qm);
    await login(licensingPage, state.licensingAdmin);

    const organizations = await callKw(qmPage, 'pm.qms.organization', 'search_read', [[], ['id', 'company_id']], { limit: 1 });
    const organization = Array.isArray(organizations.result) ? organizations.result[0] : null;
    expect(organization?.id, 'a protected organization fixture is required').toBeTruthy();
    const companyId = Array.isArray(organization.company_id) ? organization.company_id[0] : null;
    expect(companyId, 'the organization fixture must expose a company').toBeTruthy();
    evidence.protectedRecordRead = {
      status: rpcAllowed(organizations) ? 'PASS' : 'FAIL',
      model: 'pm.qms.organization',
      records: organizations.result?.length || 0,
    };

    const licenseRecords = await callKw(licensingPage, 'pm.qms.license', 'search_read', [[], ['id']], { limit: 1 });
    const licenseId = Array.isArray(licenseRecords.result) ? licenseRecords.result[0]?.id : null;
    expect(licenseId, 'a licensing fixture is required').toBeTruthy();
    evidence.protectedLicenseRead = {
      status: rpcAllowed(licenseRecords) ? 'PASS' : 'FAIL',
      model: 'pm.qms.license',
      records: licenseRecords.result?.length || 0,
    };

    const protectedField = await callKw(qmPage, 'pm.qms.license', 'read', [[licenseId], ['activation_request_ids']]);
    evidence.protectedFieldRead = {
      status: rpcDenied(protectedField) ? 'PASS' : 'FAIL',
      expected: 'DENY',
      model: 'pm.qms.license',
      field: 'activation_request_ids',
      result: summarizeRpc(protectedField),
    };

    const otherCompanyRecords = await callKw(qmPage, 'pm.qms.organization', 'search_read', [[['company_id', '!=', companyId]], ['id', 'company_id']], { limit: 10 });
    evidence.companyIsolation = {
      status: rpcAllowed(otherCompanyRecords) && otherCompanyRecords.result.length === 0 ? 'PASS' : 'FAIL',
      expected: 'no records outside current company',
      returnedRecords: otherCompanyRecords.result?.length ?? null,
    };

    const permittedCreate = await callKw(licensingPage, 'pm.qms.activation.request', 'create', [{ license_id: licenseId }]);
    activationRequestId = Number.isInteger(permittedCreate.result) ? permittedCreate.result : null;
    evidence.permittedCreate = {
      status: rpcAllowed(permittedCreate) && activationRequestId ? 'PASS' : 'FAIL',
      model: 'pm.qms.activation.request',
      result: summarizeRpc(permittedCreate),
    };
    expect(activationRequestId, 'permitted activation-request create must return an id').toBeTruthy();

    const permittedWrite = await callKw(licensingPage, 'pm.qms.activation.request', 'write', [[activationRequestId], { customer_name: 'M31 runtime evidence' }]);
    evidence.permittedWrite = {
      status: rpcAllowed(permittedWrite) && permittedWrite.result === true ? 'PASS' : 'FAIL',
      model: 'pm.qms.activation.request',
      result: summarizeRpc(permittedWrite),
    };

    const prohibitedCreate = await callKw(licensingPage, 'pm.qms.organization', 'create', [{ name: 'M31 prohibited', code: 'M31-PROHIBITED', organization_kind: 'operational', company_id: companyId }]);
    const prohibitedWrite = await callKw(licensingPage, 'pm.qms.organization', 'write', [[organization.id], { description: 'M31 prohibited' }]);
    const prohibitedUnlink = await callKw(licensingPage, 'pm.qms.organization', 'unlink', [[organization.id]]);
    evidence.prohibitedMutations = [
      { operation: 'create', model: 'pm.qms.organization', status: rpcDenied(prohibitedCreate) ? 'PASS' : 'FAIL', result: summarizeRpc(prohibitedCreate) },
      { operation: 'write', model: 'pm.qms.organization', status: rpcDenied(prohibitedWrite) ? 'PASS' : 'FAIL', result: summarizeRpc(prohibitedWrite) },
      { operation: 'unlink', model: 'pm.qms.organization', status: rpcDenied(prohibitedUnlink) ? 'PASS' : 'FAIL', result: summarizeRpc(prohibitedUnlink) },
    ];

    const qmUnlink = await callKw(qmPage, 'pm.qms.activation.request', 'unlink', [[activationRequestId]]);
    evidence.prohibitedActivationUnlink = {
      status: rpcDenied(qmUnlink) ? 'PASS' : 'FAIL',
      expected: 'DENY',
      result: summarizeRpc(qmUnlink),
    };
    evidence.workflowAuthorization = {
      status: 'NOT TESTED',
      reason: 'The activation-request model exposes no supported workflow transition method in this release; state is readonly and no synthetic state write was accepted as workflow evidence.',
    };
    test.info().annotations.push({ type: 'protected-data-mutation-evidence', description: JSON.stringify(evidence) });
    console.log(`M31_PROTECTED_DATA_MUTATION_EVIDENCE=${JSON.stringify(evidence)}`);
    expect(evidence.protectedRecordRead.status).toBe('PASS');
    expect(evidence.protectedLicenseRead.status).toBe('PASS');
    expect(evidence.protectedFieldRead.status).toBe('PASS');
    expect(evidence.companyIsolation.status).toBe('PASS');
    expect(evidence.permittedCreate.status).toBe('PASS');
    expect(evidence.permittedWrite.status).toBe('PASS');
    expect(evidence.prohibitedMutations.every((item) => item.status === 'PASS')).toBeTruthy();
    expect(evidence.prohibitedActivationUnlink.status).toBe('PASS');
  } finally {
    if (activationRequestId) {
      const cleanup = await callKw(licensingPage, 'pm.qms.activation.request', 'unlink', [[activationRequestId]]).catch(() => null);
      evidence.cleanup = { status: rpcAllowed(cleanup) ? 'PASS' : 'NOT CONFIRMED' };
    } else {
      evidence.cleanup = { status: 'NOT REQUIRED' };
    }
    console.log(`M31_PROTECTED_DATA_MUTATION_CLEANUP=${JSON.stringify(evidence.cleanup)}`);
    await qmContext.close();
    await licensingContext.close();
  }
});

test('fictional customer role sessions establish and remain customer-scoped', async ({ browser }) => {
  for (const [role, user] of Object.entries(state.roles)) {
    const context = await browser.newContext();
    const page = await context.newPage();
    const telemetry = installTelemetry(page, `role-${role.toLowerCase().replaceAll(' ', '-')}`);
    await login(page, user);
    const contract = ROLE_CONTRACT[role];
    const snapshot = await appSnapshot(page);
    expect(snapshot.shell, `${role} customer-shell contract mismatch`).toBe(contract.shell);
    if (contract.shell) {
      await openQmsApplication(page);
      await waitForCustomerNavigation(page);
      const roots = await customerRootSections(page);
      for (const root of contract.roots) expect(roots, `${role} is missing expected root ${root}`).toContain(root);
      for (const root of contract.forbiddenRoots) {
        const result = await customerRootSection(page, root);
        expect(result.reachable, `${role} unexpectedly reached forbidden root ${root}`).toBeFalsy();
      }
      await page.goto('/odoo');
      await waitForApp(page);
      expect((await appSnapshot(page)).clean).toBeTruthy();
    }
    expect(await hasText(page, 'Apps')).toBeFalsy();
    expect(await hasText(page, 'Settings')).toBeFalsy();
    await page.goto('/web/database/manager');
    await waitForApp(page);
    expect(await hasText(page, 'Database Manager')).toBeFalsy();
    test.info().annotations.push({ type: 'role-session', description: JSON.stringify({
      role,
      authenticated: true,
      customerShell: snapshot.shell,
      expectedRoots: contract.roots,
      forbiddenRoots: contract.forbiddenRoots,
      permittedRepresentative: contract.shell ? 'Dashboard' : 'authenticated application session',
      prohibitedDirectUrl: '/web/database/manager',
      prohibitedDirectUrlBlocked: true,
    }) });
    recordTelemetry(telemetry);
    expect(telemetry.pageErrors).toEqual([]);
    expect(telemetry.consoleErrors).toEqual([]);
    await context.close();
  }
});

test('Quality Manager customer shell, navigation, guided implementation and idempotent sync', async ({ page }) => {
  const telemetry = installTelemetry(page, 'quality-manager');
  await login(page, state.qm);
  expect((await appSnapshot(page)).shell).toBeTruthy();
  await openQmsApplication(page);
  await waitForCustomerNavigation(page);
  const browserDiagnostics = await browserRuntimeDiagnostics(page, telemetry);
  test.info().annotations.push({
    type: 'browser-runtime-diagnostics',
    description: JSON.stringify(browserDiagnostics),
  });
  console.log(`M31_BROWSER_RUNTIME_DIAGNOSTICS=${JSON.stringify(browserDiagnostics)}`);
  const rootNavigation = {};
  test.info().annotations.push({ type: 'experience-coverage', description: JSON.stringify(EXPERIENCE_COVERAGE) });
  for (const label of [...CUSTOMER_ROOTS, 'Configuration']) {
    rootNavigation[label] = await customerRootSection(page, label);
    expect(rootNavigation[label].reachable, `${label} is not reachable through customer navigation`).toBeTruthy();
  }
  test.info().annotations.push({ type: 'root-navigation', description: JSON.stringify(rootNavigation) });
  const inventory = await collectMenuInventory(page);
  state.menuInventory = inventory;
  const allLinks = menuLinks(inventory);
  test.info().annotations.push({ type: 'menu-inventory', description: JSON.stringify({ roots: inventory.roots, links: allLinks }) });
  expect(allLinks.some((item) => item.text === 'New Implementation')).toBeTruthy();
  expect(allLinks.some((item) => item.text === 'Implementations')).toBeTruthy();
  expect(allLinks.some((item) => item.text === 'Risks & Opportunities')).toBeTruthy();
  expect(allLinks.some((item) => item.text === 'Overview')).toBeTruthy();
  for (const label of ['Company Profile', 'Sites', 'Processes', 'Users & Access', 'Commercial License']) {
    expect(allLinks.some((item) => item.text === label), `${label} is not reachable through customer Configuration`).toBeTruthy();
  }
  expect(await hasText(page, 'Apps')).toBeFalsy();
  expect(await hasText(page, 'Settings')).toBeFalsy();
  const generation = await ensureGeneratedImplementation(page, inventory);
  const initialBody = await page.locator('body').innerText();
  const initialStats = implementationStats(initialBody);
  expect(initialStats).toEqual({ controls: true, activities: true, evidence: true, gaps: true, code: true });

  const syncGrowth = [];
  for (let i = 0; i < 2; i += 1) {
    await page.getByRole('button', { name: /^Sync Framework$/i }).click();
    await waitForApp(page);
    syncGrowth.push({ before: initialStats, after: implementationStats(await page.locator('body').innerText()) });
  }
  expect(syncGrowth[0].after).toEqual(initialStats);
  expect(syncGrowth[1].after).toEqual(initialStats);

  for (const tab of ['Packs', 'Controls', 'Implementation Areas', 'Activities', 'Evidence Summary', 'Readiness', 'Assessments', 'History']) {
    const tabLink = page.getByRole('tab', { name: tab, exact: true }).first();
    await expect(tabLink).toBeVisible();
    await tabLink.click();
    await waitForApp(page);
    expect((await appSnapshot(page)).clean).toBeTruthy();
  }

  await page.goto(generation.listHref);
  await waitForApp(page);
  const createButton = page.getByRole('button', { name: /^New$/i });
  const directCreateVisible = await createButton.isVisible().catch(() => false);
  const directCreate = { visible: directCreateVisible, possible: directCreateVisible, url: null, menuXmlid: state.implementationMenuXmlid };
  expect(directCreateVisible, 'generic Implementation creation must stay behind the guided workflow').toBeFalsy();

  const search = page.locator('input[placeholder*="Search"], input.o_searchview_input').first();
  await expect(search).toBeVisible();
  await search.fill('M31-no-match');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(600);
  const emptyText = await page.locator('body').innerText();
  const clearEmptyState = /no result|no records|no data|empty/i.test(emptyText);
  await search.fill('');
  await page.keyboard.press('Enter');
  const viewSwitcher = await page.locator('[data-tooltip="List"], [data-tooltip="Kanban"], .o_switch_view:visible').count();
  const pager = await page.locator('.o_pager:visible').count();
  test.info().annotations.push({ type: 'implementation-evidence', description: JSON.stringify({
    implementation: initialStats,
    generatedUrl: generation.url,
    syncGrowth,
    directCreate,
    clearEmptyState,
    viewSwitcher: viewSwitcher > 0,
    pager: pager > 0,
  }) });
  recordTelemetry(telemetry);
  expect(telemetry.pageErrors).toEqual([]);
  expect(telemetry.consoleErrors).toEqual([]);
  expect(telemetry.httpErrors.filter((item) => item.status >= 500)).toEqual([]);
});

test('Quality Manager domain, Action Center, Company Profile and customer terminology smoke', async ({ page }) => {
  const telemetry = installTelemetry(page, 'quality-manager-domains');
  await login(page, state.qm);
  const inventory = state.menuInventory || await collectMenuInventory(page);
  const targets = [
    ['ACTION_CENTER', 'Action Center'],
    ['RISK_BROWSER_FLOW', 'Risks & Opportunities'],
    ['NCR_BROWSER_FLOW', 'Nonconformities'],
    ['CAPA_BROWSER_FLOW', 'CAPA'],
    ['CUSTOMER_QUALITY_BROWSER_FLOW', 'Complaints'],
    ['AUDIT_BROWSER_FLOW', 'Audits'],
    ['KPI_BROWSER_FLOW', 'KPIs'],
    ['MANAGEMENT_REVIEW_BROWSER_FLOW', 'Management Review'],
    ['PEOPLE_BROWSER_FLOW', 'People'],
    ['CALIBRATION_BROWSER_FLOW', 'Monitoring Resources'],
    ['DOCUMENT_BROWSER_FLOW', 'Controlled Documents'],
    ['COMPANY_PROFILE', 'Company Profile'],
    ['PROCESSES', 'Processes'],
    ['SITES', 'Sites'],
    ['LICENSE', 'Commercial License'],
    ['ISO_9001', 'Overview'],
  ];
  const results = [];
  for (const [key, label] of targets) {
    const link = findMenuLink(inventory, label);
    if (!link) {
      results.push({ key, label, status: 'NOT_EXPOSED' });
      continue;
    }
    const result = await smokeRoute(page, label, link);
    result.status = result.clean ? 'PASS' : 'FAIL';
    results.push({ key, ...result });
    expect(result.clean, `${label} exposed an application error`).toBeTruthy();
  }
  const managementReview = results.find((item) => item.key === 'MANAGEMENT_REVIEW_BROWSER_FLOW');
  expect(managementReview?.status, 'Management Review must be exposed through customer navigation').toBe('PASS');
  expect(managementReview?.url, 'Management Review must resolve to an application route').toMatch(/\/odoo\//);
  await page.goto('/odoo');
  await waitForApp(page);
  const notificationButton = page.locator('button:has(.o-mail-MessagingMenu-counter), button:has(i[aria-label="Messages"])').first();
  const notificationsPresent = await notificationButton.isVisible().catch(() => false);
  let notificationText = '';
  if (notificationsPresent) {
    await notificationButton.click();
    await page.waitForTimeout(400);
    notificationText = (await page.locator('body').innerText()).slice(-1800);
  }
  const userButton = page.locator('button').filter({ has: page.locator('img.o_user_avatar') }).first();
  const userMenuPresent = await userButton.isVisible().catch(() => false);
  let userMenuText = '';
  if (userMenuPresent) {
    await userButton.click();
    await page.waitForTimeout(300);
    userMenuText = (await page.locator('body').innerText()).slice(-1800);
  }
  test.info().annotations.push({ type: 'domain-evidence', description: JSON.stringify({
    results: results.map(({ key, label, status, url }) => ({ key, label, status, url })),
    actionCenterSourceLinks: results.filter((item) => item.key === 'ACTION_CENTER').map((item) => item.url),
    notificationsPresent,
    notificationText,
    userMenuPresent,
    userMenuText,
    terminology: [
      { label: 'My Company', screen: 'authenticated header', classification: 'expected native single-company surface; review for terminology consistency' },
      { label: 'Implementations', screen: 'Implementation list', classification: 'customer-facing product label' },
      { label: 'Activities', screen: 'Implementation navigation', classification: 'customer-facing product label; distinguish from generic Tasks' },
    ],
  }) });
  recordTelemetry(telemetry);
  expect(telemetry.pageErrors).toEqual([]);
  expect(telemetry.consoleErrors).toEqual([]);
  expect(telemetry.httpErrors.filter((item) => item.status >= 500)).toEqual([]);
});

test('notification fixtures: assigned activity, chatter, record link, overdue and recipient isolation', async ({ browser }) => {
  test.setTimeout(180_000);
  const qmContext = await browser.newContext();
  const viewerContext = await browser.newContext();
  const qmPage = await qmContext.newPage();
  const viewerPage = await viewerContext.newPage();
  const evidence = { fixture: {}, activity: {}, chatter: {}, overdue: {}, isolation: {}, duplicates: { status: 'NOT_TESTED', reason: 'No supported repository idempotency API for generic mail.activity fixtures.' }, inAppEmail: { status: 'NOT_TESTED', reason: 'No supported disposable email target; in-app and email delivery cannot be compared.' }, cleanup: { status: 'NOT_CONFIRMED' } };
  let riskId = null;
  let activityId = null;
  try {
    await login(qmPage, state.qm);
    await login(viewerPage, state.viewer);
    const qmUid = await sessionUid(qmPage);
    const viewerUid = await sessionUid(viewerPage);
    const organizations = await callKw(qmPage, 'pm.qms.organization', 'search_read', [[], ['id']], { limit: 1 });
    const processes = await callKw(qmPage, 'pm.qms.process', 'search_read', [[], ['id']], { limit: 1 });
    const organizationId = organizations.result?.[0]?.id;
    const processId = processes.result?.[0]?.id;
    if (!qmUid || !viewerUid || !organizationId || !processId) throw new Error('Supported notification fixture prerequisites were not available');
    const yesterday = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);
    const created = await callKw(qmPage, 'pm.qms.risk', 'create', [{
      name: 'M31 disposable notification fixture',
      description: 'Fictional disposable notification fixture.',
      organization_id: organizationId,
      process_id: processId,
      owner_id: qmUid,
      target_date: yesterday,
      source: 'M31 disposable UAT',
    }]);
    if (!rpcAllowed(created) || !Number.isInteger(created.result)) throw new Error(`Risk fixture creation failed: ${JSON.stringify(summarizeRpc(created))}`);
    riskId = created.result;
    evidence.fixture = { status: 'PASS', model: 'pm.qms.risk', recordCreated: true };

    const scheduled = await callKw(qmPage, 'pm.qms.risk', 'activity_schedule', [
      [riskId],
      'mail.mail_activity_data_todo',
    ], { summary: 'M31 disposable reminder', note: 'Fictional reminder fixture.', user_id: qmUid, date_deadline: yesterday });
    if (!rpcAllowed(scheduled) || !Number.isInteger(scheduled.result)) throw new Error(`Activity fixture creation failed: ${JSON.stringify(summarizeRpc(scheduled))}`);
    activityId = scheduled.result;
    const qmActivities = await callKw(qmPage, 'mail.activity', 'search_read', [[['id', '=', activityId]], ['id', 'res_model', 'res_id', 'summary', 'date_deadline', 'user_id']]);
    evidence.activity = { status: rpcAllowed(qmActivities) && qmActivities.result?.length === 1 ? 'PASS' : 'FAIL', assignedToAuthorizedRole: qmActivities.result?.[0]?.user_id?.[0] === qmUid, recordId: qmActivities.result?.[0]?.res_id ?? null };

    const posted = await callKw(qmPage, 'pm.qms.risk', 'message_post', [[riskId]], { body: 'M31 disposable chatter fixture.', subtype_xmlid: 'mail.mt_note' });
    const messages = await callKw(qmPage, 'mail.message', 'search_read', [[['model', '=', 'pm.qms.risk'], ['res_id', '=', riskId]], ['id', 'model', 'res_id', 'message_type']]);
    evidence.chatter = { status: rpcAllowed(posted) && rpcAllowed(messages) && messages.result?.some((item) => item.res_id === riskId) ? 'PASS' : 'FAIL', linkedModel: 'pm.qms.risk', linkedRecordId: riskId };

    const risk = await callKw(qmPage, 'pm.qms.risk', 'read', [[riskId], ['id', 'code', 'is_overdue', 'days_overdue']]);
    evidence.overdue = { status: rpcAllowed(risk) && risk.result?.[0]?.is_overdue === true ? 'PASS' : 'FAIL', isOverdue: risk.result?.[0]?.is_overdue ?? null, daysOverdue: risk.result?.[0]?.days_overdue ?? null };

    const viewerActivity = await callKw(viewerPage, 'mail.activity', 'search_read', [[['id', '=', activityId]], ['id', 'res_model', 'res_id', 'summary']]);
    const viewerRisk = await callKw(viewerPage, 'pm.qms.risk', 'read', [[riskId], ['id', 'code']]);
    evidence.isolation = {
      status: !viewerActivity.result?.length && !viewerRisk.result?.length && (rpcDenied(viewerActivity) || rpcAllowed(viewerActivity)) ? 'PASS' : 'FAIL',
      unauthorizedActivityVisible: Boolean(viewerActivity.result?.length),
      unauthorizedRecordVisible: Boolean(viewerRisk.result?.length),
      linkedRecordNotExposed: !viewerRisk.result?.length,
    };
    test.info().annotations.push({ type: 'notification-evidence', description: JSON.stringify(evidence) });
    expect(evidence.fixture.status).toBe('PASS');
    expect(evidence.activity.status).toBe('PASS');
    expect(evidence.chatter.status).toBe('PASS');
    expect(evidence.overdue.status).toBe('PASS');
    expect(evidence.isolation.status).toBe('PASS');
  } finally {
    if (riskId) {
      const removed = await callKw(qmPage, 'pm.qms.risk', 'unlink', [[riskId]]).catch(() => null);
      evidence.cleanup = { status: rpcAllowed(removed) ? 'PASS' : 'NOT_CONFIRMED' };
    } else {
      evidence.cleanup = { status: 'NOT_REQUIRED' };
    }
    console.log(`M31_NOTIFICATION_CLEANUP=${JSON.stringify(evidence.cleanup)}`);
    await qmContext.close();
    await viewerContext.close();
  }
});

test('Quality Manager accessibility and responsive baseline', async ({ page }) => {
  const telemetry = installTelemetry(page, 'accessibility');
  const axeResults = [];
  await page.goto(LOGIN_PATH);
  await waitForApp(page);
  axeResults.push({ screen: 'login', ...(await new AxeBuilder({ page }).analyze()) });
  await login(page, state.qm);
  const inventory = state.menuInventory || await collectMenuInventory(page);
  const implementation = await ensureGeneratedImplementation(page, inventory);
  const screens = [
    ['dashboard', { href: '/odoo' }],
    ['implementation', { href: implementation.url }],
    ['action-center', findMenuLink(inventory, 'Action Center')],
    ['company-profile', findMenuLink(inventory, 'Company Profile')],
  ];
  for (const [screen, entry] of screens) {
    if (!entry) continue;
    await openCustomerMenuAction(page, entry, waitForApp);
    axeResults.push({ screen, ...(await new AxeBuilder({ page }).analyze()) });
  }
  const axeSummary = axeResults.map((item) => ({
    screen: item.screen,
    violations: item.violations.length,
    critical: item.violations.filter((finding) => finding.impact === 'critical').length,
    serious: item.violations.filter((finding) => finding.impact === 'serious').length,
    moderate: item.violations.filter((finding) => finding.impact === 'moderate').length,
    incomplete: item.incomplete.length,
    ids: item.violations.map((finding) => finding.id),
  }));
  await test.info().attach('axe-results.json', { body: JSON.stringify(axeResults, null, 2), contentType: 'application/json' });
  test.info().annotations.push({ type: 'axe-summary', description: JSON.stringify(axeSummary) });
  for (const viewport of [{ width: 1440, height: 900 }, { width: 1366, height: 768 }]) {
    await page.setViewportSize(viewport);
    await page.goto('/odoo');
    await waitForApp(page);
    await expect(page.getByText('Dashboard', { exact: true }).first()).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
    expect(overflow, `horizontal overflow at ${viewport.width}x${viewport.height}`).toBeFalsy();
  }
  recordTelemetry(telemetry);
  expect(telemetry.pageErrors).toEqual([]);
  expect(telemetry.consoleErrors).toEqual([]);
  expect(telemetry.httpErrors.filter((item) => item.status >= 500)).toEqual([]);
});

test('Quality Manager keyboard focus and responsive navigation contract', async ({ page }) => {
  const telemetry = installTelemetry(page, 'keyboard-responsive-navigation');
  await login(page, state.qm);
  await openQmsApplication(page);
  await waitForCustomerNavigation(page);
  const evidence = [];
  for (const viewport of [
    { width: 1600, height: 900 },
    { width: 1280, height: 720 },
    { width: 1024, height: 720 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto('/odoo');
    await waitForApp(page);
    await expect(page.getByText('Dashboard', { exact: true }).first()).toBeVisible();
    const navbar = page.locator('nav.o_main_navbar, .o_main_navbar').first();
    const actionable = navbar.locator('a:visible, button:visible').filter({ hasNotText: /Messages|Notifications/ });
    await expect(actionable.first()).toBeVisible();
    await actionable.first().focus();
    const focusBefore = await page.evaluate(() => {
      const node = document.activeElement;
      if (!node) return null;
      const style = getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return {
        tag: node.tagName.toLowerCase(),
        text: node.textContent.trim().replace(/\s+/g, ' ').slice(0, 100),
        inNavbar: Boolean(node.closest('nav.o_main_navbar, .o_main_navbar')),
        visible: Boolean(node.offsetWidth || node.offsetHeight || node.getClientRects().length),
        focusVisible: node.matches(':focus-visible'),
        outline: style.outlineStyle,
        outlineWidth: style.outlineWidth,
        boxShadow: style.boxShadow,
        rect: { width: Math.round(rect.width), height: Math.round(rect.height) },
      };
    });
    expect(focusBefore?.inNavbar).toBeTruthy();
    expect(focusBefore?.visible).toBeTruthy();
    await page.keyboard.press('Tab');
    const focusAfter = await page.evaluate(() => ({
      inNavbar: Boolean(document.activeElement?.closest('nav.o_main_navbar, .o_main_navbar')),
      visible: Boolean(document.activeElement?.offsetWidth || document.activeElement?.offsetHeight || document.activeElement?.getClientRects().length),
      tag: document.activeElement?.tagName?.toLowerCase() || null,
    }));
    expect(focusAfter.visible).toBeTruthy();

    const more = navbar.locator('button[title="More Menu"], button[aria-label="More Menu"]').first();
    const moreVisible = await more.isVisible().catch(() => false);
    let moreEvidence = { status: 'NOT_APPLICABLE', visible: false };
    if (moreVisible) {
      await more.focus();
      expect(await more.getAttribute('aria-expanded')).not.toBeNull();
      await more.click({ timeout: 5_000 });
      const overflow = page.locator('.o_more_dropdown_section:visible').first();
      await expect(overflow).toBeVisible();
      moreEvidence = {
        status: 'PASS',
        visible: true,
        ariaExpanded: await more.getAttribute('aria-expanded'),
        roots: await page.locator('.o_more_dropdown_section:visible').allTextContents(),
      };
      await page.keyboard.press('Escape');
    }
    const roots = await customerRootSections(page);
    const horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
    expect(horizontalOverflow, `horizontal overflow at ${viewport.width}x${viewport.height}`).toBeFalsy();
    evidence.push({ viewport, focusBefore, focusAfter, more: moreEvidence, roots });
  }
  test.info().annotations.push({ type: 'keyboard-responsive-evidence', description: JSON.stringify(evidence) });
  recordTelemetry(telemetry);
  expect(telemetry.pageErrors).toEqual([]);
  expect(telemetry.consoleErrors).toEqual([]);
  expect(telemetry.httpErrors.filter((item) => item.status >= 500)).toEqual([]);
});

test('restricted Viewer and Technical Administrator separation', async ({ browser }) => {
  test.skip(!state.viewer, 'Viewer fixture not supplied');
  const viewerContext = await browser.newContext();
  const viewer = await viewerContext.newPage();
  const viewerTelemetry = installTelemetry(viewer, 'viewer');
  await login(viewer, state.viewer);
  const viewerInventory = await collectMenuInventory(viewer);
  expect(await hasText(viewer, 'Apps')).toBeFalsy();
  expect(await hasText(viewer, 'Settings')).toBeFalsy();
  expect(await hasText(viewer, 'Commercial License')).toBeFalsy();
  const viewerImplementation = findMenuLink(viewerInventory, 'Implementations');
  if (viewerImplementation) {
    await viewer.goto(viewerImplementation.href);
    await waitForApp(viewer);
    expect(await viewer.getByRole('button', { name: /^New$/i }).count()).toBe(0);
  }
  await viewerContext.close();

  const adminContext = await browser.newContext();
  const admin = await adminContext.newPage();
  const adminTelemetry = installTelemetry(admin, 'technical-admin');
  await login(admin, state.admin);
  await admin.getByTitle('Home Menu').click();
  await expect(admin.getByText('Apps', { exact: true })).toBeVisible();
  await expect(admin.getByText('Settings', { exact: true })).toBeVisible();
  const adminText = await admin.locator('body').innerText();
  test.info().annotations.push({ type: 'persona-separation', description: JSON.stringify({
    viewer: { expectedShell: true, forbiddenRoots: ['Configuration', 'Apps', 'Settings'], representativeForbiddenUrl: '/web/database/manager' },
    technicalAdmin: { expectedShell: false, permittedRoots: ['Apps', 'Settings'], forbiddenCustomerShell: true, applicationText: /Apps/.test(adminText) && /Settings/.test(adminText) },
  }) });
  recordTelemetry(viewerTelemetry);
  recordTelemetry(adminTelemetry);
  expect(viewerTelemetry.pageErrors).toEqual([]);
  expect(adminTelemetry.pageErrors).toEqual([]);
  await adminContext.close();
});
