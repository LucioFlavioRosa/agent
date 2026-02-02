import pytest
from pydantic import ValidationError, BaseModel, Field
from typing import Optional, List, Literal

class AnalysisRequest(BaseModel):
    repository_type: Literal['github', 'gitlab', 'azure']
    repo_name: str = Field(...)
    branch_name: str = Field(...)
    agent_type: Literal['review', 'improve'] = Field(...)
    arquivos_especificos: Optional[List[str]] = None
    instrucoes_extras: Optional[str] = None

def test_valid_analysis_request():
    req = AnalysisRequest(
        repository_type='github',
        repo_name='org/projeto/repo',
        branch_name='main',
        agent_type='review',
        arquivos_especificos=['file1.py', 'file2.py'],
        instrucoes_extras='Favor revisar o código.'
    )
    assert req.repository_type == 'github'
    assert req.agent_type == 'review'
    assert req.repo_name == 'org/projeto/repo'
    assert req.branch_name == 'main'
    assert req.arquivos_especificos == ['file1.py', 'file2.py']
    assert req.instrucoes_extras == 'Favor revisar o código.'

def test_invalid_repository_type():
    with pytest.raises(ValidationError):
        AnalysisRequest(
            repository_type='bitbucket',
            repo_name='org/projeto/repo',
            branch_name='main',
            agent_type='review'
        )

def test_invalid_agent_type():
    with pytest.raises(ValidationError):
        AnalysisRequest(
            repository_type='github',
            repo_name='org/projeto/repo',
            branch_name='main',
            agent_type='analyze'
        )

def test_missing_required_fields():
    with pytest.raises(ValidationError):
        AnalysisRequest(
            repository_type='github',
            repo_name='org/projeto/repo',
            agent_type='review'
        )
