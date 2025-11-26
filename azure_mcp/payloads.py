from pydantic import BaseModel, Field, validator
from typing import Optional
from azure_mcp.models import ValidAnalysisTypes

class StartAzureAnalysisPayload(BaseModel):
    analysis_type: ValidAnalysisTypes = Field(..., description="Tipo de análise Azure DevOps.")
    epic_id: Optional[str] = Field(None, description="ID do épico do Azure DevOps.")
    feature_id: Optional[str] = Field(None, description="ID da feature do Azure DevOps.")
    task_id: Optional[str] = Field(None, description="ID da tarefa do Azure DevOps.")
    instrucoes_extras: Optional[str] = Field(None, description="Instruções extras para o agente.")
    model_name: Optional[str] = Field(None, description="Nome do modelo de LLM a ser usado.")
    organization: Optional[str] = Field(None, description="Organização Azure DevOps.")
    project: Optional[str] = Field(None, description="Projeto Azure DevOps.")
    usuario_executor: Optional[str] = Field(None, description="Usuário executor da análise.")

    @validator('epic_id')
    def validate_epic_id(cls, v, values):
        if values.get('analysis_type') == ValidAnalysisTypes.CRIACAO_FEATURES_AZURE_DEVOPS and (v is None or not str(v).strip()):
            raise ValueError('epic_id é obrigatório para criacao_features_azure_devops.')
        return v

    @validator('feature_id')
    def validate_feature_id(cls, v, values):
        if values.get('analysis_type') == ValidAnalysisTypes.CRIACAO_TAREFAS_AZURE_DEVOPS and (v is None or not str(v).strip()):
            raise ValueError('feature_id é obrigatório para criacao_tarefas_azure_devops.')
        return v

    @validator('task_id')
    def validate_task_id(cls, v, values):
        if values.get('analysis_type') == ValidAnalysisTypes.REVISOR_TAREFAS and (v is None or not str(v).strip()):
            raise ValueError('task_id é obrigatório para revisor_tarefas.')
        return v
