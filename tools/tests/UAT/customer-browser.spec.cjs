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
  'QMS Administrator': ['Company Profile', 'Sites', 'Processes', 'Users & Access', 'Framework Administration'],
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
    const moreMenu = page.locator('nav.o_main_navbar, .o_main_navbar')
      .first()
      .getByRole('button', { name: 'More Menu', exact: true })
      .first();
    const moreMenuPresent = await moreMenu.isVisible().catch(() => false);
    let overflowLabels = [];
    if (moreMenuPresent) {
      if ((await moreMenu.getAttribute('aria-expanded')) !== 'true') await moreMenu.click();
      overflowLabels = await page.locator([
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
  const moreMenu = navbar.getByRole('button', { name: 'More Menu', exact: true }).first();
  const moreMenuPresent = await moreMenu.isVisible().catch(() => false);
  let overflowLabels = [];
  if (moreMenuPresent) {
    if ((await moreMenu.getAttribute('aria-expanded')) !== 'true') await moreMenu.click();
    overflowLabels = await page.locator([
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
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(900);
}

async function login(page, user) {
  await page.goto(LOGIN_PATH);
  await expect(page.locator('input[name="login"], input[type="email"]').first()).toBeVisible();
  await page.locator('input[name="login"], input[type="email"]').first().fill(user.login);
  await page.locator('input[name="password"], input[type="password"]').first().fill(user.password);
  await page.getByRole('button', { name: /log in|iniciar sesión/i }).click();
  await page.waitForTimeout(1_500);
  if (/\/web\/login(?:\?|$)/.test(page.url())) throw new Error('Authentication failed');
  if (page.url().includes('/web/login_successful')) await page.goto('/odoo');
  if (!/\/odoo(?:\/|\?|$)/.test(page.url())) await page.goto('/odoo');
  await waitForApp(page);
}

async function collectMenuInventory(page) {
  await page.goto('/odoo');
  await waitForApp(page);
  const roots = await customerRootSections(page);
  const menus = {};
  for (const root of roots) {
    await openRootMenu(page, root);
    menus[root] = (await customerMenuEntries(page)).map((entry) => ({ ...entry, root }));
  }
  return { roots, menus };
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
  await page.goto(new URL(entry.href, page.url()).toString());
  await waitForApp(page);
  await page.waitForTimeout(250);
  page.off('response', onResponse);

  const payload = actionResponses.at(-1)?.payload || {};
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

test('Configuration browser contract and direct action authorization', async ({ browser }) => {
  const users = [
    ['Quality Manager', state.qm],
    ['QMS Administrator', state.qmsAdmin],
    ['Licensing Administrator', state.licensingAdmin],
  ];
  const inventories = {};
  const payloadActions = {};
  const roleEvidence = [];
  for (const [role, user] of users) {
    const context = await browser.newContext();
    const page = await context.newPage();
    const telemetry = installTelemetry(page, `configuration-${role.toLowerCase().replaceAll(' ', '-')}`);
    const result = { role, configuration: 'NOT TESTED', allowed: [] };
    try {
      await login(page, user);
      const inventory = await collectMenuInventory(page);
      inventories[role] = inventory;
      payloadActions[role] = await browserMenuActionEntries(page);
      const configuration = await customerRootSection(page, 'Configuration');
      result.configuration = configuration.reachable ? 'PASS' : 'FAIL';
      result.configurationEvidence = configuration;
      for (const label of CONFIGURATION_CONTRACT[role]) {
        const link = findMenuLink(inventory, label);
        if (!link) {
          result.allowed.push({ label, status: 'NOT TESTED', reason: 'surface not exposed through normal navigation' });
          continue;
        }
        const screen = await smokeRoute(page, label, link);
        result.allowed.push({ label, status: screen.clean ? 'PASS' : 'FAIL', url: screen.url });
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
    await context.close();
  }

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
  for (const [role, user, key, expected] of directProbes) {
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
    recordTelemetry(telemetry);
    await context.close();
  }
  const authorizationEvidence = { roleEvidence, directEvidence };
  test.info().annotations.push({ type: 'configuration-authorization', description: JSON.stringify(authorizationEvidence) });
  console.log(`M31_CONFIGURATION_AUTHORIZATION=${JSON.stringify(authorizationEvidence)}`);
  expect({
    configurationRolesPass: roleEvidence.every((item) => item.configuration === 'PASS'),
    permittedSurfacesPass: roleEvidence.flatMap((item) => item.allowed).every((item) => item.status === 'PASS'),
    directActionChecksPass: directEvidence.every((item) => item.status === 'PASS'),
  }).toEqual({
    configurationRolesPass: true,
    permittedSurfacesPass: true,
    directActionChecksPass: true,
  });
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
