import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "outputs/feishu";
const outputPath = `${outputDir}/高风险社媒人工小样本研究表.xlsx`;

const headers = [
  "研究ID",
  "平台",
  "初始风险等级",
  "研究动作",
  "是否可公开访问",
  "是否需要登录",
  "允许记录字段",
  "禁止记录字段",
  "是否进入正式线索库",
  "是否进入触达队列",
  "允许动作",
  "禁止动作",
  "政策/依据链接",
  "待核查事项",
  "建议结论",
  "合规复核状态",
  "备注",
];

const rows = [
  [
    "HRS-0001",
    "VKontakte",
    "High",
    "policy_review_only / manual_small_sample_only",
    "待核查",
    "可能需要登录",
    "官网、公开邮箱、公开电话、公开 WhatsApp/Telegram、公开商务说明",
    "粉丝、好友、评论、互动关系、私信内容、非公开资料",
    "否",
    "否",
    "人工查看公开主页；只记录跳转官网或公开商务联系方式",
    "自动采集、自动私信、自动加好友、登录后批采、采集粉丝/评论/关系链",
    "https://vk.com/terms",
    "最新 API/自动化规则、公开主页字段保存边界、商业再利用限制",
    "不作为自动采集来源；仅辅助发现官网后回到 Low/Medium 来源复核",
    "待合规复核",
    "High 渠道不得进入 AI/Agent 自动化任务和触达队列",
  ],
  [
    "HRS-0002",
    "Odnoklassniki",
    "High",
    "policy_review_only / manual_small_sample_only",
    "待核查",
    "可能需要登录",
    "官网、公开邮箱、公开电话、公开 WhatsApp/Telegram、公开商务说明",
    "粉丝、好友、评论、互动关系、私信内容、非公开资料",
    "否",
    "否",
    "人工查看公开主页；只记录跳转官网或公开商务联系方式",
    "自动采集、自动互动、登录后批采、采集用户资料或关系链",
    "https://ok.ru/regulations",
    "公开主页字段边界、自动化访问限制、商业联系限制",
    "只做小样本政策研究；不进入正式线索库",
    "待合规复核",
    "若发现官网，必须从官网重新采集和取证",
  ],
  [
    "HRS-0003",
    "TikTok",
    "High",
    "policy_review_only",
    "待核查",
    "可能需要登录",
    "公开主页简介中的官网或商务邮箱",
    "视频、评论、粉丝、点赞、用户画像、非公开资料",
    "否",
    "否",
    "人工查看公开主页简介是否有官网；优先跳转官网复核",
    "自动化提取、抓取视频/评论/粉丝、批量保存内容、自动互动",
    "https://www.tiktok.com/legal/page/row/terms-of-service/en",
    "地区版本条款、Business API 可用性、公开资料保存范围",
    "原则上不进入 PoC 线索流程",
    "待合规复核",
    "仅可作为品牌发现渠道，不作为自动采集源",
  ],
  [
    "HRS-0004",
    "Max",
    "High",
    "policy_review_only",
    "待核查",
    "通讯工具通常需要账号",
    "官方 business/partner 入口、公开官网",
    "联系人、群、通讯录、聊天内容、非公开资料",
    "否",
    "否",
    "研究官方条款和 business/partner 能力",
    "自动加联系人、群发、抓取通讯录、登录后采集",
    "待核查：Max 官方用户协议、隐私政策、商业合作条款",
    "官方条款、是否提供商业 API 或企业授权",
    "等官方商业接口或授权机制明确后再评估",
    "待合规复核",
    "通讯工具默认不作为公开获客采集源",
  ],
];

function styleSheet(sheet, rowCount, colCount) {
  const all = sheet.getRangeByIndexes(0, 0, rowCount, colCount);
  const header = sheet.getRangeByIndexes(0, 0, 1, colCount);
  header.format.fill.color = "#7F1D1D";
  header.format.font.color = "#FFFFFF";
  header.format.font.bold = true;
  all.format.wrapText = true;
  sheet.freezePanes.freezeRows(1);
  const widths = [120, 160, 120, 260, 130, 130, 300, 330, 130, 130, 310, 360, 360, 280, 360, 140, 360];
  widths.forEach((width, i) => {
    sheet.getRangeByIndexes(0, i, rowCount, 1).format.columnWidth = width;
  });
}

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("高风险社媒研究");
const values = [headers, ...rows];
sheet.getRangeByIndexes(0, 0, values.length, headers.length).values = values;
styleSheet(sheet, values.length, headers.length);

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

console.log(JSON.stringify({ outputPath, rows: rows.length, columns: headers.length }, null, 2));
