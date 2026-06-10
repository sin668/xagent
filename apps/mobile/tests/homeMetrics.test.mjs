import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildHomeDashboard,
  filterExecutableAiTasks,
  getPendingPriorityLeads,
} from '../src/services/homeMetrics.js';
import { homeDashboard } from '../src/data/homeSeed.js';

const sampleLeads = [
  {
    id: 'lead-1',
    grade: 'B',
    status: 'pending',
    doNotContact: false,
    followUpDueToday: true,
    channelRisk: 'Low',
  },
  {
    id: 'lead-2',
    grade: 'C',
    status: 'pending',
    doNotContact: false,
    followUpDueToday: true,
    channelRisk: 'Medium',
  },
  {
    id: 'lead-3',
    grade: 'B',
    status: 'pending',
    doNotContact: true,
    followUpDueToday: true,
    channelRisk: 'Low',
  },
  {
    id: 'lead-4',
    grade: 'A',
    status: 'pending',
    doNotContact: false,
    followUpDueToday: false,
    channelRisk: 'Low',
  },
  {
    id: 'lead-5',
    grade: 'Invalid',
    status: 'pending',
    doNotContact: false,
    followUpDueToday: true,
    channelRisk: 'Low',
  },
];

const sampleAiTasks = [
  {
    id: 'task-1',
    title: '公开官网补全任务',
    status: 'running',
    channelRisk: 'Low',
    progress: 68,
  },
  {
    id: 'task-2',
    title: 'VK 高风险页面研究',
    status: 'running',
    channelRisk: 'High',
    progress: 10,
  },
  {
    id: 'task-3',
    title: 'Forbidden 自动触达',
    status: 'queued',
    channelRisk: 'Forbidden',
    progress: 0,
  },
];

test('pending priority leads include only pending B/C leads and exclude do-not-contact customers', () => {
  const leads = getPendingPriorityLeads(sampleLeads);

  assert.deepEqual(
    leads.map((lead) => lead.id),
    ['lead-1', 'lead-2'],
  );
});

test('executable AI tasks exclude High and Forbidden channel risks', () => {
  const tasks = filterExecutableAiTasks(sampleAiTasks);

  assert.deepEqual(
    tasks.map((task) => task.id),
    ['task-1'],
  );
});

test('home dashboard summarizes acceptance metrics and channel performance', () => {
  const dashboard = buildHomeDashboard({
    leads: sampleLeads,
    aiTasks: sampleAiTasks,
    customers: [
      { id: 'customer-a', grade: 'A', hasVehicleIntent: true, followupStatus: 'due_today' },
      { id: 'customer-b', grade: 'B', hasVehicleIntent: false, nextAction: '今日待跟进' },
      { id: 'customer-c', grade: 'C', hasVehicleIntent: true, nextAction: '销售跟进中' },
      { id: 'customer-watch', grade: 'WATCH', hasVehicleIntent: true, nextAction: '今日待跟进' },
    ],
    channels: [
      {
        name: '官网/公开目录',
        riskLevel: 'Low',
        totalLeads: 50,
        bGradeLeads: 23,
        effectiveRate: 0.46,
      },
      {
        name: '高风险社媒研究',
        riskLevel: 'High',
        totalLeads: 12,
        bGradeLeads: 4,
        effectiveRate: 0.33,
      },
    ],
  });

  assert.equal(dashboard.pendingPriorityCount, 2);
  assert.equal(dashboard.totalCandidateLeads, 5);
  assert.equal(dashboard.bGradeRatioText, '40%');
  assert.equal(dashboard.pendingFollowUpCount, 2);
  assert.deepEqual(dashboard.leadStats.map((stat) => stat.label), ['A/B/C级线索', '线索来源', '被清洗线索']);
  assert.deepEqual(dashboard.leadStats.map((stat) => stat.count), [4, 2, 1]);
  assert.equal(dashboard.executableAiTasks.length, 1);
  assert.equal(dashboard.channelPerformance.length, 1);
  assert.equal(dashboard.channelPerformance[0].name, '官网/公开目录');
  assert.deepEqual(dashboard.customerStats.map((stat) => stat.label), ['A/B/C级客户', '车型意向客户', '今日待跟进']);
  assert.deepEqual(dashboard.customerStats.map((stat) => stat.count), [3, 3, 2]);
});

test('home dashboard can use backend summary counts for lead statistic cards', () => {
  const dashboard = buildHomeDashboard({
    leads: sampleLeads,
    channels: [],
    leadStatsSummary: {
      abc_grade_count: 128,
      source_count: 93,
      cleaned_lead_count: 41,
    },
  });

  assert.deepEqual(dashboard.leadStats.map((stat) => stat.count), [128, 93, 41]);
});

test('home dashboard uses source candidate and executed cleanup totals for linked lead stat cards', () => {
  const dashboard = buildHomeDashboard({
    leads: sampleLeads,
    channels: [
      { name: '官网', riskLevel: 'Low' },
      { name: '公开目录', riskLevel: 'Medium' },
    ],
    leadStatsSummary: {
      sourceCandidatesTotal: 57,
      cleanedLeadsTotal: 19,
    },
  });

  assert.deepEqual(dashboard.leadStats.map((stat) => stat.count), [4, 57, 19]);
});

test('seed dashboard excludes High and Forbidden work from executable homepage sections', () => {
  assert.equal(homeDashboard.executableAiTasks.some((task) => task.channelRisk === 'High'), false);
  assert.equal(homeDashboard.executableAiTasks.some((task) => task.channelRisk === 'Forbidden'), false);
  assert.equal(homeDashboard.channelPerformance.some((channel) => channel.riskLevel === 'High'), false);
  assert.equal(homeDashboard.channelPerformance.some((channel) => channel.riskLevel === 'Forbidden'), false);
});
