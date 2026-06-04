import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildChannelDashboardView,
  buildDateRangeQuery,
  fetchChannelLeadDashboard,
  isInvestableChannel,
} from '../src/services/channelDashboard.js';

test('channel dashboard view exposes totals, B/C counts, and invalid rate text', () => {
  const view = buildChannelDashboardView({
    summary: {
      candidate_count: 5,
      bc_grade_count: 3,
      invalid_rate: 0.4,
    },
    channels: [
      {
        channel_name: 'official_website',
        display_name: '官网/公开目录',
        risk_level: 'Low',
        risk_status: 'active',
        candidate_count: 3,
        b_grade_count: 1,
        c_grade_count: 1,
        bc_grade_count: 2,
        invalid_rate: 1 / 3,
        investment_recommendation: 'candidate',
      },
    ],
  });

  assert.equal(view.summary.candidateCount, 5);
  assert.equal(view.summary.bcGradeCount, 3);
  assert.equal(view.summary.invalidRateText, '40%');
  assert.equal(view.channels[0].bcText, 'B 1 / C 1');
  assert.equal(view.channels[0].invalidRateText, '33%');
  assert.equal(view.channels[0].riskLabel, '低风险');
  assert.equal(isInvestableChannel(view.channels[0]), true);
});

test('high and forbidden channels are rendered as research or blocked, never investable', () => {
  const view = buildChannelDashboardView({
    summary: {},
    channels: [
      {
        channel_name: 'vkontakte',
        display_name: 'VK',
        risk_level: 'High',
        risk_status: 'researching',
        candidate_count: 0,
        b_grade_count: 0,
        c_grade_count: 0,
        bc_grade_count: 0,
        invalid_rate: 0,
        investment_recommendation: 'blocked',
      },
      {
        channel_name: 'facebook',
        display_name: 'Facebook',
        risk_level: 'Forbidden',
        risk_status: 'blocked',
        candidate_count: 0,
        b_grade_count: 0,
        c_grade_count: 0,
        bc_grade_count: 0,
        invalid_rate: 0,
        investment_recommendation: 'blocked',
      },
    ],
  });

  assert.equal(view.channels[0].statusLabel, '研究中');
  assert.equal(view.channels[1].statusLabel, '已阻断');
  assert.equal(isInvestableChannel(view.channels[0]), false);
  assert.equal(isInvestableChannel(view.channels[1]), false);
});

test('date range query keeps dashboard filtering explicit', () => {
  assert.equal(buildDateRangeQuery({ dateFrom: '2026-05-01', dateTo: '2026-05-28' }), '?date_from=2026-05-01&date_to=2026-05-28');
  assert.equal(buildDateRangeQuery({}), '');
});

test('fetch channel dashboard uses the backend dashboard contract', async () => {
  const requestedUrls = [];
  const payload = await fetchChannelLeadDashboard({
    baseUrl: 'https://api.example.test',
    dateFrom: '2026-05-01',
    dateTo: '2026-05-28',
    fetcher: async (url) => {
      requestedUrls.push(url);
      return {
        ok: true,
        json: async () => ({ summary: { candidate_count: 0 }, channels: [] }),
      };
    },
  });

  assert.equal(
    requestedUrls[0],
    'https://api.example.test/dashboard/channel-leads?date_from=2026-05-01&date_to=2026-05-28',
  );
  assert.equal(payload.channels.length, 0);
});
