from models import FinalStatusResponse, JobFields

class ResponseBuilderService:
    def build_completed_response(self, job_id, job_info, blob_url=None):
        summary = None
        build_errors = None
        if JobFields.COMMIT_DETAILS in job_info['data']:
            commit_details = job_info['data'][JobFields.COMMIT_DETAILS]
            summary = []
            build_errors = []
            for detail in commit_details:
                pr_url = detail.get('pr_url')
                branch_name = detail.get('branch_name')
                arquivos_modificados = detail.get('arquivos_modificados', [])
                summary.append({
                    'pull_request_url': pr_url,
                    'branch_name': branch_name,
                    'arquivos_modificados': arquivos_modificados
                })
                if 'build_errors' in detail and detail['build_errors']:
                    build_errors.extend(detail['build_errors'])
        if JobFields.BUILD_ERRORS in job_info['data'] and job_info['data'][JobFields.BUILD_ERRORS]:
            build_errors = job_info['data'][JobFields.BUILD_ERRORS]
        if build_errors is not None and len(build_errors) == 0:
            build_errors = None
        return FinalStatusResponse(
            job_id=job_id,
            status=job_info.get('status'),
            summary=summary,
            error_details=job_info['data'].get(JobFields.ERROR_DETAILS),
            analysis_report=job_info['data'].get(JobFields.ANALYSIS_REPORT),
            diagnostic_logs=job_info['data'].get(JobFields.DIAGNOSTIC_LOGS),
            report_blob_url=blob_url,
            build_errors=build_errors
        )
