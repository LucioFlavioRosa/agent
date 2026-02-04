import yaml
import os

def resolver_tipo_analise_do_workflow(analysis_type: str, workflows_path: str = None) -> str:
    """
    Carrega o arquivo workflows.yaml, busca a chave analysis_type e retorna o valor de steps[0].params.tipo_analise.
    Args:
        analysis_type (str): Nome da chave do workflow.
        workflows_path (str, optional): Caminho para o arquivo workflows.yaml. Default: raiz do projeto.
    Returns:
        str: Valor de tipo_analise do primeiro step do workflow.
    Raises:
        FileNotFoundError: Se o arquivo workflows.yaml não for encontrado.
        KeyError: Se a chave analysis_type não existir no arquivo.
        ValueError: Se o arquivo estiver malformado ou não contiver a estrutura esperada.
    """
    if workflows_path is None:
        workflows_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'workflows.yaml')
    if not os.path.exists(workflows_path):
        raise FileNotFoundError(f"Arquivo workflows.yaml não encontrado: {workflows_path}")
    try:
        with open(workflows_path, 'r', encoding='utf-8') as f:
            workflows = yaml.safe_load(f)
    except Exception as e:
        raise ValueError(f"Erro ao carregar workflows.yaml: {e}")
    if analysis_type not in workflows:
        raise KeyError(f"Chave '{analysis_type}' não encontrada em workflows.yaml")
    workflow = workflows[analysis_type]
    steps = workflow.get('steps')
    if not steps or not isinstance(steps, list) or len(steps) == 0:
        raise ValueError(f"Workflow '{analysis_type}' não possui steps válidos em workflows.yaml")
    params = steps[0].get('params')
    if not params or 'tipo_analise' not in params:
        raise ValueError(f"Step 0 do workflow '{analysis_type}' não possui 'params.tipo_analise' em workflows.yaml")
    return params['tipo_analise']
