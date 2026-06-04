import { buildHomeDashboard } from '../services/homeMetrics.js';

export const homeSeedLeads = [
  { id: 'ru-001', grade: 'B', status: 'pending', doNotContact: false, followUpDueToday: true, channelRisk: 'Low' },
  { id: 'ru-002', grade: 'C', status: 'pending', doNotContact: false, followUpDueToday: true, channelRisk: 'Medium' },
  { id: 'ru-003', grade: 'B', status: 'pending', doNotContact: true, followUpDueToday: true, channelRisk: 'Low' },
  { id: 'ru-004', grade: 'B', status: 'pending', doNotContact: false, followUpDueToday: false, channelRisk: 'Low' },
  { id: 'ru-005', grade: 'A', status: 'pending', doNotContact: false, followUpDueToday: true, channelRisk: 'Low' },
  { id: 'ru-006', grade: 'C', status: 'pending', doNotContact: false, followUpDueToday: false, channelRisk: 'Medium' },
  { id: 'ru-007', grade: 'B', status: 'completed', doNotContact: false, followUpDueToday: false, channelRisk: 'Low' },
  { id: 'ru-008', grade: 'Invalid', status: 'pending', doNotContact: false, followUpDueToday: false, channelRisk: 'Low' },
];

export const homeSeedAiTasks = [
  {
    id: 'task-web-enrich',
    title: '公开官网补全任务',
    source: '官网/公开目录',
    status: 'running',
    channelRisk: 'Low',
    candidateCount: 18,
    estimateText: '预计 6 分钟',
    progress: 68,
  },
  {
    id: 'task-grade-review',
    title: 'B/C 级线索人工复核',
    source: 'AI 分级',
    status: 'review',
    channelRisk: 'Medium',
    candidateCount: 7,
    estimateText: '交付前检查',
    progress: 35,
  },
  {
    id: 'task-social-research',
    title: '高风险社媒研究样本',
    source: 'VK',
    status: 'research_only',
    channelRisk: 'High',
    candidateCount: 9,
    estimateText: '不进入自动作业',
    progress: 5,
  },
];

export const homeSeedChannels = [
  {
    name: '官网/公开目录',
    riskLevel: 'Low',
    totalLeads: 50,
    bGradeLeads: 23,
    effectiveRate: 0.46,
  },
  {
    name: '搜索引擎/Yandex',
    riskLevel: 'Medium',
    totalLeads: 28,
    bGradeLeads: 9,
    effectiveRate: 0.32,
  },
  {
    name: '高风险社媒研究',
    riskLevel: 'High',
    totalLeads: 12,
    bGradeLeads: 4,
    effectiveRate: 0.33,
  },
];

export const homeDashboard = buildHomeDashboard({
  leads: homeSeedLeads,
  aiTasks: homeSeedAiTasks,
  channels: homeSeedChannels,
});
