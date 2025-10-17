from models import JobFields

def create_initial_job_data(payload_dict, normalized_repo_name, analysis_name, branch_name):
    job_data = {
        JobFields.REPO_NAME: normalized_repo_name,
        JobFields.ANALYSIS_NAME: analysis_name,
        JobFields.DATA: dict(payload_dict),
        JobFields.BRANCH_NAME: branch_name,
        JobFields.STATUS: None,
    }
    job_data[JobFields.DATA][JobFields.BRANCH_NAME] = branch_name
    return job_data

def create_derived_job_data(original_job, analysis_name, normalized_repo_name, report, branch_name):
    job_data = {
        JobFields.REPO_NAME: normalized_repo_name,
        JobFields.ANALYSIS_NAME: analysis_name,
        JobFields.DATA: dict(original_job.get(JobFields.DATA, {})),
        JobFields.BRANCH_NAME: branch_name,
        JobFields.STATUS: None,
        JobFields.ANALYSIS_REPORT: report,
    }
    job_data[JobFields.DATA][JobFields.BRANCH_NAME] = branch_name
    return job_data
