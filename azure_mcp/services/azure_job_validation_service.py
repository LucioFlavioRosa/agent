from services.job_validation_service import JobValidationService

class AzureJobValidationService(JobValidationService):
    def validate_payload(self, payload):
        analysis_type = getattr(payload, 'analysis_type', None)
        if not payload.organization or not payload.project:
            raise Exception("organization e project são obrigatórios para qualquer análise Azure.")
        if analysis_type == 'criacao_features_azure_devops' and not payload.epic_id:
            raise Exception("epic_id é obrigatório para criacao_features_azure_devops.")
        if analysis_type == 'criacao_tarefas_azure_devops' and not payload.feature_id:
            raise Exception("feature_id é obrigatório para criacao_tarefas_azure_devops.")
        if analysis_type == 'revisor_tarefas' and not payload.task_id:
            raise Exception("task_id é obrigatório para revisor_tarefas.")
        if analysis_type == 'criacao_epicos_azure_devops' and not payload.instrucoes_extras:
            raise Exception("instrucoes_extras é obrigatório para criacao_epicos_azure_devops.")

    def validate_job_exists(self, job, job_id):
        super().validate_job_exists(job, job_id)
        # Azure-specific: organization/project must always be present
        data = job.get('data', {})
        if not data.get('organization') or not data.get('project'):
            raise Exception(f"Job {job_id} inválido: organization e project obrigatórios.")

    def validate_job_for_approval(self, job, job_id):
        super().validate_job_for_approval(job, job_id)
        # Azure-specific: organization/project must always be present
        data = job.get('data', {})
        if not data.get('organization') or not data.get('project'):
            raise Exception(f"Job {job_id} inválido para aprovação: organization e project obrigatórios.")
