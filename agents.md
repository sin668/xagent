# 开发阶段铁律

1. 每个步骤完成后，必须执行两轮独立的多维度评审，评审未完成不得进入下一步。
2. 两轮评审都必须显式记录结论、发现项和修正结果；若第一轮修正后仍有新增实质问题，第二轮继续以独立视角复核。
3. 只有在连续两轮评审都没有新增实质阻塞问题时，当前步骤才可视为完成。
4. 该规则适用于所有后续 Story 开发、校验、实现和收口流程，优先级高于个人习惯性省略。
5. 请严格执行前后端联调测试，而不是只有seed数据的静态页面。
6. 所有过程、结果、注解和文档都使用中文。

<claude-mem-context>
# Memory Context

# [xagent] recent context, 2026-06-10 6:10pm GMT+8

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (17,252t read) | 111,126t work | 84% savings

### May 26, 2026
740 1:57p ✅ Setup implementation planning infrastructure for BMAD project
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
### Jun 10, 2026
925 2:11p 🟣 Mobile homepage statistics display requirements identified
926 " 🔵 Mobile app statistics tracking already implemented in homeMetrics service
927 2:13p 🔵 Homepage statistics implementation matches user requirements via buildHomeLeadStats function
928 2:14p 🔵 Homepage statistics pipeline uses backend summary data processed through buildHomeDashboard
937 2:17p 🔵 Homepage cleaned leads statistic showing incorrect count
938 2:26p 🔵 Cleaned leads count discrepancy detected on homepage
939 " 🔴 Backend API returning incorrect total count for lead cleanup suggestions
941 " 🔵 Second homepage statistics discrepancy discovered for A/B/C grade leads
942 " 🔵 Homepage A/B/C级线索 count discrepancy traced to different data sources
940 2:27p 🔵 API endpoint returning incorrect total count confirmed through testing
943 2:31p 🟣 Customer details page enhancement with manual field completion
944 2:59p 🔵 Current customer detail page layout and enhancement requirements identified
946 " 🔵 Customer detail page manual enrichment enhancement requirements and implementation patterns identified
948 " 🔵 Customer detail page enhancement test requirements defined for manual recording implementation
945 3:00p 🔵 Customer detail page enhancement patterns identified from lead details and followups pages
949 3:01p 🟣 Adding manual data entry for pending customer fields
947 3:02p 🔵 Customer detail page enhancement patterns analyzed for manual recording implementation
950 3:06p 🟣 Implemented manual field entry for customer pending fields
951 3:08p 🟣 Manual customer field entry feature implemented and tested successfully
952 " 🟣 CSS styling implemented for manual field entry UI components
954 3:10p 🔵 Customer detail page enhancement requirements identified
953 3:14p 🟣 Manual field entry feature completed with full test coverage and build verification
955 3:45p 🔵 Build System Output Shows uniCloud Hosting
956 4:19p 🔴 Do Not Contact Status Persistence Fixed in API Adapter
957 4:23p 🔴 Do Not Contact State Persistence Bug Fixed Across Full Stack
958 4:30p 🟣 Customer redirect logic re-applied to lead detail page
959 5:29p 🟣 Mobile outreach email sending with Industrial Luxury aesthetic
960 5:47p 🔵 Backend API datetime.utcnow() deprecation warning in outreach draft service

Access 111k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>