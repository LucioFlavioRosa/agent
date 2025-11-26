import uuid
from typing import Optional, Dict, Any
from models import JobFields

class JobDataService:
    def create_initial_job_data(self, payload_dict: Dict[str, Any], normalized_repo_name: Optional[str], analysis_name: Optional[str]) -> Dict[str, Any]:
        job_data = {
            JobFields.STATUS: JobFields.STARTING,
            JobFields.DATA: {
                **payload_dict,
                JobFields.REPO_NAME: normalized_repo_name,
                JobFields.ANALYSIS_NAME: analysis_name,
                JobFields.ERROR_DETAILS: None,
                JobFields.REPORT_BLOB_URL: None,
                JobFields.ANALYSIS_REPORT: None,
                JobFields.COMMIT_DETAILS: [],
                JobFields.DIAGNOSTIC_LOGS: {},
                JobFields.BUILD_ERRORS: None
            }
        }
        return job_data

    def create_derived_job_data(self, original_job: Dict[str, Any], analysis_name: str, normalized_repo_name: Optional[str], report: Optional[str]) -> Dict[str, Any]:
        derived_data = original_job[JobFields.DATA].copy()
        derived_data[JobFields.REPO_NAME] = normalized_repo_name
        derived_data[JobFields.ANALYSIS_NAME] = analysis_name
        derived_data[JobFields.ANALYSIS_REPORT] = report
        derived_data[JobFields.REPORT_BLOB_URL] = None
        derived_data[JobFields.COMMIT_DETAILS] = []
        derived_data[JobFields.BUILD_ERRORS] = None
        derived_data[JobFields.ERROR_DETAILS] = None
        derived_data[JobFields.DIAGNOSTIC_LOGS] = {}
        return {
            JobFields.STATUS: JobFields.STARTING,
            JobFields.DATA: derived_data
        }

    def generate_analysis_name(self, custom_name: Optional[str], job_id: str) -> str:
        if custom_name and custom_name.strip():
            return custom_name.strip()
        return f"analysis_{job_id[:8]}"
