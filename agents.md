# 开发阶段铁律

1. 每个步骤完成后，必须执行两轮独立的多维度评审，评审未完成不得进入下一步。
2. 两轮评审都必须显式记录结论、发现项和修正结果；若第一轮修正后仍有新增实质问题，第二轮继续以独立视角复核。
3. 只有在连续两轮评审都没有新增实质阻塞问题时，当前步骤才可视为完成。
4. 该规则适用于所有后续 Story 开发、校验、实现和收口流程，优先级高于个人习惯性省略。
5. 请严格执行前后端联调测试，而不是只有seed数据的静态页面。
6. 所有过程、结果、注解和文档都使用中文。

<claude-mem-context>
# Memory Context

# [xagent] recent context, 2026-06-08 4:06pm GMT+8

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 33 obs (14,155t read) | 0t work

### May 25, 2026
692 2:57p ✅ Added failure case library concept to overseas vehicle procurement AI acquisition system
698 6:06p ✅ Added cost and ROI dimension to overseas vehicle procurement AI acquisition system
### May 26, 2026
700 9:31a ✅ Established cost control limits for PoC phase of overseas vehicle acquisition system
706 9:32a ✅ Added ROI metrics hierarchy to overseas vehicle acquisition system cost framework
695 9:33a ✅ Expanded overseas vehicle procurement AI acquisition system brainstorming with PoC/MVP roadmap
707 9:34a ⚖️ Selected Plan B implementation approach for overseas vehicle acquisition system
708 9:54a 🟣 Created comprehensive design specification for overseas vehicle acquisition AI system
724 10:54a 🟣 Generated professional PowerPoint presentation for overseas vehicle procurement AI system
726 10:59a ✅ Refined and regenerated PowerPoint presentation for overseas vehicle procurement AI acquisition system
740 1:57p ✅ Setup implementation planning infrastructure for BMAD project
741 " 🔵 BMAD implementation plan completed with comprehensive two-phase structure
742 " ✅ BMAD implementation plan created with comprehensive two-phase structure
743 2:03p ✅ BMAD implementation plan finalized with comprehensive task breakdown
752 2:04p 🟣 MVP prototype infrastructure created for overseas vehicle leads AI system
759 2:05p 🟣 Headless Chrome screenshot automation for prototype validation
761 2:56p 🔵 Successful screenshot automation using Chrome headless
762 " 🔵 Playwright screenshot automation failures
763 " 🔵 Python HTTP server permission error
### Jun 1, 2026
825 1:59p 🔵 Project structure discovery for overseas vehicle leads AI system
826 2:00p 🔵 Comprehensive LLM integration architecture in vehicle leads AI system
827 2:01p 🔵 Existing comprehensive deployment documentation found in docs/deploy directory
828 " 🔵 Mobile and admin application architecture discovery
830 " 🔵 Comprehensive agent exploration reveals complete system architecture and missing LLM configuration
829 " 🔵 Mobile app configuration and CSV validation infrastructure discovered
831 2:03p 🔵 Comprehensive LLM prompt engineering system discovered for lead extraction and grading
832 " ✅ Deployment documentation for LLM integration requested
834 2:04p 🔵 Complete API architecture and data models documented for AI lead generation system
836 " 🟣 Implemented comprehensive seed data generator for XAgent API
833 2:07p 🔵 AI-powered lead generation system architecture documented
835 2:09p ✅ Deploy documentation and seed data generation tasks initiated
837 2:14p 🔴 Fixed IndexError in seed data customer grade assignment
S135 Fixed IndexError in seed data script - customer grade array access now uses modulo to prevent index out of range (Jun 1 at 2:14 PM)
838 4:18p 🔵 Discovered LLM agent integration configuration gap between .env and Settings
839 4:20p 🔵 Confirmed LLM integration architecture uses external agent processing with no internal API client
</claude-mem-context>