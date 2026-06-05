import assert from 'node:assert/strict';
import { test } from 'node:test';

import { buildBottomTabs, navigateBottomTab } from '../src/services/bottomTabs.js';

test('bottom tabs expose top-level mobile destinations with active state', () => {
  const tabs = buildBottomTabs('leads');

  assert.deepEqual(
    tabs.map((tab) => `${tab.key}:${tab.path}:${tab.active}`),
    [
      'home:/pages/home/index:false',
      'leads:/pages/leads/index:true',
      'customers:/pages/customers/index:false',
      'email:/pages/email-replies/index:false',
      'sources:/pages/sources/index:false',
    ],
  );
  assert.equal(tabs.some((tab) => tab.key === 'ai'), false);
});

test('bottom tabs support customers workbench as a top-level active destination', () => {
  const tabs = buildBottomTabs('customers');
  const customers = tabs.find((tab) => tab.key === 'customers');

  assert.equal(customers.path, '/pages/customers/index');
  assert.equal(customers.label, '客户');
  assert.equal(customers.active, true);
});

test('bottom tabs support email replies as a fifth-stage top-level destination', () => {
  const tabs = buildBottomTabs('email');
  const email = tabs.find((tab) => tab.key === 'email');

  assert.equal(email.path, '/pages/email-replies/index');
  assert.equal(email.label, '邮件');
  assert.equal(email.active, true);
});

test('bottom tab navigation uses redirectTo and skips the active tab', () => {
  const calls = [];
  const fakeUni = {
    redirectTo(payload) {
      calls.push(payload);
    },
  };
  const [home, leads] = buildBottomTabs('leads');

  assert.equal(navigateBottomTab(leads, fakeUni), false);
  assert.equal(navigateBottomTab(home, fakeUni), true);
  assert.deepEqual(calls, [{ url: '/pages/home/index' }]);
});

test('bottom tab navigation falls back to navigateTo when redirectTo is unavailable', () => {
  const calls = [];
  const fakeUni = {
    navigateTo(payload) {
      calls.push(payload);
    },
  };
  const [home] = buildBottomTabs('leads');

  assert.equal(navigateBottomTab(home, fakeUni), true);
  assert.deepEqual(calls, [{ url: '/pages/home/index' }]);
});
