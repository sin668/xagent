import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "outputs/poc-feishu-seed";
const outputPath = `${outputDir}/俄罗斯车辆采购AI获客PoC-飞书五张表Seed数据.xlsx`;

const people = ["张三", "李四", "王五", "赵六", "陈晨", "刘洋", "Anna", "Dmitry"];

const cities = [
  "Moscow",
  "Saint Petersburg",
  "Vladivostok",
  "Novosibirsk",
  "Kazan",
  "Yekaterinburg",
  "Krasnodar",
  "Rostov-on-Don",
  "Samara",
  "Nizhny Novgorod",
];

const dealerNames = [
  "Avto Premium Moscow",
  "Siberia Motors",
  "VladAuto Trade",
  "Nevsky Auto Dealer",
  "Kazan Auto Import",
  "Ural Used Cars",
  "Far East Motors",
  "Volga Auto Center",
  "Rostov Car Market",
  "Krasnodar Drive",
  "AutoLine SPB",
  "Moscow Fleet Cars",
  "Novosibirsk AutoHub",
  "Drom Dealer Vlad",
  "Prime Cars Kazan",
  "East Import Auto",
  "Auto Selection RU",
  "Dealer Garage Media",
  "Auto Parts Service RU",
  "Classic Motors Watch",
];

const sourcePlatforms = [
  "官网",
  "搜索引擎",
  "地图",
  "公开目录",
  "YouTube",
  "Telegram",
  "VK",
  "Avito",
  "Auto.ru",
  "Drom",
  "X",
  "Facebook/Instagram",
];

const customerTypes = [
  "当地车商/二级经销商",
  "当地车商/二级经销商",
  "当地车商/二级经销商",
  "个人买家",
  "KOL/汽车博主",
  "非目标",
  "未知",
];

const levels = ["A", "B", "B", "C", "Invalid", "Watch"];
const statuses = {
  A: ["新采集", "待补全", "待复核"],
  B: ["待复核", "可交付客服", "客服跟进中"],
  C: ["可交付销售", "销售跟进中"],
  Invalid: ["无效/暂不匹配"],
  Watch: ["沉淀观察"],
};

function pick(list, index, offset = 0) {
  return list[(index + offset) % list.length];
}

function dateTime(dayOffset, hour = 10, minute = 0) {
  const day = String(27 + dayOffset).padStart(2, "0");
  return `2026-05-${day} ${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function safeDomain(name, index) {
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return `https://${slug || `dealer-${index}`}.example.ru`;
}

function buildLeadRows() {
  const rows = [];
  for (let i = 0; i < 20; i += 1) {
    const id = `LEAD-${String(i + 1).padStart(4, "0")}`;
    const level = pick(levels, i);
    const isDoNotContact = i === 6 || i === 15;
    const risk = i === 13 ? "High" : i === 18 ? "Medium" : pick(["Low", "Low", "Medium"], i);
    const customerType = i === 18 ? "非目标" : pick(customerTypes, i);
    const status = isDoNotContact ? "拒绝联系/勿扰" : pick(statuses[level], i);
    const name = dealerNames[i];
    const city = pick(cities, i);
    const platform = pick(sourcePlatforms, i);
    const domain = safeDomain(name, i + 1);

    rows.push([
      id,
      name,
      "Russia",
      city,
      customerType,
      level,
      status,
      i % 4 === 0 ? "used Japanese cars, SUVs" : i % 4 === 1 ? "premium used vehicles, sedans" : i % 4 === 2 ? "commercial vans and pickup trucks" : "mixed used car inventory",
      level === "Invalid" ? "否" : i % 5 === 0 ? "未知" : "是",
      level === "Invalid" ? "页面显示为维修/配件服务，不是车商" : platform === "VK" ? "公开页面每周更新库存照片" : "公开页面展示二手车库存和联系方式",
      i % 3 === 0 ? "email + phone" : i % 3 === 1 ? "phone + Telegram" : "website form + email",
      `sales${i + 1}@seed-dealer${i + 1}.example.ru`,
      `+7 999 ${String(100 + i).padStart(3, "0")} ${String(2000 + i).padStart(4, "0")}`,
      i % 2 === 0 ? `+7 999 ${String(100 + i).padStart(3, "0")} ${String(2000 + i).padStart(4, "0")}` : "Unknown",
      i % 4 === 0 ? `@dealer_seed_${i + 1}` : "Unknown",
      domain,
      platform,
      `${domain}/contact`,
      level === "Invalid" ? "公开页面主要为配件/维修，不符合目标客户" : "公开页面展示车辆销售、库存或经销商联系方式",
      risk,
      level,
      level === "C" ? "已回复并表达采购兴趣，建议交付出口销售" : level === "B" ? "有库存和公开联系方式，建议交付客服" : level === "A" ? "基础信息完整但主营车型需补全" : level === "Invalid" ? "非目标业务或无有效联系方式" : "信息不足，建议沉淀观察",
      level === "A" ? "主营车型、进口车相关性" : level === "Watch" ? "联系方式、业务真实性" : "",
      level === "C" ? "交付销售" : level === "B" ? "交付客服" : level === "Invalid" ? "标记无效" : "补全信息",
      pick(people, i),
      level === "C" ? "出口销售" : level === "B" ? "客服" : level === "Invalid" ? "暂不交付" : "线索运营",
      isDoNotContact ? "是" : "否",
      isDoNotContact ? "客户明确拒绝继续联系" : "",
      dateTime(i % 3, 9 + (i % 7), 15),
      dateTime((i + 1) % 3, 14 + (i % 5), 30),
      level === "Invalid" ? "无效" : level === "Watch" ? "退回补全" : "通过",
      level === "Invalid" ? "已记录到失败案例库候选" : "样例数据，待真实采集替换",
      i === 11 ? "疑似重复" : i === 12 ? "强重复" : "非重复",
      i < 12 ? `OUT-${String(i + 1).padStart(4, "0")}` : "",
      i % 2 === 0 ? `INV-${String((i % 20) + 1).padStart(4, "0")}` : "",
      "Seed 数据，仅用于 PoC 表格验证",
    ]);
  }
  return rows;
}

function buildChannelRows() {
  const channels = [
    ["官网", "公开网页", "Russia", "used cars dealer Russia; дилер подержанных автомобилей", "Low", "人工查看公开页面;记录官网、邮箱、电话、表单链接;AI 处理人工复制的公开文本", "自动表单轰炸;高频访问;抓取登录区;保存无来源信息", "客户官网 Terms/Privacy/Contact 页面；robots.txt 如有", "待核查", "人工公开页查看", "是"],
    ["公开目录", "公开目录", "Russia", "auto dealer directory Russia; каталог автодилеров", "Low", "人工查看公开企业目录;记录企业名、官网、公开联系方式和目录链接", "批量抓取目录;采集非公开会员信息;绕过访问限制", "目录网站 Terms/Privacy 页面", "待核查", "人工公开页查看", "是"],
    ["搜索引擎", "搜索结果", "Russia", "дилер подержанных автомобилей; used car dealer Moscow", "Low", "使用关键词人工搜索;打开公开结果;记录原始来源链接", "批量抓取搜索结果页;规避搜索限制;保存无来源结果", "搜索引擎服务条款和结果页来源网站条款", "待核查", "搜索引擎结果", "是"],
    ["Google 地图结果", "地图标注", "Russia", "used car dealer Moscow; car dealer Vladivostok", "Medium", "人工查看公开商户卡片;优先记录商户官网;保留地图链接", "批量抓取地图内容;离线复制地图内容;绕过 API/配额;批量保存评论/照片", "https://cloud.google.com/maps-platform/terms; https://developers.google.com/maps/documentation/places/web-service/policies", "已初核", "人工公开页查看", "是"],
    ["Yandex 地图结果", "地图标注", "Russia", "автосалон бу; авто дилер", "Medium", "人工查看公开商户卡片;优先记录官网和公开电话;保留 Yandex Maps 链接", "批量抓取地图;规避限制;复制地图数据库;高频访问", "https://www.yandex.ru/legal/maps_termsofuse/en/; https://yandex.ru/dev/commercial/doc/en/", "已初核", "人工公开页查看", "是"],
    ["YouTube", "公开社媒/视频", "Russia", "обзор авто дилер; авто из Китая дилер", "Medium", "查看公开视频、频道简介和描述中的官网/邮箱;记录公开视频链接", "自动评论;自动私信;批量订阅;批量抓取评论/频道;绕过 API", "https://www.youtube.com/t/terms", "已初核", "人工公开页查看", "否"],
    ["Telegram", "公开频道/通讯工具", "Russia", "авто из Китая; автосалон", "High", "政策研究;人工查看公开频道简介;记录公开官网，不主动私信", "自动私信;自动加群;批量群发;抓取私域群;骚扰非联系人", "https://telegram.org/tos; https://telegram.org/faq_spam", "已初核", "禁止采集", "否"],
    ["X", "公开社媒", "Russia", "russian car dealer; used cars Russia", "High", "政策研究;通过公开资料人工找到官网", "浏览器自动化抓取;自动关注;自动私信;批量互动;规避 API", "https://docs.x.com/developer-guidelines; https://help.x.com/articles/76915-automation-rules-and-best-practices; https://docs.x.com/developer-terms/policy", "已初核", "禁止采集", "否"],
    ["Facebook/Instagram", "公开社媒", "Russia", "used cars Russia; auto dealer Russia", "High", "政策研究;人工查看公开主页;优先记录官网", "自动抓取;自动私信;自动加好友;未授权数据收集", "https://www.facebook.com/legal/automated_data_collection_terms", "已初核", "禁止采集", "否"],
    ["Avito", "平台市场", "Russia", "авто дилер; автомобили с пробегом", "High", "政策研究;人工小样本查看;优先记录商家公开官网", "登录后批量采集;自动联系卖家;规避平台风控;抓取非公开内容", "Avito 官方规则/用户协议入口，待复核", "待核查", "禁止采集", "否"],
    ["VK", "公开社媒", "Russia", "автосалон; авто из Китая", "High", "政策研究;人工查看公开主页;优先记录官网", "自动私信;自动加好友;登录后批量采集;抓取非公开内容", "VK Terms/API 文档入口，待复核", "待核查", "禁止采集", "否"],
    ["Auto.ru", "平台市场", "Russia", "dealer cars; автосалон", "High", "政策研究;人工小样本查看公开商户页;保留原始链接", "使用机器人批量抓取;复制数据库;自动联系;绕过限制", "https://yandex.ru/legal/autoru_terms_of_service/ru/", "已初核", "禁止采集", "否"],
    ["Drom", "平台市场/论坛", "Russia", "автосалон drom; drom dealer", "Medium", "人工查看公开商户页或公开帖;优先记录官网和公开联系方式", "批量抓取;自动联系;抓取登录内容;规避限制", "Drom 官方条款入口，待复核", "待核查", "人工公开页查看", "是"],
    ["本地行业协会", "公开目录", "Russia", "auto association dealer list; ассоциация автодилеров", "Low", "查看公开会员名单;记录官网和公开联系方式", "采集非公开会员资料;批量骚扰", "协会官网 Terms/Privacy 页面", "待核查", "人工公开页查看", "是"],
    ["进口商官网", "公开网页", "Russia", "import cars from China Russia; импорт авто из Китая", "Low", "查看公开页;记录公开联系方式;AI 处理人工复制文本", "自动表单轰炸;批量邮件;抓取登录区", "进口商官网 Terms/Privacy/Contact 页面", "待核查", "人工公开页查看", "是"],
    ["公开论坛", "公开论坛", "Russia", "used car dealer forum; авто форум дилер", "Medium", "查看公开帖;记录公开官网或商务联系方式", "自动注册;自动发帖;抓取登录内容;批量私信", "论坛 Terms/Rules 页面", "待核查", "人工公开页查看", "是"],
    ["汽车媒体", "公开网页", "Russia", "dealer interview Russia; интервью автодилер", "Medium", "查看公开报道;记录采访中的官网和公开商务信息", "抓取非公开数据;自动评论;复制付费内容", "媒体网站 Terms/Privacy 页面", "待核查", "人工公开页查看", "是"],
    ["WhatsApp", "通讯工具", "Russia", "dealer whatsapp public", "High", "仅记录客户主动公开的商务号码;不主动自动添加", "自动加联系人;自动群发;未授权触达;批量骚扰", "https://www.whatsapp.com/legal/business-policy", "已初核", "禁止采集", "否"],
    ["微信", "通讯工具", "Russia", "WeChat dealer", "High", "C 级客户主动提供后人工添加;仅人工跟进", "自动加好友;批量拉群;群发;购买异常账号", "企业内部微信使用规范，待补充", "待核查", "禁止采集", "否"],
    ["线下展会名录", "公开目录", "Russia", "auto expo exhibitor list; автосалон выставка", "Low", "查看公开参展商;记录官网和公开商务联系方式", "采集非公开参会者信息;批量骚扰", "展会官网 Terms/Privacy 页面", "待核查", "人工公开页查看", "是"],
  ];

  return channels.map((row, i) => [
    `CH-${String(i + 1).padStart(4, "0")}`,
    ...row,
    pick(people, i),
    dateTime(i % 3, 11, 0),
    row[4] === "High" ? "High 风险渠道只做政策研究和人工小样本，不进入自动化任务" : "按 channel-risk-register.md 更新，用于 PoC 渠道风险视图验证",
  ]);
}

function buildInventoryRows() {
  const vehicles = [
    ["Toyota", "Land Cruiser Prado", 2022, 18000, "准新车", "2.7L, 4WD, leather"],
    ["Toyota", "Camry", 2021, 42000, "二手车", "2.5L, hybrid, comfort"],
    ["Nissan", "X-Trail", 2020, 51000, "二手车", "2.0L, AWD"],
    ["Lexus", "RX 350", 2021, 28000, "准新车", "premium package"],
    ["Mitsubishi", "Pajero Sport", 2019, 76000, "二手车", "diesel, 4WD"],
    ["Honda", "CR-V", 2022, 22000, "准新车", "hybrid, AWD"],
    ["Mazda", "CX-5", 2021, 34000, "二手车", "2.5L, AWD"],
    ["Hyundai", "Santa Fe", 2020, 59000, "二手车", "diesel, 7 seats"],
    ["Kia", "Sorento", 2021, 39000, "二手车", "2.2 diesel"],
    ["Mercedes-Benz", "GLE 350", 2020, 47000, "二手车", "premium SUV"],
    ["BMW", "X5", 2021, 36000, "二手车", "xDrive, M package"],
    ["Audi", "Q7", 2020, 62000, "二手车", "quattro, 7 seats"],
    ["Volkswagen", "Tiguan", 2022, 24000, "准新车", "2.0 TSI"],
    ["Skoda", "Kodiaq", 2021, 41000, "二手车", "7 seats"],
    ["Geely", "Monjaro", 2023, 8000, "库存车", "2.0T, AWD"],
    ["Chery", "Tiggo 8 Pro", 2023, 6000, "库存车", "1.6T, 7 seats"],
    ["Haval", "Dargo", 2023, 9000, "库存车", "2.0T, AWD"],
    ["BYD", "Song Plus", 2023, 12000, "准新车", "PHEV"],
    ["Zeekr", "001", 2023, 5000, "准新车", "EV, long range"],
    ["Toyota", "Hiace", 2020, 68000, "二手车", "commercial van"],
  ];

  return vehicles.map((v, i) => {
    const price = 18000 + i * 1850;
    const status = i % 7 === 0 ? "待确认" : i % 9 === 0 ? "已过期" : i % 11 === 0 ? "不可外发" : "已确认";
    const exportStatus = i % 10 === 0 ? "不可出口" : i % 4 === 0 ? "待确认" : "可出口";
    return [
      `INV-${String(i + 1).padStart(4, "0")}`,
      v[0],
      v[1],
      v[2],
      v[3],
      v[4],
      v[5],
      price,
      "USD",
      status,
      exportStatus,
      `https://seed-inventory.example.com/cars/${String(i + 1).padStart(4, "0")}`,
      `2026-06-${String(5 + (i % 20)).padStart(2, "0")}`,
      i % 2 === 0 ? "二级经销商;进口车商" : "当地车商/二级经销商",
      pick(["Russia", "Russia;Kazakhstan", "Russia;Belarus"], i),
      pick(people, i + 2),
      status === "已确认" ? "内部参考，可进入报价前复核" : "价格或出口状态需复核，不可直接外发",
    ];
  });
}

function buildOutreachRows() {
  const statusesList = ["未发送", "已发送", "已回复", "拒绝", "无回复", "错误联系方式"];
  return Array.from({ length: 20 }, (_, i) => {
    const status = pick(statusesList, i);
    const doNotContact = status === "拒绝";
    const channel = pick(["Email", "官网表单", "电话", "WhatsApp", "Telegram", "VK"], i);
    const risk = ["WhatsApp", "Telegram", "VK"].includes(channel) ? "High" : channel === "电话" ? "Medium" : "Low";
    return [
      `OUT-${String(i + 1).padStart(4, "0")}`,
      `LEAD-${String((i % 20) + 1).padStart(4, "0")}`,
      dealerNames[i % dealerNames.length],
      channel,
      risk,
      i % 2 === 0 ? "RU-V1-B级初触达" : "RU-V1-C级需求确认",
      pick(people, i + 3),
      status === "未发送" ? "" : dateTime(i % 3, 10 + (i % 6), 20),
      status,
      status === "已回复" ? "客户询问 Toyota SUV 和付款方式" : status === "拒绝" ? "客户明确表示暂不需要继续联系" : status === "错误联系方式" ? "邮箱退信或电话无效" : "",
      status === "已回复" ? "升级销售" : status === "拒绝" ? "标记勿扰" : status === "错误联系方式" ? "补充信息" : "继续跟进",
      status === "已回复" || status === "无回复" ? dateTime((i + 1) % 3, 15, 0) : "",
      doNotContact ? "是" : "否",
      doNotContact ? "客户明确拒绝继续联系" : "",
      status === "未发送" ? "否" : "是",
      risk === "High" ? "高风险渠道仅记录人工小样本，不自动发送" : "未承诺价格、物流、清关、付款或交付周期",
      dateTime(i % 3, 9, 45),
      "Seed 触达记录，用于验证状态和勿扰视图",
    ];
  });
}

function buildScriptRows() {
  const types = ["初次触达", "价格FAQ", "车况FAQ", "物流FAQ", "付款FAQ", "合作模式FAQ", "拒绝联系回复", "其他"];
  return Array.from({ length: 20 }, (_, i) => {
    const type = pick(types, i);
    const status = pick(["草稿", "待业务审核", "待合规审核", "可外发", "停用"], i);
    return [
      `SCR-${String(i + 1).padStart(4, "0")}`,
      `RU-V${1 + Math.floor(i / 8)}-${type}-${i + 1}`,
      type,
      i % 3 === 0 ? "B;C" : i % 3 === 1 ? "B" : "C",
      i % 2 === 0 ? "Email;官网表单" : "Email",
      `中文内部版示例：用于${type}场景，先确认客户是否有采购二手车、准新车或库存车需求，不做价格和交付承诺。`,
      `Здравствуйте! Мы изучаем возможность сотрудничества по поставкам автомобилей. Если вам не интересно, пожалуйста, сообщите нам, и мы больше не будем вас беспокоить.`,
      "最终价格;物流时效;清关结果;付款安全;交付周期",
      status,
      status === "可外发" ? pick(people, i) : "",
      status === "可外发" ? dateTime(i % 3, 16, 0) : "",
      `v1.${i}`,
      "如不方便联系，请回复 stop 或 сообщите, пожалуйста, если не хотите получать сообщения.",
      "AI 只能引用已审核版本，不得自由承诺交易条件",
      status === "停用" ? "旧版本停用，防止误用" : "Seed 话术，用于审核流程验证",
    ];
  });
}

const sheets = [
  {
    name: "客户线索",
    headers: [
      "线索ID",
      "客户名称",
      "国家",
      "城市/地区",
      "客户类型",
      "线索等级",
      "线索状态",
      "主营车型/业务",
      "是否经营二手/进口车",
      "规模/活跃度信号",
      "联系方式摘要",
      "邮箱",
      "电话",
      "WhatsApp",
      "Telegram",
      "官网",
      "来源平台",
      "来源链接",
      "来源证据备注",
      "渠道风险等级",
      "AI 推荐等级",
      "AI 推荐原因",
      "缺失信息",
      "下一步建议",
      "负责人",
      "交付团队",
      "是否勿扰",
      "勿扰原因",
      "首次采集时间",
      "最近更新时间",
      "人工复核结果",
      "人工复核备注",
      "重复判断",
      "关联触达记录",
      "关联车源",
      "备注",
    ],
    rows: buildLeadRows(),
  },
  {
    name: "渠道来源",
    headers: [
      "渠道ID",
      "平台/渠道名称",
      "渠道类型",
      "适用国家",
      "关键词",
      "风险等级",
      "允许动作",
      "禁止动作",
      "政策来源",
      "政策核查状态",
      "采集方式",
      "是否进入 PoC",
      "负责人",
      "最近核查时间",
      "备注",
    ],
    rows: buildChannelRows(),
  },
  {
    name: "车源报价",
    headers: [
      "车源ID",
      "品牌",
      "车型",
      "年份",
      "里程",
      "车况",
      "配置摘要",
      "价格",
      "币种",
      "价格确认状态",
      "可出口状态",
      "图片/视频链接",
      "有效期",
      "适配客户类型",
      "适配地区",
      "负责人",
      "备注",
    ],
    rows: buildInventoryRows(),
  },
  {
    name: "触达记录",
    headers: [
      "触达ID",
      "关联客户",
      "客户名称快照",
      "触达渠道",
      "渠道风险等级",
      "话术版本",
      "发送人",
      "发送时间",
      "触达状态",
      "回复摘要",
      "下一步动作",
      "下一步时间",
      "是否触发勿扰",
      "勿扰原因",
      "人工确认",
      "合规备注",
      "创建时间",
      "备注",
    ],
    rows: buildOutreachRows(),
  },
  {
    name: "话术库",
    headers: [
      "话术ID",
      "话术名称",
      "话术类型",
      "适用等级",
      "适用渠道",
      "中文内部版",
      "俄语客户版",
      "禁止承诺点",
      "审核状态",
      "审核人",
      "审核时间",
      "版本号",
      "拒绝联系路径",
      "风险提示",
      "备注",
    ],
    rows: buildScriptRows(),
  },
];

function colName(index) {
  let n = index + 1;
  let name = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    name = String.fromCharCode(65 + rem) + name;
    n = Math.floor((n - 1) / 26);
  }
  return name;
}

const workbook = Workbook.create();

for (const [sheetIndex, config] of sheets.entries()) {
  const sheet = workbook.worksheets.add(config.name);
  const lastCol = colName(config.headers.length - 1);
  const values = [config.headers, ...config.rows];
  sheet.getRange(`A1:${lastCol}${values.length}`).values = values;

  const headerRange = sheet.getRange(`A1:${lastCol}1`);
  headerRange.format = {
    fill: { color: "#17324D" },
    font: { color: "#FFFFFF", bold: true },
    alignment: { horizontal: "center", vertical: "center", wrapText: true },
  };

  sheet.getRange(`A2:${lastCol}${values.length}`).format = {
    alignment: { vertical: "top", wrapText: true },
  };

  const idRange = sheet.getRange(`A2:A${values.length}`);
  idRange.format = {
    fill: { color: "#F3F6FA" },
    font: { bold: true, color: "#17324D" },
  };

}

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

for (const config of sheets) {
  const singleWorkbook = Workbook.create();
  const sheet = singleWorkbook.worksheets.add(config.name);
  const lastCol = colName(config.headers.length - 1);
  const values = [config.headers, ...config.rows];
  sheet.getRange(`A1:${lastCol}${values.length}`).values = values;
  sheet.getRange(`A1:${lastCol}1`).format = {
    fill: { color: "#17324D" },
    font: { color: "#FFFFFF", bold: true },
    alignment: { horizontal: "center", vertical: "center", wrapText: true },
  };
  sheet.getRange(`A2:${lastCol}${values.length}`).format = {
    alignment: { vertical: "top", wrapText: true },
  };
  sheet.getRange(`A2:A${values.length}`).format = {
    fill: { color: "#F3F6FA" },
    font: { bold: true, color: "#17324D" },
  };

  const safeName = config.name.replace(/[\/\\:*?"<>|]/g, "-");
  const singleOutput = await SpreadsheetFile.exportXlsx(singleWorkbook);
  await singleOutput.save(`${outputDir}/${safeName}.xlsx`);
}

const summary = sheets.map((s) => `${s.name}: ${s.rows.length} rows`).join("\n");
console.log(`Saved ${outputPath}\nSaved separate files in ${outputDir}\n${summary}`);
