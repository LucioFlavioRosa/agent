import hashlib
import re
class AnalysisNameService:
    def generate_analysis_name(self, analysis_name: str, job_id: str) -> str:
        if analysis_name:
            sanitized = self._sanitize_analysis_name(analysis_name)
            return f"{sanitized}-{job_id[:8]}"
        return f"analysis-{job_id[:8]}"
    def _sanitize_analysis_name(self, name: str) -> str:
        name = name.lower()
        name = re.sub(r'[^a-z0-9\-_]', '-', name)
        name = re.sub(r'-+', '-', name)
        return name.strip('-')
    def register_analysis(self, analysis_name: str, job_id: str):
        pass