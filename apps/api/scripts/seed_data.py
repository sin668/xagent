"""
XAgent Seed Data Generator

Usage:
    cd apps/api
    python -m scripts.seed_data          # Run all seeds
    python -m scripts.seed_data --table channel_risk_rules  # Run single table
    python -m scripts.seed_data --dry-run  # Preview without writing
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.enums import (
    ChannelPlanStatus,
    ChannelRiskLevel,
    ComplianceReviewStatus,
    ContactMethodType,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    FailedCaseType,
    KnowledgeEmbeddingStatus,
    KnowledgeItemStatus,
    KnowledgeReviewStatus,
    OutreachStatus,
    PageSnapshotReadStatus,
    RiskEventSeverity,
    RiskEventStatus,
    ScriptReviewStatus,
    SourcePlatform,
    SourceUsageType,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.models import (
    ChannelPlan,
    ChannelRiskRule,
    CollectionTask,
    ComplianceReview,
    ContactMethod,
    Customer,
    FailedCase,
    InventoryItem,
    KnowledgeCollection,
    KnowledgeEmbedding,
    KnowledgeItem,
    LeadSource,
    OutreachRecord,
    ScriptTemplate,
)

NOW = datetime.now(timezone.utc)
random.seed(42)

# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------

PEOPLE = ["张三", "李四", "王五", "赵六", "陈晨", "刘洋", "Anna", "Dmitry"]
CITIES = [
    "Moscow", "Saint Petersburg", "Vladivostok", "Novosibirsk", "Kazan",
    "Yekaterinburg", "Krasnodar", "Rostov-on-Don", "Samara", "Nizhny Novgorod",
]
DEALER_NAMES = [
    "Avto Premium Moscow", "Siberia Motors", "VladAuto Trade", "Nevsky Auto Dealer",
    "Kazan Auto Import", "Ural Used Cars", "Far East Motors", "Volga Auto Center",
    "Rostov Car Market", "Krasnodar Drive", "AutoLine SPB", "Moscow Fleet Cars",
    "Novosibirsk AutoHub", "Drom Dealer Vlad", "Prime Cars Kazan", "East Import Auto",
    "Auto Selection RU", "Dealer Garage Media", "Auto Parts Service RU",
    "Classic Motors Watch",
]


# ---------------------------------------------------------------------------
# Channel Risk Rules (20)
# ---------------------------------------------------------------------------

CHANNEL_RISK_RULES = [
    {
        "channel_name": "官网",
        "channel_type": "公开网页",
        "risk_level": ChannelRiskLevel.LOW,
        "collection_allowed": True,
        "ai_processing_allowed": True,
        "allowed_actions": "read_public_page;extract_business_contact;capture_limited_evidence",
        "forbidden_actions": "login;scrape_full_site;auto_form_bomb;high_frequency_access",
        "policy_source_url": "客户官网 Terms/Privacy/Contact 页面;robots.txt",
        "notes": "标准公开网页采集,优先记录邮箱和电话",
    },
    {
        "channel_name": "公开目录",
        "channel_type": "公开目录",
        "risk_level": ChannelRiskLevel.LOW,
        "collection_allowed": True,
        "ai_processing_allowed": True,
        "allowed_actions": "read_public_page;record_business_name;record_public_contact",
        "forbidden_actions": "scrape_non_public_member;bulk_harassment",
        "policy_source_url": "目录网站 Terms/Privacy 页面",
        "notes": "企业目录公开信息采集",
    },
    {
        "channel_name": "搜索引擎",
        "channel_type": "搜索结果",
        "risk_level": ChannelRiskLevel.LOW,
        "collection_allowed": True,
        "ai_processing_allowed": True,
        "allowed_actions": "keyword_search;open_public_result;record_source_link",
        "forbidden_actions": "scrape_search_pages;evade_search_limits;save_no_source_results",
        "policy_source_url": "搜索引擎服务条款和结果页来源网站条款",
        "notes": "关键词搜索公开结果",
    },
    {
        "channel_name": "Google 地图结果",
        "channel_type": "地图标注",
        "risk_level": ChannelRiskLevel.MEDIUM,
        "collection_allowed": True,
        "ai_processing_allowed": True,
        "allowed_actions": "view_public_card;record_official_site;keep_maps_link",
        "forbidden_actions": "bulk_scrape_maps;offline_copy;evade_api_quota;bulk_save_reviews",
        "policy_source_url": "https://cloud.google.com/maps-platform/terms",
        "notes": "公开商户卡片信息采集",
    },
    {
        "channel_name": "Yandex 地图结果",
        "channel_type": "地图标注",
        "risk_level": ChannelRiskLevel.MEDIUM,
        "collection_allowed": True,
        "ai_processing_allowed": True,
        "allowed_actions": "view_public_card;record_official_site_and_phone;keep_yandex_maps_link",
        "forbidden_actions": "bulk_scrape;evade_limits;copy_maps_database;high_frequency",
        "policy_source_url": "https://www.yandex.ru/legal/maps_termsofuse/en/",
        "notes": "Yandex 地图公开商户信息",
    },
    {
        "channel_name": "YouTube",
        "channel_type": "公开社媒/视频",
        "risk_level": ChannelRiskLevel.MEDIUM,
        "collection_allowed": True,
        "ai_processing_allowed": True,
        "allowed_actions": "view_public_video;read_channel_description;record_official_site",
        "forbidden_actions": "auto_comment;auto_dm;bulk_subscribe;scrape_comments;evade_api",
        "policy_source_url": "https://www.youtube.com/t/terms",
        "notes": "公开视频和频道信息",
    },
    {
        "channel_name": "Telegram",
        "channel_type": "公开频道/通讯工具",
        "risk_level": ChannelRiskLevel.HIGH,
        "collection_allowed": False,
        "ai_processing_allowed": False,
        "allowed_actions": "policy_research;view_public_channel_bio;record_official_site",
        "forbidden_actions": "auto_dm;auto_join_group;bulk_broadcast;scrape_private_group;harassment",
        "policy_source_url": "https://telegram.org/tos",
        "notes": "仅政策研究,不进入自动化任务",
    },
    {
        "channel_name": "X",
        "channel_type": "公开社媒",
        "risk_level": ChannelRiskLevel.HIGH,
        "collection_allowed": False,
        "ai_processing_allowed": False,
        "allowed_actions": "policy_research;find_official_site_via_public_profile",
        "forbidden_actions": "browser_automation;auto_follow;auto_dm;bulk_interact;evade_api",
        "policy_source_url": "https://docs.x.com/developer-terms/policy",
        "notes": "仅政策研究,禁止自动化采集",
    },
    {
        "channel_name": "Facebook/Instagram",
        "channel_type": "公开社媒",
        "risk_level": ChannelRiskLevel.HIGH,
        "collection_allowed": False,
        "ai_processing_allowed": False,
        "allowed_actions": "policy_research;view_public_page;record_official_site",
        "forbidden_actions": "auto_scrape;auto_dm;auto_friend_request;unauthorized_data_collection",
        "policy_source_url": "https://www.facebook.com/legal/automated_data_collection_terms",
        "notes": "仅政策研究,禁止自动化采集",
    },
    {
        "channel_name": "Avito",
        "channel_type": "平台市场",
        "risk_level": ChannelRiskLevel.HIGH,
        "collection_allowed": False,
        "ai_processing_allowed": False,
        "allowed_actions": "policy_research;manual_small_sample_view;record_official_site",
        "forbidden_actions": "login_bulk_scrape;auto_contact_seller;evade_risk_control;scrape_non_public",
        "policy_source_url": "Avito 官方规则/用户协议",
        "notes": "仅政策研究和人工小样本",
    },
    {
        "channel_name": "VK",
        "channel_type": "公开社媒",
        "risk_level": ChannelRiskLevel.HIGH,
        "collection_allowed": False,
        "ai_processing_allowed": False,
        "allowed_actions": "policy_research;view_public_page;record_official_site",
        "forbidden_actions": "auto_dm;auto_friend_request;login_bulk_scrape;scrape_non_public",
        "policy_source_url": "VK Terms/API 文档",
        "notes": "仅政策研究,禁止自动化采集",
    },
    {
        "channel_name": "Auto.ru",
        "channel_type": "平台市场",
        "risk_level": ChannelRiskLevel.HIGH,
        "collection_allowed": False,
        "ai_processing_allowed": False,
        "allowed_actions": "policy_research;manual_small_sample_view;keep_source_link",
        "forbidden_actions": "robot_bulk_scrape;copy_database;auto_contact;evade_limits",
        "policy_source_url": "https://yandex.ru/legal/autoru_terms_of_service/ru/",
        "notes": "仅政策研究和人工小样本",
    },
    {
        "channel_name": "Drom",
        "channel_type": "平台市场/论坛",
        "risk_level": ChannelRiskLevel.MEDIUM,
        "collection_allowed": True,
        "ai_processing_allowed": True,
        "allowed_actions": "view_public_merchant_page;record_official_site_and_contact",
        "forbidden_actions": "bulk_scrape;auto_contact;scrape_login_content;evade_limits",
        "policy_source_url": "Drom 官方条款",
        "notes": "公开商户页和公开帖信息",
    },
    {
        "channel_name": "本地行业协会",
        "channel_type": "公开目录",
        "risk_level": ChannelRiskLevel.LOW,
        "collection_allowed": True,
        "ai_processing_allowed": True,
        "allowed_actions": "view_public_member_list;record_official_site;record_public_contact",
        "forbidden_actions": "scrape_non_public_member;bulk_harassment",
        "policy_source_url": "协会官网 Terms/Privacy 页面",
        "notes": "公开会员名单信息",
    },
    {
        "channel_name": "进口商官网",
        "channel_type": "公开网页",
        "risk_level": ChannelRiskLevel.LOW,
        "collection_allowed": True,
        "ai_processing_allowed": True,
        "allowed_actions": "read_public_page;record_public_contact;ai_process_copied_text",
        "forbidden_actions": "auto_form_bomb;bulk_email;scrape_login_area",
        "policy_source_url": "进口商官网 Terms/Privacy 页面",
        "notes": "进口商公开信息,可 AI 处理",
    },
    {
        "channel_name": "公开论坛",
        "channel_type": "公开论坛",
        "risk_level": ChannelRiskLevel.MEDIUM,
        "collection_allowed": True,
        "ai_processing_allowed": True,
        "allowed_actions": "view_public_post;record_official_site;record_public_business_contact",
        "forbidden_actions": "auto_register;auto_post;scrape_login_content;bulk_dm",
        "policy_source_url": "论坛 Terms/Rules 页面",
        "notes": "公开帖和商务信息",
    },
    {
        "channel_name": "汽车媒体",
        "channel_type": "公开网页",
        "risk_level": ChannelRiskLevel.MEDIUM,
        "collection_allowed": True,
        "ai_processing_allowed": True,
        "allowed_actions": "view_public_article;record_interview_site;record_public_business_info",
        "forbidden_actions": "scrape_non_public;auto_comment;copy_paid_content",
        "policy_source_url": "媒体网站 Terms/Privacy 页面",
        "notes": "公开报道中的商务信息",
    },
    {
        "channel_name": "WhatsApp",
        "channel_type": "通讯工具",
        "risk_level": ChannelRiskLevel.HIGH,
        "collection_allowed": False,
        "ai_processing_allowed": False,
        "allowed_actions": "record_customer_provided_business_number;no_auto_add",
        "forbidden_actions": "auto_add_contact;bulk_broadcast;unauthorized_outreach;bulk_harassment",
        "policy_source_url": "https://www.whatsapp.com/legal/business-policy",
        "notes": "仅记录客户主动公开的商务号码",
    },
    {
        "channel_name": "微信",
        "channel_type": "通讯工具",
        "risk_level": ChannelRiskLevel.HIGH,
        "collection_allowed": False,
        "ai_processing_allowed": False,
        "allowed_actions": "manual_add_after_c_level_provides;manual_follow_up_only",
        "forbidden_actions": "auto_add_friend;bulk_group;broadcast;purchase_abnormal_account",
        "policy_source_url": "企业内部微信使用规范",
        "notes": "C 级客户主动提供后人工添加",
    },
    {
        "channel_name": "线下展会名录",
        "channel_type": "公开目录",
        "risk_level": ChannelRiskLevel.LOW,
        "collection_allowed": True,
        "ai_processing_allowed": True,
        "allowed_actions": "view_public_exhibitor_list;record_official_site;record_public_business_contact",
        "forbidden_actions": "scrape_non_public_attendee;bulk_harassment",
        "policy_source_url": "展会官网 Terms/Privacy 页面",
        "notes": "公开参展商信息",
    },
]


# ---------------------------------------------------------------------------
# Channel Plans (20)
# ---------------------------------------------------------------------------

CHANNEL_PLANS = [
    {"country": "Russia", "city": "Moscow", "channel_name": "官网", "risk_level": ChannelRiskLevel.LOW, "keywords": ["used cars dealer Russia", "дилер подержанных автомобилей"], "daily_url_limit": 20, "daily_lead_limit": 10},
    {"country": "Russia", "city": "Moscow", "channel_name": "搜索引擎", "risk_level": ChannelRiskLevel.LOW, "keywords": ["дилер подержанных автомобилей", "used car dealer Moscow"], "daily_url_limit": 15, "daily_lead_limit": 8},
    {"country": "Russia", "city": "Moscow", "channel_name": "Google 地图结果", "risk_level": ChannelRiskLevel.MEDIUM, "keywords": ["used car dealer Moscow", "car dealer"], "daily_url_limit": 10, "daily_lead_limit": 5},
    {"country": "Russia", "city": "Saint Petersburg", "channel_name": "官网", "risk_level": ChannelRiskLevel.LOW, "keywords": ["автодилер Санкт-Петербург", "used cars SPb"], "daily_url_limit": 15, "daily_lead_limit": 8},
    {"country": "Russia", "city": "Saint Petersburg", "channel_name": "Yandex 地图结果", "risk_level": ChannelRiskLevel.MEDIUM, "keywords": ["автосалон бу", "авто дилер"], "daily_url_limit": 10, "daily_lead_limit": 5},
    {"country": "Russia", "city": "Vladivostok", "channel_name": "官网", "risk_level": ChannelRiskLevel.LOW, "keywords": ["автодилер Владивосток", "used cars Vladivostok"], "daily_url_limit": 10, "daily_lead_limit": 5},
    {"country": "Russia", "city": "Vladivostok", "channel_name": "Drom", "risk_level": ChannelRiskLevel.MEDIUM, "keywords": ["автосалон drom", "drom dealer"], "daily_url_limit": 8, "daily_lead_limit": 4},
    {"country": "Russia", "city": "Novosibirsk", "channel_name": "搜索引擎", "risk_level": ChannelRiskLevel.LOW, "keywords": ["автодилер Новосибирск", "used car dealer Novosibirsk"], "daily_url_limit": 10, "daily_lead_limit": 5},
    {"country": "Russia", "city": "Novosibirsk", "channel_name": "公开目录", "risk_level": ChannelRiskLevel.LOW, "keywords": ["автосалон", "каталог автодилеров"], "daily_url_limit": 10, "daily_lead_limit": 5},
    {"country": "Russia", "city": "Kazan", "channel_name": "官网", "risk_level": ChannelRiskLevel.LOW, "keywords": ["автодилер Казань", "used car Kazan"], "daily_url_limit": 8, "daily_lead_limit": 4},
    {"country": "Russia", "city": "Yekaterinburg", "channel_name": "搜索引擎", "risk_level": ChannelRiskLevel.LOW, "keywords": ["автодилер Екатеринбург", "used cars Yekaterinburg"], "daily_url_limit": 8, "daily_lead_limit": 4},
    {"country": "Russia", "city": "Krasnodar", "channel_name": "官网", "risk_level": ChannelRiskLevel.LOW, "keywords": ["автосалон Краснодар", "used cars Krasnodar"], "daily_url_limit": 8, "daily_lead_limit": 4},
    {"country": "Russia", "city": "Rostov-on-Don", "channel_name": "搜索引擎", "risk_level": ChannelRiskLevel.LOW, "keywords": ["автодилер Ростов", "used car dealer Rostov"], "daily_url_limit": 8, "daily_lead_limit": 4},
    {"country": "Russia", "city": "Samara", "channel_name": "YouTube", "risk_level": ChannelRiskLevel.MEDIUM, "keywords": ["обзор авто дилер", "авто из Китая дилер"], "daily_url_limit": 5, "daily_lead_limit": 3},
    {"country": "Russia", "city": "Nizhny Novgorod", "channel_name": "公开论坛", "risk_level": ChannelRiskLevel.MEDIUM, "keywords": ["used car dealer forum", "авто форум дилер"], "daily_url_limit": 5, "daily_lead_limit": 3},
    {"country": "Russia", "city": "Moscow", "channel_name": "汽车媒体", "risk_level": ChannelRiskLevel.MEDIUM, "keywords": ["dealer interview Russia", "интервью автодилер"], "daily_url_limit": 5, "daily_lead_limit": 3},
    {"country": "Russia", "city": "Moscow", "channel_name": "本地行业协会", "risk_level": ChannelRiskLevel.LOW, "keywords": ["auto association dealer list", "ассоциация автодилеров"], "daily_url_limit": 5, "daily_lead_limit": 3},
    {"country": "Russia", "city": "Moscow", "channel_name": "进口商官网", "risk_level": ChannelRiskLevel.LOW, "keywords": ["import cars from China Russia", "импорт авто из Китая"], "daily_url_limit": 10, "daily_lead_limit": 5},
    {"country": "Russia", "city": "Vladivostok", "channel_name": "线下展会名录", "risk_level": ChannelRiskLevel.LOW, "keywords": ["auto expo exhibitor list", "автосалон выставка"], "daily_url_limit": 5, "daily_lead_limit": 3},
    {"country": "Kazakhstan", "city": "Almaty", "channel_name": "搜索引擎", "risk_level": ChannelRiskLevel.LOW, "keywords": ["автодилер Алматы", "used car dealer Almaty"], "daily_url_limit": 8, "daily_lead_limit": 4},
]


# ---------------------------------------------------------------------------
# Customers (20)
# ---------------------------------------------------------------------------

CUSTOMER_GRADES = ["A", "B", "B", "C", "Invalid", "Watch"]
CUSTOMER_TYPES = [
    CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
    CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
    CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
    CustomerType.PERSONAL_BUYER,
    CustomerType.KOL_AUTO_BLOGGER,
    CustomerType.NON_TARGET,
    CustomerType.UNKNOWN,
]
STATUS_BY_GRADE = {
    "A": [CustomerStatus.NEW, CustomerStatus.NEEDS_ENRICHMENT, CustomerStatus.PENDING_REVIEW],
    "B": [CustomerStatus.PENDING_REVIEW, CustomerStatus.READY_FOR_CUSTOMER_SERVICE, CustomerStatus.CUSTOMER_SERVICE_FOLLOWING],
    "C": [CustomerStatus.READY_FOR_SALES, CustomerStatus.SALES_FOLLOWING],
    "Invalid": [CustomerStatus.INVALID],
    "Watch": [CustomerStatus.WATCH],
}
PLATFORM_MAP = {
    "官网": SourcePlatform.OFFICIAL_WEBSITE,
    "搜索引擎": SourcePlatform.SEARCH_ENGINE,
    "地图": SourcePlatform.GOOGLE_MAPS,
    "公开目录": SourcePlatform.PUBLIC_DIRECTORY,
    "YouTube": SourcePlatform.YOUTUBE,
    "Drom": SourcePlatform.DROM,
}
CONTACT_PLATFORMS = ["官网", "搜索引擎", "地图", "公开目录", "YouTube", "Drom"]


# ---------------------------------------------------------------------------
# Inventory (20)
# ---------------------------------------------------------------------------

INVENTORY_DATA = [
    {"brand": "Toyota", "model": "Land Cruiser Prado", "year": 2022, "mileage_km": 18000, "condition_summary": "准新车", "configuration": "2.7L, 4WD, leather"},
    {"brand": "Toyota", "model": "Camry", "year": 2021, "mileage_km": 42000, "condition_summary": "二手车", "configuration": "2.5L, hybrid, comfort"},
    {"brand": "Nissan", "model": "X-Trail", "year": 2020, "mileage_km": 51000, "condition_summary": "二手车", "configuration": "2.0L, AWD"},
    {"brand": "Lexus", "model": "RX 350", "year": 2021, "mileage_km": 28000, "condition_summary": "准新车", "configuration": "premium package"},
    {"brand": "Mitsubishi", "model": "Pajero Sport", "year": 2019, "mileage_km": 76000, "condition_summary": "二手车", "configuration": "diesel, 4WD"},
    {"brand": "Honda", "model": "CR-V", "year": 2022, "mileage_km": 22000, "condition_summary": "准新车", "configuration": "hybrid, AWD"},
    {"brand": "Mazda", "model": "CX-5", "year": 2021, "mileage_km": 34000, "condition_summary": "二手车", "configuration": "2.5L, AWD"},
    {"brand": "Hyundai", "model": "Santa Fe", "year": 2020, "mileage_km": 59000, "condition_summary": "二手车", "configuration": "diesel, 7 seats"},
    {"brand": "Kia", "model": "Sorento", "year": 2021, "mileage_km": 39000, "condition_summary": "二手车", "configuration": "2.2 diesel"},
    {"brand": "Mercedes-Benz", "model": "GLE 350", "year": 2020, "mileage_km": 47000, "condition_summary": "二手车", "configuration": "premium SUV"},
    {"brand": "BMW", "model": "X5", "year": 2021, "mileage_km": 36000, "condition_summary": "二手车", "configuration": "xDrive, M package"},
    {"brand": "Audi", "model": "Q7", "year": 2020, "mileage_km": 62000, "condition_summary": "二手车", "configuration": "quattro, 7 seats"},
    {"brand": "Volkswagen", "model": "Tiguan", "year": 2022, "mileage_km": 24000, "condition_summary": "准新车", "configuration": "2.0 TSI"},
    {"brand": "Skoda", "model": "Kodiaq", "year": 2021, "mileage_km": 41000, "condition_summary": "二手车", "configuration": "7 seats"},
    {"brand": "Geely", "model": "Monjaro", "year": 2023, "mileage_km": 8000, "condition_summary": "库存车", "configuration": "2.0T, AWD"},
    {"brand": "Chery", "model": "Tiggo 8 Pro", "year": 2023, "mileage_km": 6000, "condition_summary": "库存车", "configuration": "1.6T, 7 seats"},
    {"brand": "Haval", "model": "Dargo", "year": 2023, "mileage_km": 9000, "condition_summary": "库存车", "configuration": "2.0T, AWD"},
    {"brand": "BYD", "model": "Song Plus", "year": 2023, "mileage_km": 12000, "condition_summary": "准新车", "configuration": "PHEV"},
    {"brand": "Zeekr", "model": "001", "year": 2023, "mileage_km": 5000, "condition_summary": "准新车", "configuration": "EV, long range"},
    {"brand": "Toyota", "model": "Hiace", "year": 2020, "mileage_km": 68000, "condition_summary": "二手车", "configuration": "commercial van"},
]


# ---------------------------------------------------------------------------
# Script Templates (20)
# ---------------------------------------------------------------------------

SCRIPT_TYPES = ["初次触达", "价格FAQ", "车况FAQ", "物流FAQ", "付款FAQ", "合作模式FAQ", "拒绝联系回复", "其他"]

SCRIPT_DATA = [
    {
        "name": "RU-V1-B级初触达-1",
        "script_type": "初次触达",
        "applicable_grades": "B;C",
        "applicable_channels": "EMAIL;WEBSITE_FORM",
        "chinese_internal_text": "用于初次触达场景,先确认客户是否有采购二手车、准新车或库存车需求,不做价格和交付承诺。",
        "russian_customer_text": "Здравствуйте! Мы изучаем возможность сотрудничества по поставкам автомобилей. Если вам не интересно, пожалуйста, сообщите нам, и мы больше не будем вас беспокоить.",
        "forbidden_promises": "最终价格;物流时效;清关结果;付款安全;交付周期",
        "opt_out_path": "如不方便联系,请回复 stop 或 сообщите, пожалуйста, если не хотите получать сообщения.",
    },
    {
        "name": "RU-V1-B级初触达-2",
        "script_type": "初次触达",
        "applicable_grades": "B",
        "applicable_channels": "EMAIL",
        "chinese_internal_text": "B 级客户初次触达,确认二手车采购意向。",
        "russian_customer_text": "Добрый день! Наша компания специализируется на поставках автомобилей из Китая. Мы хотели бы узнать, заинтересованы ли вы в сотрудничестве. Если нет — просто сообщите, и мы не будем вас беспокоить.",
        "forbidden_promises": "最终价格;物流时效;清关结果;付款安全;交付周期",
        "opt_out_path": "Пожалуйста, напишите \"стоп\", если вы не хотите получать сообщения.",
    },
    {
        "name": "RU-V1-价格FAQ-3",
        "script_type": "价格FAQ",
        "applicable_grades": "B;C",
        "applicable_channels": "EMAIL;WEBSITE_FORM",
        "chinese_internal_text": "客户询问价格时的标准回复,不承诺具体价格,引导提供需求详情。",
        "russian_customer_text": "Спасибо за ваш интерес! Точная цена зависит от модели, комплектации и срока поставки. Пожалуйста, уточните, какие модели вас интересуют, и мы подготовим предложение.",
        "forbidden_promises": "最终价格;交付周期",
        "opt_out_path": "Если у вас нет потребности в закупке автомобилей, пожалуйста, сообщите нам.",
    },
    {
        "name": "RU-V1-车况FAQ-4",
        "script_type": "车况FAQ",
        "applicable_grades": "B",
        "applicable_channels": "EMAIL",
        "chinese_internal_text": "客户询问车况时的标准回复。",
        "russian_customer_text": "Все автомобили проходят предпоставочную проверку. Мы предоставляем отчёт о состоянии, фото и описание комплектации для каждого автомобиля.",
        "forbidden_promises": "最终价格;交付周期",
        "opt_out_path": "Если вопрос снят, дайте знать.",
    },
    {
        "name": "RU-V1-物流FAQ-5",
        "script_type": "物流FAQ",
        "applicable_grades": "B;C",
        "applicable_channels": "EMAIL;WEBSITE_FORM",
        "chinese_internal_text": "客户询问物流时效的回复,不承诺具体时效。",
        "russian_customer_text": "Сроки доставки зависят от маршрута и текущей загруженности. Мы можем обсудить варианты после уточнения ваших потребностей.",
        "forbidden_promises": "最终价格;物流时效;清关结果;交付周期",
        "opt_out_path": "Если больше не заинтересованы, пожалуйста, дайте знать.",
    },
    {
        "name": "RU-V1-付款FAQ-6",
        "script_type": "付款FAQ",
        "applicable_grades": "B;C",
        "applicable_channels": "EMAIL",
        "chinese_internal_text": "客户询问付款方式的回复,不承诺付款安全。",
        "russian_customer_text": "У нас есть несколько вариантов оплаты. Мы можем обсудить детали, когда будете готовы к следующим шагам.",
        "forbidden_promises": "最终价格;付款安全;清关结果",
        "opt_out_path": "Пожалуйста, сообщите, если хотите прекратить общение.",
    },
    {
        "name": "RU-V1-合作模式FAQ-7",
        "script_type": "合作模式FAQ",
        "applicable_grades": "C",
        "applicable_channels": "EMAIL;WEBSITE_FORM",
        "chinese_internal_text": "C 级客户合作模式讨论,交付销售跟进。",
        "russian_customer_text": "Мы предлагаем гибкие условия сотрудничества для дилеров. Давайте обсудим, какой формат подходит вашей компании.",
        "forbidden_promises": "最终价格;物流时效;清关结果;付款安全;交付周期",
        "opt_out_path": "Если не заинтересованы, пожалуйста, напишите нам.",
    },
    {
        "name": "RU-V1-拒绝联系回复-8",
        "script_type": "拒绝联系回复",
        "applicable_grades": "B;C",
        "applicable_channels": "EMAIL;WEBSITE_FORM",
        "chinese_internal_text": "客户拒绝联系时的标准回复,确认勿扰标记。",
        "russian_customer_text": "Понятно, спасибо за ответ. Мы больше не будем вас беспокоить. Если в будущем вам потребуется сотрудничество, вы всегда можете связаться с нами.",
        "forbidden_promises": "",
        "opt_out_path": "已确认拒绝,标记勿扰。",
    },
    {
        "name": "RU-V1-初次触达-9",
        "script_type": "初次触达",
        "applicable_grades": "B",
        "applicable_channels": "EMAIL",
        "chinese_internal_text": "标准初次触达,确认采购意向。",
        "russian_customer_text": "Здравствуйте! Наша компания поставляет автомобили из Китая. Мы будем рады обсудить возможное сотрудничество. Если вам не интересно — просто сообщите.",
        "forbidden_promises": "最终价格;物流时效;清关结果;付款安全;交付周期",
        "opt_out_path": "Напишите \"стоп\", чтобы отказаться от рассылки.",
    },
    {
        "name": "RU-V2-C级需求确认-10",
        "script_type": "初次触达",
        "applicable_grades": "C",
        "applicable_channels": "EMAIL",
        "chinese_internal_text": "C 级客户需求确认,已有回复信号。",
        "russian_customer_text": "Добрый день! Спасибо за ваш ответ. Мы готовы обсудить детали поставки автомобилей. Какие модели и объёмы вас интересуют?",
        "forbidden_promises": "最终价格;物流时效;清关结果;付款安全;交付周期",
        "opt_out_path": "Если вопрос уже не актуален, дайте знать.",
    },
    {
        "name": "RU-V2-价格FAQ-11",
        "script_type": "价格FAQ",
        "applicable_grades": "C",
        "applicable_channels": "EMAIL;WEBSITE_FORM",
        "chinese_internal_text": "C 级客户价格追问,引导提供需求详情。",
        "russian_customer_text": "Благодарим за интерес! Цена зависит от модели и комплектации. Уточните ваши потребности, и мы подготовим индивидуальное предложение.",
        "forbidden_promises": "最终价格;交付周期",
        "opt_out_path": "Если тема закрыта, сообщите.",
    },
    {
        "name": "RU-V2-车况FAQ-12",
        "script_type": "车况FAQ",
        "applicable_grades": "B;C",
        "applicable_channels": "EMAIL",
        "chinese_internal_text": "车况详情回复。",
        "russian_customer_text": "Мы предоставляем полную информацию о состоянии каждого автомобиля, включая фото, пробег и историю обслуживания.",
        "forbidden_promises": "最终价格;交付周期",
        "opt_out_path": "Пожалуйста, сообщите, если хотите прекратить общение.",
    },
    {
        "name": "RU-V2-物流FAQ-13",
        "script_type": "物流FAQ",
        "applicable_grades": "B;C",
        "applicable_channels": "EMAIL",
        "chinese_internal_text": "物流询问回复,不承诺时效。",
        "russian_customer_text": "Доставка осуществляется в зависимости от расположения. Конкретные сроки обсудим после подтверждения заказа.",
        "forbidden_promises": "物流时效;清关结果;交付周期",
        "opt_out_path": "Если неактуально, дайте знать.",
    },
    {
        "name": "RU-V2-付款FAQ-14",
        "script_type": "付款FAQ",
        "applicable_grades": "C",
        "applicable_channels": "EMAIL",
        "chinese_internal_text": "C 级付款方式讨论。",
        "russian_customer_text": "Мы рассмотрим варианты оплаты после согласования деталей сотрудничества.",
        "forbidden_promises": "付款安全;清关结果;最终价格",
        "opt_out_path": "Если больше не заинтересованы, напишите нам.",
    },
    {
        "name": "RU-V2-合作模式FAQ-15",
        "script_type": "合作模式FAQ",
        "applicable_grades": "B;C",
        "applicable_channels": "EMAIL;WEBSITE_FORM",
        "chinese_internal_text": "合作模式讨论。",
        "russian_customer_text": "Мы открыты к различным форматам сотрудничества — от разовых поставок до долгосрочных контрактов.",
        "forbidden_promises": "最终价格;物流时效;清关结果;付款安全;交付周期",
        "opt_out_path": "Если неактуально, дайте знать.",
    },
    {
        "name": "RU-V2-拒绝联系回复-16",
        "script_type": "拒绝联系回复",
        "applicable_grades": "B;C",
        "applicable_channels": "EMAIL",
        "chinese_internal_text": "拒绝联系确认。",
        "russian_customer_text": "Спасибо за ответ. Мы удалили ваш контакт из списка рассылки. При необходимости вы всегда можете связаться с нами.",
        "forbidden_promises": "",
        "opt_out_path": "已确认拒绝,标记勿扰。",
    },
    {
        "name": "RU-V2-初次触达-17",
        "script_type": "初次触达",
        "applicable_grades": "B",
        "applicable_channels": "EMAIL;WEBSITE_FORM",
        "chinese_internal_text": "标准 B 级初次触达模板。",
        "russian_customer_text": "Здравствуйте! Мы изучаем возможности сотрудничества по поставкам автомобилей с пробегом, почти новых и складских автомобилей. Если вам интересно, пожалуйста, сообщите.",
        "forbidden_promises": "最终价格;物流时效;清关结果;付款安全;交付周期",
        "opt_out_path": "Если вам не интересно, просто напишите \"стоп\".",
    },
    {
        "name": "RU-V3-C级需求确认-18",
        "script_type": "初次触达",
        "applicable_grades": "C",
        "applicable_channels": "EMAIL",
        "chinese_internal_text": "C 级客户二次跟进。",
        "russian_customer_text": "Добрый день! Мы хотели бы вернуться к нашему обсуждению о поставках автомобилей. Если ваше решение изменилось, будем рады сотрудничеству.",
        "forbidden_promises": "最终价格;物流时效;清关结果;付款安全;交付周期",
        "opt_out_path": "Если неактуально, просто напишите нам.",
    },
    {
        "name": "RU-V3-价格FAQ-19",
        "script_type": "价格FAQ",
        "applicable_grades": "C",
        "applicable_channels": "EMAIL",
        "chinese_internal_text": "C 级价格追问跟进。",
        "russian_customer_text": "Мы готовим для вас индивидуальное предложение. Как только будет готово, мы направим его на ваш email.",
        "forbidden_promises": "最终价格;交付周期",
        "opt_out_path": "Если тема закрыта, дайте знать.",
    },
    {
        "name": "RU-V3-其他-20",
        "script_type": "其他",
        "applicable_grades": "B;C",
        "applicable_channels": "EMAIL",
        "chinese_internal_text": "通用回复模板。",
        "russian_customer_text": "Спасибо за ваше обращение! Мы рассмотрим ваш запрос и ответим в ближайшее время.",
        "forbidden_promises": "最终价格;物流时效;清关结果;付款安全;交付周期",
        "opt_out_path": "Если хотите прекратить общение, сообщите, пожалуйста.",
    },
]

SCRIPT_REVIEW_STATUSES = [
    ScriptReviewStatus.DRAFT,
    ScriptReviewStatus.BUSINESS_REVIEW,
    ScriptReviewStatus.COMPLIANCE_REVIEW,
    ScriptReviewStatus.APPROVED_FOR_EXTERNAL_USE,
    ScriptReviewStatus.DISABLED,
]


# ---------------------------------------------------------------------------
# Knowledge Collections & Items (6 collections)
# ---------------------------------------------------------------------------

KNOWLEDGE_COLLECTIONS = [
    {"name": "keyword_library", "description": "搜索关键词库,用于公开渠道发现目标客户"},
    {"name": "channel_sop", "description": "渠道标准操作流程,定义各渠道允许/禁止的动作"},
    {"name": "compliance_rules", "description": "合规规则集,硬规则边界和红线约束"},
    {"name": "failed_cases", "description": "失败案例库,可用于 RAG 上下文避免重复错误"},
    {"name": "faq", "description": "常见问题和标准回复,用于触达草稿生成"},
    {"name": "script_template", "description": "话术模板库,用于生成俄语触达内容"},
]

KNOWLEDGE_ITEMS = [
    # keyword_library
    {"collection": "keyword_library", "title": "俄语二手车经销商搜索关键词", "body": "дилер подержанных автомобилей, автосалон б/у, used car dealer Russia, купить авто с пробегом, автомобили с пробегом дилер, б/у автомобили Москва, подержанные авто дилер, автодилер бу", "language": "ru", "country": "Russia"},
    {"collection": "keyword_library", "title": "英语二手车经销商搜索关键词", "body": "used car dealer Russia, second hand car dealer Moscow, pre-owned vehicle dealer, car dealership Russia, import cars from China, Chinese vehicles dealer", "language": "en", "country": "Russia"},
    {"collection": "keyword_library", "title": "中国品牌车辆关键词", "body": "Geely, Chery, Haval, BYD, Great Wall, Changan, Exeed, Jetour, Omoda, Zeekr, Lynk & Co, китайские автомобили, авто из Китая", "language": "zh", "country": "Russia"},

    # channel_sop
    {"collection": "channel_sop", "title": "Low 风险渠道采集 SOP", "body": "Low 风险渠道(官网、搜索引擎、公开目录)允许: read_public_page, extract_business_contact, capture_limited_evidence。每日 URL 上限 20, 每日 Lead 上限 10。必须记录来源 URL 和证据文本。", "language": "zh", "country": "Russia"},
    {"collection": "channel_sop", "title": "Medium 风险渠道采集 SOP", "body": "Medium 风险渠道(地图、YouTube、Drom、公开论坛、汽车媒体)允许人工查看公开信息,记录官网和公开联系方式。不自动联系,不批量采集。每日 URL 上限 10。", "language": "zh", "country": "Russia"},
    {"collection": "channel_sop", "title": "High 风险渠道处理 SOP", "body": "High 风险渠道(Telegram, X, Facebook/Instagram, VK, Avito, Auto.ru, WhatsApp, 微信)仅允许政策研究和人工小样本。禁止进入自动化采集任务。禁止自动私信、加好友、批量互动。", "language": "zh", "country": "Russia"},

    # compliance_rules
    {"collection": "compliance_rules", "title": "禁止承诺清单", "body": "在任何对外沟通中,不得承诺: 最终价格(финальную цену)、物流时效(быструю доставку)、清关结果(таможенное оформление)、付款安全(безопасную оплату)、交付周期(сроки доставки)。违反此规则视为合规事件。", "language": "zh", "country": "Russia"},
    {"collection": "compliance_rules", "title": "触达合规要求", "body": "所有触达必须: 1)仅人工发送(auto_send_enabled=false); 2)包含拒绝联系路径; 3)不承诺交易条件; 4)渠道风险允许; 5)客户未标记勿扰; 6)AI 输入输出已审计; 7)模板状态为可外发。", "language": "zh", "country": "Russia"},
    {"collection": "compliance_rules", "title": "C 级客户合规审核要求", "body": "C 级客户(高意向)必须经过合规审核后才能交付销售。合规审核内容包括: 客户信息真实性验证、联系方式有效性确认、渠道来源合规性检查、过往勿扰记录查询。", "language": "zh", "country": "Russia"},
    {"collection": "compliance_rules", "title": "勿扰(DNC)机制", "body": "客户标记 do_not_contact 后: 不得生成触达草稿、不得记录发送、不得自动跟进。标记原因包括: 客户明确拒绝、联系方式无效且无法补全、非目标客户确认。", "language": "zh", "country": "Russia"},

    # failed_cases
    {"collection": "failed_cases", "title": "非目标业务识别规则", "body": "非目标业务包括: 纯维修/配件服务(无车辆销售)、个人车辆出售(非经销商)、二手车评估/鉴定服务、汽车保险/金融服务。判断依据: 页面主要内容是否包含库存列表或销售信息。", "language": "zh", "country": "Russia"},
    {"collection": "failed_cases", "title": "LLM 编造检测案例", "body": "典型案例: LLM 输出了联系方式(如 email: info@dealer.ru),但该 email 不在原始公开文本中出现。校验逻辑: 所有 contacts 中的 value 必须能在 public_text 中找到子串匹配。", "language": "zh", "country": "Russia"},

    # faq
    {"collection": "faq", "title": "价格相关问题标准回复", "body": "Q: 车多少钱? A: 价格取决于具体车型、配置和当前库存。请告知您感兴趣的具体车型,我们会为您准备详细报价。注意: 不得承诺最终价格。", "language": "zh", "country": "Russia"},
    {"collection": "faq", "title": "物流相关问题标准回复", "body": "Q: 多久能到? A: 交付时间取决于车型、路线和当前物流状况。确认订单后我们会提供预估时间。注意: 不得承诺具体物流时效。", "language": "zh", "country": "Russia"},
    {"collection": "faq", "title": "付款相关问题标准回复", "body": "Q: 怎么付款? A: 我们提供多种付款方式,具体方案在确认订单后讨论。注意: 不得承诺付款安全。", "language": "zh", "country": "Russia"},
    {"collection": "faq", "title": "车况相关问题标准回复", "body": "Q: 车况如何? A: 所有车辆均经过出厂检验,提供详细的车况报告、实拍照片和配置清单。如需更多信息,我们可以安排视频看车。", "language": "zh", "country": "Russia"},

    # script_template
    {"collection": "script_template", "title": "B 级客户初次触达模板", "body": "目标: 确认客户采购意向。语气: 专业、简洁。内容: 介绍公司背景、表达合作意愿、询问采购需求。必须包含拒绝联系路径。适用渠道: Email, 官网表单。", "language": "zh", "country": "Russia"},
    {"collection": "script_template", "title": "C 级客户需求确认模板", "body": "目标: 深入了解采购需求,推进合作。语气: 热情、专业。内容: 回复客户兴趣、询问具体车型和数量、介绍合作方式。必须包含拒绝联系路径。适用渠道: Email。", "language": "zh", "country": "Russia"},
]


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

def seed_channel_risk_rules(session: Session) -> int:
    existing = session.query(ChannelRiskRule).count()
    if existing > 0:
        print(f"  [SKIP] channel_risk_rules: {existing} rows exist")
        return 0
    count = 0
    for i, data in enumerate(CHANNEL_RISK_RULES):
        session.add(ChannelRiskRule(
            id=uuid4(),
            external_id=f"CH-{i+1:04d}",
            updated_by=PEOPLE[i % len(PEOPLE)],
            last_reviewed_at=NOW - timedelta(days=random.randint(1, 30)),
            updated_at=NOW,
            **data,
        ))
        count += 1
    session.flush()
    print(f"  [OK] channel_risk_rules: {count} rows inserted")
    return count


def seed_channel_plans(session: Session) -> int:
    existing = session.query(ChannelPlan).count()
    if existing > 0:
        print(f"  [SKIP] channel_plans: {existing} rows exist")
        return 0
    count = 0
    for i, data in enumerate(CHANNEL_PLANS):
        plan = ChannelPlan(
            id=uuid4(),
            channel_type=data["channel_name"],
            source_usage_type=SourceUsageType.PUBLIC_DISCOVERY_ONLY if data["risk_level"] == ChannelRiskLevel.HIGH else SourceUsageType.AUTOMATIC_COLLECTION,
            status=random.choice([ChannelPlanStatus.ENABLED, ChannelPlanStatus.ENABLED, ChannelPlanStatus.DRAFT]),
            owner=PEOPLE[i % len(PEOPLE)],
            created_at=NOW - timedelta(days=random.randint(1, 30)),
            updated_at=NOW,
        )
        for k, v in data.items():
            setattr(plan, k, v)
        session.add(plan)
        count += 1
    session.flush()
    print(f"  [OK] channel_plans: {count} rows inserted")
    return count


def seed_customers_and_contacts(session: Session) -> int:
    existing = session.query(Customer).count()
    if existing > 0:
        print(f"  [SKIP] customers + contacts + sources: {existing} rows exist")
        return 0
    count = 0
    for i in range(20):
        grade = CustomerGrade(CUSTOMER_GRADES[i % len(CUSTOMER_GRADES)])
        customer_type = CustomerType.NON_TARGET if i == 18 else CUSTOMER_TYPES[i % len(CUSTOMER_TYPES)]
        is_dnc = i == 6 or i == 15
        status = CustomerStatus.DO_NOT_CONTACT if is_dnc else random.choice(STATUS_BY_GRADE[grade.value])
        risk = ChannelRiskLevel.HIGH if i == 13 else (ChannelRiskLevel.MEDIUM if i == 18 else random.choice([ChannelRiskLevel.LOW, ChannelRiskLevel.LOW, ChannelRiskLevel.MEDIUM]))
        platform = CONTACT_PLATFORMS[i % len(CONTACT_PLATFORMS)]
        source_platform = PLATFORM_MAP.get(platform, SourcePlatform.OTHER)
        city = CITIES[i % len(CITIES)]
        name = DEALER_NAMES[i]
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        domain = f"https://{slug or f'dealer-{i+1}'}.example.ru"

        business_types = [
            "used Japanese cars, SUVs",
            "premium used vehicles, sedans",
            "commercial vans and pickup trucks",
            "mixed used car inventory",
        ]
        grade_reasons = {
            "A": "基础信息完整但主营车型需补全",
            "B": "有库存和公开联系方式,建议交付客服",
            "C": "已回复并表达采购兴趣,建议交付出口销售",
            "Invalid": "非目标业务或无有效联系方式",
            "Watch": "信息不足,建议沉淀观察",
        }

        customer = Customer(
            id=uuid4(),
            external_id=f"LEAD-{i+1:04d}",
            name=name,
            country="Russia",
            city=city,
            customer_type=customer_type,
            grade=grade,
            status=status,
            owner=PEOPLE[i % len(PEOPLE)],
            do_not_contact=is_dnc,
            do_not_contact_reason="客户明确拒绝继续联系" if is_dnc else None,
            do_not_contact_marked_by=PEOPLE[i % len(PEOPLE)] if is_dnc else None,
            do_not_contact_marked_at=NOW - timedelta(days=5) if is_dnc else None,
            ai_recommended_grade=grade,
            ai_recommendation_reason=grade_reasons.get(grade.value, "Unknown"),
            missing_fields="主营车型、进口车相关性" if grade == CustomerGrade.A else ("联系方式、业务真实性" if grade == CustomerGrade.WATCH else None),
            created_at=NOW - timedelta(days=random.randint(1, 15)),
            updated_at=NOW,
        )
        session.add(customer)
        session.flush()  # get customer.id
        count += 1

        # Contact methods
        email = f"sales{i+1}@seed-dealer{i+1}.example.ru"
        phone = f"+7 999 {100+i:03d} {2000+i:04d}"
        whatsapp = phone if i % 2 == 0 else None
        telegram = f"@dealer_seed_{i+1}" if i % 4 == 0 else None

        contacts = [
            {"method_type": ContactMethodType.EMAIL, "value": email, "is_primary": True, "is_verified": False},
            {"method_type": ContactMethodType.PHONE, "value": phone, "is_primary": False, "is_verified": False},
        ]
        if whatsapp:
            contacts.append({"method_type": ContactMethodType.WHATSAPP, "value": whatsapp, "is_primary": False, "is_verified": False})
        if telegram:
            contacts.append({"method_type": ContactMethodType.TELEGRAM, "value": telegram, "is_primary": False, "is_verified": False})

        for c in contacts:
            session.add(ContactMethod(
                id=uuid4(),
                customer_id=customer.id,
                source_url=domain,
                evidence_note="Seed data",
                created_at=NOW - timedelta(days=random.randint(1, 10)),
                **c,
            ))

        # Lead source
        session.add(LeadSource(
            id=uuid4(),
            external_id=f"SRC-{i+1:04d}",
            customer_id=customer.id,
            platform=source_platform,
            source_url=domain,
            source_title=f"{name} - 公开页面",
            evidence_note="公开页面展示车辆销售、库存或经销商联系方式" if grade != CustomerGrade.INVALID else "公开页面主要为配件/维修,不符合目标客户",
            channel_risk_level=risk,
            collected_keyword=f"used car dealer {city}".lower(),
            collected_by=PEOPLE[i % len(PEOPLE)],
            collected_at=NOW - timedelta(days=random.randint(1, 15)),
        ))

        # Compliance review for C grade
        if grade == CustomerGrade.C:
            session.add(ComplianceReview(
                id=uuid4(),
                customer_id=customer.id,
                review_type="c_grade_quote_contract",
                status=random.choice([ComplianceReviewStatus.PENDING, ComplianceReviewStatus.APPROVED]),
                reason="C 级客户合规审核",
                reviewer=PEOPLE[(i + 3) % len(PEOPLE)],
                reviewed_at=NOW - timedelta(days=random.randint(0, 5)) if random.random() > 0.5 else None,
                created_at=NOW - timedelta(days=random.randint(1, 10)),
            ))

    session.flush()
    print(f"  [OK] customers: 20 rows, contacts: ~60 rows, sources: 20 rows, compliance: ~3 rows")
    return count


def seed_inventory(session: Session) -> int:
    existing = session.query(InventoryItem).count()
    if existing > 0:
        print(f"  [SKIP] inventory_items: {existing} rows exist")
        return 0
    count = 0
    for i, data in enumerate(INVENTORY_DATA):
        price = 18000 + i * 1850
        quote_status = "pending" if i % 7 != 0 else ("expired" if i % 9 == 0 else "confirmed")
        export_ready = False if i % 10 == 0 else (None if i % 4 == 0 else True)
        session.add(InventoryItem(
            id=uuid4(),
            external_id=f"INV-{i+1:04d}",
            brand=data["brand"],
            model=data["model"],
            year=data["year"],
            mileage_km=data["mileage_km"],
            vehicle_type="SUV" if "SUV" in data.get("configuration", "") or data["brand"] in ("Toyota", "Nissan", "Honda", "Mitsubishi") else "Sedan",
            condition_summary=data["condition_summary"],
            configuration=data["configuration"],
            quoted_price=price,
            currency="USD",
            quote_status=quote_status,
            export_ready=export_ready,
            media_urls=[f"https://seed-inventory.example.com/cars/{i+1:04d}/photo1.jpg"],
            valid_until=NOW + timedelta(days=30 + i),
            source_ref=f"https://seed-inventory.example.com/cars/{i+1:04d}",
            created_at=NOW - timedelta(days=random.randint(1, 20)),
            updated_at=NOW,
        ))
        count += 1
    session.flush()
    print(f"  [OK] inventory_items: {count} rows inserted")
    return count


def seed_outreach_records(session: Session) -> int:
    existing = session.query(OutreachRecord).count()
    if existing > 0:
        print(f"  [SKIP] outreach_records: {existing} rows exist")
        return 0
    customers = session.query(Customer).order_by(Customer.created_at).limit(20).all()
    if not customers:
        print("  [WARN] No customers found, skipping outreach_records")
        return 0
    count = 0
    statuses = [OutreachStatus.DRAFT, OutreachStatus.SENT, OutreachStatus.REPLIED, OutreachStatus.REJECTED, OutreachStatus.NO_RESPONSE, OutreachStatus.BAD_CONTACT]
    channels = [ContactMethodType.EMAIL, ContactMethodType.WEBSITE_FORM, ContactMethodType.PHONE, ContactMethodType.WHATSAPP, ContactMethodType.TELEGRAM]
    for i in range(20):
        customer = customers[i % len(customers)]
        status = statuses[i % len(statuses)]
        is_replied = status == OutreachStatus.REPLIED
        is_rejected = status == OutreachStatus.REJECTED
        is_dnc = is_rejected
        channel = channels[i % len(channels)]
        session.add(OutreachRecord(
            id=uuid4(),
            external_id=f"OUT-{i+1:04d}",
            customer_id=customer.id,
            channel=channel,
            status=status,
            script_version="RU-V1-B级初触达" if i % 2 == 0 else "RU-V1-C级需求确认",
            sent_by=PEOPLE[(i + 3) % len(PEOPLE)] if status != OutreachStatus.DRAFT else None,
            owner=PEOPLE[i % len(PEOPLE)],
            sent_at=NOW - timedelta(days=random.randint(0, 10)) if status != OutreachStatus.DRAFT else None,
            response_summary="客户询问 Toyota SUV 和付款方式" if is_replied else ("客户明确表示暂不需要继续联系" if is_rejected else (None if status == OutreachStatus.DRAFT else "")),
            next_action="升级销售" if is_replied else ("标记勿扰" if is_rejected else "继续跟进"),
            triggers_do_not_contact=is_dnc,
            do_not_contact_reason="客户明确拒绝继续联系" if is_dnc else None,
            created_at=NOW - timedelta(days=random.randint(1, 15)),
        ))
        count += 1
    session.flush()
    print(f"  [OK] outreach_records: {count} rows inserted")
    return count


def seed_script_templates(session: Session) -> int:
    existing = session.query(ScriptTemplate).count()
    if existing > 0:
        print(f"  [SKIP] script_templates: {existing} rows exist")
        return 0
    count = 0
    for i, data in enumerate(SCRIPT_DATA):
        review_status = SCRIPT_REVIEW_STATUSES[i % len(SCRIPT_REVIEW_STATUSES)]
        session.add(ScriptTemplate(
            id=uuid4(),
            external_id=f"SCR-{i+1:04d}",
            version=f"v1.{i}",
            risk_note="AI 只能引用已审核版本,不得自由承诺交易条件",
            reviewer=PEOPLE[i % len(PEOPLE)] if review_status == ScriptReviewStatus.APPROVED_FOR_EXTERNAL_USE else None,
            reviewed_at=NOW - timedelta(days=random.randint(0, 5)) if review_status == ScriptReviewStatus.APPROVED_FOR_EXTERNAL_USE else None,
            created_at=NOW - timedelta(days=random.randint(1, 20)),
            updated_at=NOW,
            review_status=review_status,
            **data,
        ))
        count += 1
    session.flush()
    print(f"  [OK] script_templates: {count} rows inserted")
    return count


def seed_knowledge(session: Session) -> int:
    existing = session.query(KnowledgeCollection).count()
    if existing > 0:
        print(f"  [SKIP] knowledge: {existing} collections exist")
        return 0
    count = 0

    # Collections
    collection_map: dict[str, KnowledgeCollection] = {}
    for col_data in KNOWLEDGE_COLLECTIONS:
        col = KnowledgeCollection(
            id=uuid4(),
            name=col_data["name"],
            description=col_data["description"],
            status=KnowledgeItemStatus.ACTIVE,
            review_status=KnowledgeReviewStatus.APPROVED,
            version="v1",
            created_at=NOW,
            updated_at=NOW,
        )
        session.add(col)
        collection_map[col.name] = col
        count += 1
    session.flush()

    # Items
    for item_data in KNOWLEDGE_ITEMS:
        col_name = item_data.pop("collection")
        col = collection_map[col_name]
        session.add(KnowledgeItem(
            id=uuid4(),
            collection_id=col.id,
            status=KnowledgeItemStatus.ACTIVE,
            review_status=KnowledgeReviewStatus.APPROVED,
            version="v1",
            created_at=NOW,
            updated_at=NOW,
            **item_data,
        ))
        count += 1
    session.flush()
    print(f"  [OK] knowledge: {len(KNOWLEDGE_COLLECTIONS)} collections, {len(KNOWLEDGE_ITEMS)} items")
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_TABLES = {
    "channel_risk_rules": seed_channel_risk_rules,
    "channel_plans": seed_channel_plans,
    "customers": seed_customers_and_contacts,
    "inventory": seed_inventory,
    "outreach_records": seed_outreach_records,
    "script_templates": seed_script_templates,
    "knowledge": seed_knowledge,
}


def main():
    parser = argparse.ArgumentParser(description="XAgent Seed Data Generator")
    parser.add_argument("--table", choices=list(ALL_TABLES.keys()), help="Seed a single table")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--db-url", default=None, help="Database URL (default: from .env or hardcoded)")
    args = parser.parse_args()

    if args.dry_run:
        print("=== DRY RUN ===")
        for name, fn in ALL_TABLES.items():
            if args.table and name != args.table:
                continue
            print(f"  Would seed: {name}")
        print("=== END DRY RUN ===")
        return

    db_url = args.db_url
    if not db_url:
        try:
            from app.settings import settings
            db_url = settings.database_url.replace("asyncpg", "psycopg")
        except Exception:
            db_url = "postgresql://vehicle_leads:vehicle_leads@localhost:5432/vehicle_leads"

    print(f"Connecting to: {db_url}")
    engine = create_engine(db_url)

    with Session(engine) as session:
        tables = {args.table: ALL_TABLES[args.table]} if args.table else ALL_TABLES
        total = 0
        for name, fn in tables.items():
            print(f"\nSeeding {name}...")
            total += fn(session)
        session.commit()
        print(f"\nDone. Total rows inserted: {total}")


if __name__ == "__main__":
    main()
