import pytest

# Supondo que analysis_types.py define get_report_filename e AnalysisType
from backend.app.utils.analysis_types import get_report_filename, AnalysisType

@pytest.mark.parametrize("analysis_type,expected", [
    (AnalysisType.AGENT_EPICS_GENERATOR_DIGITAL, "epics.md"),
    (AnalysisType.AGENT_EPICS_REVIWER_DIGITAL, "epics.md"),
    (AnalysisType.AGENT_FEATURES_GENERATOR_DIGITAL, "features.md"),
    (AnalysisType.AGENT_FEATURES_REVIWER_DIGITAL, "features.md"),
    (AnalysisType.AGENT_TIMELINE_GENERATOR_DIGITAL, "timeline.md"),
    (AnalysisType.AGENT_TIMELINE_REVIWER_DIGITAL, "timeline.md"),
    (AnalysisType.AGENT_RISKS_GENERATOR_DIGITAL, "risks.md"),
    (AnalysisType.AGENT_RISKS_REVIWER_DIGITAL, "risks.md")
])
def test_get_report_filename_valid_types(analysis_type, expected):
    assert get_report_filename(analysis_type) == expected


def test_get_report_filename_invalid_type():
    with pytest.raises(ValueError):
        get_report_filename("invalid_type")
