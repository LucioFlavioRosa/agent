from enum import Enum

class AnalysisType(str, Enum):
    AGENT_EPICS_GENERATOR_DIGITAL = "agent_epics_generator_digital"
    AGENT_EPICS_REVIWER_DIGITAL = "agent_epics_reviwer_digital"
    AGENT_FEATURES_GENERATOR_DIGITAL = "agent_features_generator_digital"
    AGENT_FEATUARES_REVIWER_DIGITAL = "agent_featuares_reviwer_digital"
    AGENT_TIMELINE_GENERATOR_DIGITAL = "agent_timeline_generator_digital"
    AGENT_TIMELINE_REVIWER_DIGITAL = "agent_timeline_reviwer_digital"
    AGENT_RISKS_GENERATOR_DIGITAL = "agent_risks_generator_digital"
    AGENT_RISKS_REVIWER_DIGITAL = "agent_risks_reviwer_digital"

ANALYSIS_TYPE_TO_REPORT_NAME = {
    AnalysisType.AGENT_EPICS_GENERATOR_DIGITAL: "epics",
    AnalysisType.AGENT_EPICS_REVIWER_DIGITAL: "epics",
    AnalysisType.AGENT_FEATURES_GENERATOR_DIGITAL: "features",
    AnalysisType.AGENT_FEATUARES_REVIWER_DIGITAL: "features",
    AnalysisType.AGENT_TIMELINE_GENERATOR_DIGITAL: "timeline",
    AnalysisType.AGENT_TIMELINE_REVIWER_DIGITAL: "timeline",
    AnalysisType.AGENT_RISKS_GENERATOR_DIGITAL: "risks",
    AnalysisType.AGENT_RISKS_REVIWER_DIGITAL: "risks"
}

def get_report_filename(analysis_type: str) -> str:
    """
    Retorna o nome do arquivo de relatório baseado no tipo de análise.
    """
    try:
        enum_type = AnalysisType(analysis_type)
        return ANALYSIS_TYPE_TO_REPORT_NAME[enum_type]
    except (ValueError, KeyError):
        return "report"
