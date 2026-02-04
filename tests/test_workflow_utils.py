import os
import tempfile
import pytest
import yaml
from tools.workflow_utils import resolver_tipo_analise_do_workflow

def criar_workflows_yaml(temp_path, conteudo_dict):
    workflows_path = os.path.join(temp_path, 'workflows.yaml')
    with open(workflows_path, 'w', encoding='utf-8') as f:
        yaml.dump(conteudo_dict, f)
    return workflows_path

def test_resolver_tipo_analise_sucesso(tmp_path):
    workflows_dict = {
        'analise_performance_eficiencia': {
            'steps': [
                {'params': {'tipo_analise': 'relatorio_performance_eficiencia.md'}}
            ]
        }
    }
    workflows_path = criar_workflows_yaml(tmp_path, workflows_dict)
    tipo_analise = resolver_tipo_analise_do_workflow('analise_performance_eficiencia', workflows_path)
    assert tipo_analise == 'relatorio_performance_eficiencia.md'

def test_resolver_tipo_analise_chave_inexistente(tmp_path):
    workflows_dict = {
        'outra_analise': {
            'steps': [
                {'params': {'tipo_analise': 'relatorio_outro.md'}}
            ]
        }
    }
    workflows_path = criar_workflows_yaml(tmp_path, workflows_dict)
    with pytest.raises(KeyError):
        resolver_tipo_analise_do_workflow('analise_performance_eficiencia', workflows_path)

def test_resolver_tipo_analise_workflows_yaml_malformado(tmp_path):
    workflows_path = os.path.join(tmp_path, 'workflows.yaml')
    with open(workflows_path, 'w', encoding='utf-8') as f:
        f.write('malformed: [')
    with pytest.raises(ValueError):
        resolver_tipo_analise_do_workflow('analise_performance_eficiencia', workflows_path)

def test_resolver_tipo_analise_steps_ausente(tmp_path):
    workflows_dict = {
        'analise_performance_eficiencia': {
            # steps ausente
        }
    }
    workflows_path = criar_workflows_yaml(tmp_path, workflows_dict)
    with pytest.raises(ValueError):
        resolver_tipo_analise_do_workflow('analise_performance_eficiencia', workflows_path)

def test_resolver_tipo_analise_params_ausente(tmp_path):
    workflows_dict = {
        'analise_performance_eficiencia': {
            'steps': [
                {}  # params ausente
            ]
        }
    }
    workflows_path = criar_workflows_yaml(tmp_path, workflows_dict)
    with pytest.raises(ValueError):
        resolver_tipo_analise_do_workflow('analise_performance_eficiencia', workflows_path)

def test_resolver_tipo_analise_tipo_analise_ausente(tmp_path):
    workflows_dict = {
        'analise_performance_eficiencia': {
            'steps': [
                {'params': {}}  # tipo_analise ausente
            ]
        }
    }
    workflows_path = criar_workflows_yaml(tmp_path, workflows_dict)
    with pytest.raises(ValueError):
        resolver_tipo_analise_do_workflow('analise_performance_eficiencia', workflows_path)
