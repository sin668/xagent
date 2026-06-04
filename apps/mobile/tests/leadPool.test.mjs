import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildLeadPoolStats,
  buildLeadFilterTabs,
  filterLeadPool,
  getLeadCardViewModel,
} from '../src/services/leadPool.js';
import { leadPoolSeed } from '../src/data/leadPoolSeed.js';

const sampleLeads = [
  {
    id: 'lead-a',
    customerName: 'Prime Auto Moscow',
    city: 'Moscow',
    customerType: '进口车商',
    channel: '官网',
    grade: 'A',
    status: 'pending',
    riskLevel: 'Low',
    doNotContact: false,
    isOverdue: false,
    contacts: [{ type: 'Email', value: 'prime@dealer.example.ru' }],
  },
  {
    id: 'lead-b',
    customerName: 'AutoCity Moscow',
    city: 'Moscow',
    customerType: '二手进口车商',
    channel: '官网 + 邮箱',
    grade: 'B',
    status: 'pending',
    riskLevel: 'Low',
    doNotContact: false,
    isOverdue: false,
    contacts: [{ type: 'email', value: 'sales@autocity.example' }],
  },
  {
    id: 'lead-c',
    customerName: 'Siberia Auto Trade',
    city: 'Novosibirsk',
    customerType: '已询价车商',
    channel: 'WhatsApp',
    grade: 'C',
    status: 'pending',
    riskLevel: 'Medium',
    doNotContact: false,
    isOverdue: true,
    handoffTeam: 'export_sales',
    complianceReviewStatus: 'required',
    contacts: [{ type: 'whatsapp', value: '+7 900 000 00 00' }],
  },
  {
    id: 'lead-dnc',
    customerName: 'Quiet Dealer',
    city: 'Kazan',
    customerType: '车商',
    channel: '官网',
    grade: 'B',
    status: 'do_not_contact',
    riskLevel: 'Low',
    doNotContact: true,
    isOverdue: true,
    contacts: [{ type: 'email', value: 'quiet@example.test' }],
  },
  {
    id: 'lead-invalid',
    customerName: 'Parts Service RU',
    city: 'Kazan',
    customerType: '配件/维修',
    channel: '公开目录',
    grade: 'Invalid',
    status: 'invalid',
    riskLevel: 'Low',
    doNotContact: false,
    isOverdue: false,
    contacts: [{ type: 'email', value: 'parts-service@example.test' }],
  },
  {
    id: 'lead-watch',
    customerName: 'Watch Only Auto',
    city: 'Saint Petersburg',
    customerType: '观察线索',
    channel: '搜索引擎',
    grade: 'Watch',
    status: 'watch',
    riskLevel: 'Medium',
    doNotContact: false,
    isOverdue: false,
    contacts: [{ type: 'telegram', value: '@watch_auto' }],
  },
  {
    id: 'lead-high',
    customerName: 'VK Cars Import RU',
    city: 'Moscow',
    customerType: '公开社媒线索',
    channel: 'VK',
    grade: 'B',
    status: 'pending',
    riskLevel: 'High',
    requiresSecondaryVerification: true,
    hasContact: true,
    evidenceStatus: 'present',
    contacts: [{ type: 'vkontakte', value: 'https://vk.com/cars-import' }],
  },
  {
    id: 'lead-missing-contact',
    customerName: 'No Contact Dealer',
    city: 'Vladivostok',
    customerType: '车商',
    channel: '公开目录',
    grade: 'B',
    status: 'pending',
    riskLevel: 'Medium',
    hasContact: false,
    evidenceStatus: 'present',
    contacts: [],
  },
];

test('default pending list excludes invalid, watch, and do-not-contact leads', () => {
  const leads = filterLeadPool(sampleLeads, 'pending');

  assert.deepEqual(
    leads.map((lead) => lead.id),
    ['lead-a', 'lead-b', 'lead-c', 'lead-high', 'lead-missing-contact'],
  );
});

test('all list shows every lead regardless contact status or grade', () => {
  const leads = filterLeadPool(sampleLeads, 'all');

  assert.deepEqual(
    leads.map((lead) => lead.id),
    ['lead-a', 'lead-b', 'lead-c', 'lead-dnc', 'lead-invalid', 'lead-watch', 'lead-high', 'lead-missing-contact'],
  );
});

test('lead pool supports A/B/C, email, social, and D/E filters', () => {
  assert.deepEqual(
    filterLeadPool(sampleLeads, 'grade-abc').map((lead) => lead.id),
    ['lead-a', 'lead-b', 'lead-c', 'lead-high', 'lead-missing-contact'],
  );
  assert.deepEqual(
    filterLeadPool(sampleLeads, 'email-contact').map((lead) => lead.id),
    ['lead-a', 'lead-b', 'lead-dnc', 'lead-invalid'],
  );
  assert.deepEqual(
    filterLeadPool(sampleLeads, 'social-contact').map((lead) => lead.id),
    ['lead-c', 'lead-watch', 'lead-high'],
  );
  assert.deepEqual(
    filterLeadPool(sampleLeads, 'grade-de').map((lead) => lead.id),
    ['lead-invalid', 'lead-watch'],
  );
});

test('lead pool stats summarize contact and grade groups for mobile header', () => {
  const stats = buildLeadPoolStats(sampleLeads);

  assert.deepEqual(
    stats.map((item) => `${item.key}:${item.label}:${item.count}`),
    [
      'email:有邮箱联系线索:4',
      'social:有社交媒体联系线索:3',
      'grade-abc:A/B/C级线索:5',
      'grade-de:D/E级线索:2',
    ],
  );
});

test('C grade lead card view model exposes sales handoff and compliance review status', () => {
  const card = getLeadCardViewModel(sampleLeads.find((lead) => lead.id === 'lead-c'));

  assert.equal(card.gradeLabel, 'C 级');
  assert.equal(card.handoffLabel, '交付销售');
  assert.equal(card.complianceLabel, '待合规复核');
  assert.equal(card.riskLabel, '中风险');
});

test('lead card displays Watch as D grade and Invalid as E grade', () => {
  const invalidCard = getLeadCardViewModel(sampleLeads.find((lead) => lead.id === 'lead-invalid'));
  const watchCard = getLeadCardViewModel(sampleLeads.find((lead) => lead.id === 'lead-watch'));

  assert.equal(watchCard.gradeLabel, 'D 级');
  assert.equal(invalidCard.gradeLabel, 'E 级');
});

test('filter tabs include counts for required mobile lead pool views', () => {
  const tabs = buildLeadFilterTabs(sampleLeads);

  assert.deepEqual(
    tabs.map((tab) => `${tab.key}:${tab.count}`),
    ['all:8', 'email-contact:4', 'social-contact:3', 'grade-abc:5', 'grade-de:2'],
  );
});

test('seed pending filter does not expose invalid, watch, or do-not-contact records', () => {
  const ids = filterLeadPool(leadPoolSeed, 'pending').map((lead) => lead.id);

  assert.deepEqual(ids, ['ru-auto-city', 'ru-vostok', 'ru-siberia']);
  assert.equal(ids.includes('ru-quiet'), false);
  assert.equal(ids.includes('ru-parts'), false);
  assert.equal(ids.includes('ru-watch'), false);
});
