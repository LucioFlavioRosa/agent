import pytest

# Supondo que a função get_report_type está em backend/app/utils/analysis_type_mapper.py
from backend.app.utils.analysis_type_mapper import get_report_type

ANALYSIS_TYPE_MAPPING = {
    "agent_epics_generator_digital": "epics",
    "agent_epics_reviwer_digital": "epics",
    "agent_features_generator_digital": "features",
    "agent_featuares_reviwer_digital": "features",
    "agent_timeline_generator_digital": "timeline",
    "agent_timeline_reviwer_digital": "timeline",
    "agent_risks_generator_digital": "risks",
    "agent_risks_reviwer_digital": "risks"
}

@pytest.mark.parametrize("analysis_type,expected", list(ANALYSIS_TYPE_MAPPING.items()))
def test_valid_analysis_types(analysis_type, expected):
    assert get_report_type(analysis_type) == expected

def test_invalid_analysis_type():
    assert get_report_type("invalid_type") is None

def test_case_sensitivity():
    # O mapeamento deve ser case-sensitive
    assert get_report_type("Agent_epics_generator_digital") is None
    assert get_report_type("agent_EPICS_generator_digital") is None
    # Lowercase correto funciona
    assert get_report_type("agent_epics_generator_digital") == "epics"
