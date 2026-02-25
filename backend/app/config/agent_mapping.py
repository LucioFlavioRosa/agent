AGENT_CONFIG = {
    "agent_epics_generator_digital": {
        "prompt_file": "create_epics.md",
        "output_filename": "epics.md",      
        "llm_model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "service": "claude_aws_service"
    },
    "agent_epics_reviwer_digital": {
        "prompt_file": "epics.md",
        "output_filename": "epics.md",      
        "llm_model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "service": "claude_aws_service"
    },
    "agent_features_generator_digital": {
        "prompt_file": "create_features.md",
        "output_filename": "features.md",
        "llm_model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "service": "claude_aws_service"
    },
    "agent_timeline_generator_digital": {
        "prompt_file": "create_timeline.md",
        "output_filename": "timeline.md",
        "llm_model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "service": "claude_aws_service"
    }
}
