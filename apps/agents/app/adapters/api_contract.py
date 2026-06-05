class ApiContractBoundary:
    allowed_output_tables = (
        "lead_enrichment_field_candidates",
        "lead_cleanup_suggestions",
        "shadow_source_candidates",
        "shadow_staging_lead_candidates",
        "shadow_lead_grading_suggestions",
    )
    forbidden_core_tables = ("customers", "lead_sources", "contact_methods", "lead_source_candidates", "staging_leads")

    def validate_output_table(self, table_name: str) -> str:
        normalized = table_name.strip()
        if normalized in self.forbidden_core_tables:
            raise ValueError("Agent 项目不得直接写 core 表。")
        if normalized not in self.allowed_output_tables:
            raise ValueError("Agent 项目仅允许输出结构化 staging 候选。")
        return normalized
