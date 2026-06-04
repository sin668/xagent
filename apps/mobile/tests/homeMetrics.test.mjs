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
  assert.equal(dashboard.executableAiTasks.length, 1);
  assert.equal(dashboard.channelPerformance.length, 1);
  assert.equal(dashboard.channelPerformance[0].name, '官网/公开目录');
});

test('seed dashboard excludes High and Forbidden work from executable homepage sections', () => {
  assert.equal(homeDashboard.executableAiTasks.some((task) => task.channelRisk === 'High'), false);
  assert.equal(homeDashboard.executableAiTasks.some((task) => task.channelRisk === 'Forbidden'), false);
  assert.equal(homeDashboard.channelPerformance.some((channel) => channel.riskLevel === 'High'), false);
  assert.equal(homeDashboard.channelPerformance.some((channel) => channel.riskLevel === 'Forbidden'), false);
});
