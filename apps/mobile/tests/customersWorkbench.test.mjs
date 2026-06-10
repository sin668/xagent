import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildCustomerFilterTabs,
  buildCustomerStats,
  createCustomersService,
  filterCustomers,
  getCustomerCardViewModel,
  mapCustomer,
  sortCustomersByNextAction,
} from '../src/services/customers.js';

const customerPayload = {
  items: [
    {
      id: 'customer-low',
      name: 'Low Priority Motors',
      country: 'Russia',
      city: 'Kazan',
      customer_type: 'local_dealer_secondary_dealer',
      grade: 'B',
      status: 'sales_following',
      owner: 'sales-a',
      contacts: [{ type: 'email', value: 'sales@low.example.ru', is_primary: true }],
      contact_summary: { total: 1, primary: 'email:sales@low.example.ru' },
      vehicle_intent_summary: { total: 0, items: [] },
      next_action: '销售跟进中',
      next_action_priority: 60,
    },
    {
      id: 'customer-today',
      name: 'AutoCity Moscow',
      country: 'Russia',
      city: 'Moscow',
      customer_type: 'local_dealer_secondary_dealer',
      grade: 'B',
      status: 'customer_service_following',
      owner: 'cs-a',
      contacts: [{ type: 'telegram', value: '@autocity', is_primary: true }],
      contact_summary: { total: 2, primary: 'telegram:@autocity' },
      vehicle_intent_summary: { total: 1, items: [{ label: 'Toyota Camry' }] },
      followup_status: 'due_today',
      next_action: '今日待跟进',
      next_action_priority: 10,
    },
    {
      id: 'customer-compliance',
      name: 'Siberia Auto Trade',
      country: 'Russia',
      city: 'Novosibirsk',
      customer_type: 'importer',
      grade: 'C',
      status: 'ready_for_sales',
      owner: '',
      contacts: [{ type: 'phone', value: '+7 383 *** **22', is_primary: true }],
      contact_summary: { total: 1, primary: 'phone:+7 383 *** **22' },
      vehicle_intent_summary: { total: 2, items: [{ label: '新能源 SUV' }, { label: '混动 SUV' }] },
      next_action: 'C级待合规复核',
      next_action_priority: 20,
    },
  ],
};

test('客户 mapper 展示名称、国家城市、等级、联系方式、意向车型和下一步动作', () => {
  const mapped = mapCustomer(customerPayload.items[1]);
  const card = getCustomerCardViewModel(mapped);

  assert.equal(mapped.id, 'customer-today');
  assert.equal(mapped.name, 'AutoCity Moscow');
  assert.equal(mapped.countryCityText, 'Russia · Moscow');
  assert.equal(card.gradeLabel, 'B 级');
  assert.equal(card.contactSummaryText, 'telegram:@autocity');
  assert.equal(card.vehicleIntentText, 'Toyota Camry');
  assert.equal(card.nextAction, '今日待跟进');
});

test('客户默认按下一步动作优先级排序', () => {
  const sorted = sortCustomersByNextAction(customerPayload.items.map(mapCustomer));

  assert.deepEqual(sorted.map((customer) => customer.id), ['customer-today', 'customer-compliance', 'customer-low']);
});

test('客户工作台筛选支持A/B/C客户、今日待跟进、C级待合规、有车型意向、待分配', () => {
  const customers = customerPayload.items.map(mapCustomer);
  const tabs = buildCustomerFilterTabs(customers);

  assert.deepEqual(tabs.map((tab) => tab.key), ['all', 'today', 'c_compliance', 'has_intent', 'unassigned']);
  assert.deepEqual(filterCustomers(customers, 'grade_abc').map((item) => item.id), [
    'customer-low',
    'customer-today',
    'customer-compliance',
  ]);
  assert.equal(filterCustomers(customers, 'today').map((item) => item.id).join(','), 'customer-today');
  assert.equal(filterCustomers(customers, 'c_compliance').map((item) => item.id).join(','), 'customer-compliance');
  assert.deepEqual(filterCustomers(customers, 'has_intent').map((item) => item.id), ['customer-today', 'customer-compliance']);
  assert.equal(filterCustomers(customers, 'unassigned').map((item) => item.id).join(','), 'customer-compliance');
});

test('客户统计卡作为过滤入口，第一块统计 A/B/C 级客户', () => {
  const customers = customerPayload.items.map(mapCustomer);
  const stats = buildCustomerStats(customers);

  assert.deepEqual(stats.map((stat) => stat.filterKey), ['grade_abc', 'has_intent', 'today']);
  assert.equal(stats[0].label, 'A/B/C级客户');
  assert.equal(stats[0].count, 3);
  assert.equal(stats[1].count, 2);
  assert.equal(stats[2].count, 1);
});

test('客户服务只读取 customers，不混入 staging_leads', async () => {
  const calls = [];
  const service = createCustomersService({
    client: {
      get(endpoint) {
        calls.push(endpoint);
        return Promise.resolve(customerPayload);
      },
    },
  });

  const result = await service.listCustomers({ limit: 100 });

  assert.deepEqual(calls, ['/customers?limit=100']);
  assert.equal(result.items.length, 3);
  assert.deepEqual(result.items.map((item) => item.id), ['customer-today', 'customer-compliance', 'customer-low']);
});
