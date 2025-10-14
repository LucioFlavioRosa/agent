from typing import Optional, List

class JobFields:
    STATUS = 'status'
    DATA = 'data'
    PAUSED_AT_STEP = 'paused_at_step'
    INSTRUCOES_EXTRAS_APROVACAO = 'instrucoes_extras_aprovacao'
    REPORT_BLOB_URL = 'report_blob_url'
    ANALYSIS_REPORT = 'analysis_report'
    COMMIT_DETAILS = 'commit_details'
    ERROR_DETAILS = 'error_details'
    DIAGNOSTIC_LOGS = 'diagnostic_logs'
    BUILD_RESULT = 'build_result'
    BUILD_ERRORS = 'build_errors'
    EXECUTAR_STEPS_INCREMENTALMENTE = 'executar_steps_incrementalmente'
    EXECUTAR_BUILD_DOTNET = 'executar_build_dotnet'
    STEP_BATCHES = 'step_batches'
    CURRENT_BATCH_INDEX = 'current_batch_index'
    BATCH_RESULTS = 'batch_results'
    REPO_NAME = 'repo_name'
    REPOSITORY_TYPE = 'repository_type'
    GERAR_RELATORIO_APENAS = 'gerar_relatorio_apenas'
    PROJETO = 'projeto'
    MAX_STEPS_PER_BATCH = 'max_steps_per_batch'
    GERAR_NOVO_RELATORIO = 'gerar_novo_relatorio'
    ANALYSIS_NAME = 'analysis_name'
    REPO_NAME_MODERNIZADO = 'repo_name_modernizado'
    BRANCH_NAME_MODERNIZADO = 'branch_name_modernizado'
    REPO_NAME_ORIGINAL = 'repo_name_original'
    BRANCH_NAME_ORIGINAL = 'branch_name_original'
    RETORNAR_LISTA_ARQUIVOS = 'retornar_lista_arquivos'
    MODO_ADICAO_INCREMENTAL = 'modo_adicao_incremental'
    USUARIO_EXECUTOR = 'usuario_executor'

class JobStatus:
    WORKFLOW_STARTED = 'WORKFLOW_STARTED'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    REJECTED = 'REJECTED'

class JobActions:
    APPROVE = 'approve'
    REJECT = 'reject'

class FinalStatusResponse:
    def __init__(self, job_id: str, status: str, summary: Optional[List[dict]] = None, diagnostic_logs: Optional[str] = None, report_blob_url: Optional[str] = None, build_errors: Optional[List[str]] = None, error_details: Optional[str] = None, analysis_report: Optional[str] = None):
        self.job_id = job_id
        self.status = status
        self.summary = summary
        self.diagnostic_logs = diagnostic_logs
        self.report_blob_url = report_blob_url
        self.build_errors = build_errors
        self.error_details = error_details
        self.analysis_report = analysis_report
