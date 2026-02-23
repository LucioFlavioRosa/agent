from typing import Dict, Optional

ANALYSIS_TYPE_TO_REPORT: Dict[str, str] = {
    "agent_epics_generator_digital": "epics",
    "agent_epics_reviwer_digital": "epics",
    "agent_features_generator_digital": "features",
    "agent_featuares_reviwer_digital": "features",
    "agent_timeline_generator_digital": "timeline",
    "agent_timeline_reviwer_digital": "timeline",
    "agent_risks_generator_digital": "risks",
    "agent_risks_reviwer_digital": "risks"
}

def get_report_type(analysis_type: str) -> Optional[str]:
    """
    Retorna o tipo de relatório correspondente ao analysis_type, ou None se não encontrado.
    """
    return ANALYSIS_TYPE_TO_REPORT.get(analysis_type)
