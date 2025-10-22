from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class JobStatus:
    WORKFLOW_STARTED = "workflow_started"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"

class JobFields:
    DATA = "data"
    STATUS = "status"
    INSTRUCOES_EXTRAS_APROVACAO = "instrucoes_extras_aprovacao"
    PAUSED_AT_STEP = "paused_at_step"
    REPO_NAME = "repo_name_modernizado"
    REPOSITORY_TYPE = "repository_type"
    PROJETO = "projeto"
    ANALYSIS_REPORT = "analysis_report"
    REPORT_BLOB_URL = "report_blob_url"
    GERAR_RELATORIO_APENAS = "gerar_relatorio_apenas"
    EXECUTAR_STEPS_INCREMENTALMENTE = "executar_steps_incrementalmente"
    MAX_STEPS_PER_BATCH = "max_steps_per_batch"
    STEP_BATCHES = "step_batches"
    CURRENT_BATCH_INDEX = "current_batch_index"
    BATCH_RESULTS = "batch_results"
    GERAR_NOVO_RELATORIO = "gerar_novo_relatorio"
    ANALYSIS_NAME = "analysis_name"

class JobActions:
    APPROVE = "approve"
    REJECT = "reject"

class ValidAnalysisTypes(str, Enum):
    tipo1 = "tipo1"
    tipo2 = "tipo2"
    # ... outros tipos

class StartAnalysisPayload(BaseModel):
    repo_name_modernizado: str = Field(description="Nome do repositório modernizado")
    branch_name_modernizado: Optional[str] = Field(None, description="Branch do repositório modernizado")
    projeto: str = Field(description="Nome do projeto para agrupar atividades e organizar histórico")
    analysis_type: ValidAnalysisTypes
    instrucoes_extras: Optional[str] = None
    usar_rag: bool = Field(False)
    gerar_relatorio_apenas: bool = Field(False)
    gerar_novo_relatorio: bool = Field(
        True,
        description="Se False, tenta ler relatório existente do Blob Storage usando analysis_name antes de gerar um novo"
    )
    model_name: Optional[str] = Field(None, description="Nome do modelo de LLM a ser usado. Se nulo, usa o padrão.")
    arquivos_especificos: Optional[list] = Field(None, description="Lista opcional de caminhos específicos de arquivos para ler. Se fornecido, apenas esses arquivos serão processados.")
    analysis_name: Optional[str] = Field(None, description="Nome personalizado para identificar a análise.")
    repository_type: str = Field(description="Tipo do repositório: 'github', 'gitlab', 'azure'.")
    repo_name_original: Optional[str] = Field(None, description="Nome do repositório original para comparação")
    branch_name_original: Optional[str] = Field(None, description="Branch do repositório original")
    retornar_lista_arquivos: bool = Field(False, description="Se True, além do código filtrado, retorna lista completa de todos os arquivos do repositório")
    usuario_executor: Optional[str] = Field(None, description="Nome do usuário que está executando a análise")
    executar_steps_incrementalmente: bool = Field(
        True, description="[DEPRECATED: O valor False está descontinuado e será removido em versões futuras. Use sempre True.] Se True, os passos do relatório de implementação serão executados de forma incremental (um ou mais passos por vez, respeitando dependências), ao invés de enviar todas as mudanças de uma só vez. Útil para relatórios extensos que podem exceder limites de tokens da LLM.")
    executar_build_dotnet: bool = Field(False, description="Se True, executa o build do projeto .NET após o commit e retorna os erros de compilação, se houver.")
    max_steps_per_batch: Optional[int] = Field(3, description="Número máximo de steps por batch na execução incremental")
