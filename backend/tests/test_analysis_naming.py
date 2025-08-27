import pytest
from fastapi.testclient import TestClient
from mcp_server_fastapi import app, job_store
import uuid

client = TestClient(app)

# Geração de nome único para evitar conflitos entre execuções de teste
ANALYSIS_NAME = f"test-analysis-{uuid.uuid4()}"

def get_payload():
    """
    Gera payload de teste padronizado para criação de análise com nome específico.
    
    Esta função factory centraliza a criação de payloads de teste, garantindo
    consistência entre diferentes cenários de teste e facilitando manutenção
    quando a estrutura de dados mudar.
    
    Returns:
        dict: Payload configurado para testes de nomeação de análise contendo:
            - repo_name (str): Repositório de teste no formato 'org/repo'
            - analysis_type (str): Tipo de análise a ser executada
            - branch_name (str): Branch de origem para análise
            - instrucoes_extras (str): Instruções específicas do teste
            - usar_rag (bool): Flag para uso de RAG (desabilitado em testes)
            - gerar_relatorio_apenas (bool): Flag para gerar apenas relatório
            - model_name (None): Usa modelo padrão do sistema
            - analysis_name (str): Nome único da análise para identificação
    
    Note:
        - Usa analysis_name global único para evitar conflitos
        - Configurado para gerar apenas relatório (mais rápido para testes)
        - RAG desabilitado para evitar dependências externas em testes
    """
    return {
        "repo_name": "org/testrepo",
        "analysis_type": "default",  # ajuste conforme workflow disponível
        "branch_name": "main",
        "instrucoes_extras": "Teste de nomeação de análise.",
        "usar_rag": False,  # Desabilitado para evitar dependências externas
        "gerar_relatorio_apenas": True,  # Acelera execução dos testes
        "model_name": None,  # Usa modelo padrão do sistema
        "analysis_name": ANALYSIS_NAME  # Nome único para identificação
    }

def test_create_analysis_with_name():
    """
    Testa a funcionalidade de criação de análise com nome personalizado.
    
    Objetivo:
        Verificar se o sistema consegue criar uma análise com um nome
        personalizado e se esse nome é corretamente armazenado no job store
        para posterior recuperação.
    
    Cenário de Teste:
        1. Envia requisição POST para criar análise com analysis_name específico
        2. Verifica se resposta contém job_id válido
        3. Recupera job do store usando job_id retornado
        4. Valida se analysis_name foi persistido corretamente nos dados do job
    
    Validações:
        - Status code 200 na criação
        - Job_id presente na resposta
        - Job existe no store após criação
        - Analysis_name persistido corretamente nos dados do job
    
    Raises:
        AssertionError: Se qualquer validação falhar
    
    Note:
        - Usa nome único global para evitar conflitos
        - Testa tanto a API quanto a persistência no job store
        - Fundamental para funcionalidade de busca por nome
    """
    # Envia requisição de criação de análise
    response = client.post("/start-analysis", json=get_payload())
    
    # Valida resposta da API
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    
    # Verifica persistência no job store
    job = job_store.get_job(job_id)
    assert job is not None
    
    # Valida se analysis_name foi salvo corretamente
    assert job["data"].get("analysis_name") == ANALYSIS_NAME

def test_retrieve_report_by_analysis_name():
    """
    Testa a funcionalidade de recuperação de relatório usando nome da análise.
    
    Objetivo:
        Verificar se o sistema consegue localizar e retornar um relatório
        de análise usando o nome personalizado em vez do job_id, implementando
        busca por nome como alternativa mais amigável ao usuário.
    
    Cenário de Teste:
        1. Cria análise com nome específico
        2. Aguarda processamento básico (simulado com sleep)
        3. Busca relatório usando endpoint de busca por nome
        4. Valida dados retornados (job_id, analysis_name, analysis_report)
    
    Validações:
        - Criação bem-sucedida da análise
        - Busca por nome retorna status 200
        - Job_id na resposta corresponde ao job original
        - Analysis_name na resposta corresponde ao nome buscado
        - Campo analysis_report está presente na resposta
    
    Raises:
        AssertionError: Se qualquer validação falhar
    
    Note:
        - Sleep simula tempo de processamento mínimo
        - Testa endpoint específico de busca por nome
        - Valida integridade dos dados entre criação e recuperação
    """
    # Cria análise com nome específico
    response = client.post("/start-analysis", json=get_payload())
    job_id = response.json()["job_id"]
    
    # Aguarda processamento mínimo (simulação de processamento assíncrono)
    import time
    time.sleep(2)
    
    # Busca relatório usando nome da análise
    response2 = client.get(f"/analyses/by-name/{ANALYSIS_NAME}")
    
    # Valida resposta da busca por nome
    assert response2.status_code == 200
    data = response2.json()
    
    # Valida integridade dos dados retornados
    assert data["job_id"] == job_id
    assert data["analysis_name"] == ANALYSIS_NAME
    assert "analysis_report" in data

def test_code_generation_from_existing_report():
    """
    Testa a funcionalidade de geração de código baseada em relatório existente.
    
    Objetivo:
        Verificar se o sistema consegue iniciar um processo de geração
        de código usando como entrada um relatório de análise já existente,
        identificado pelo nome da análise. Isso permite workflows em duas etapas:
        análise → aprovação → geração de código.
    
    Cenário de Teste:
        1. Cria análise inicial para gerar relatório base
        2. Aguarda processamento para garantir relatório disponível
        3. Inicia geração de código baseada no relatório existente
        4. Valida se novo job foi criado para a etapa de geração
    
    Validações:
        - Análise inicial criada com sucesso
        - Geração de código iniciada com status 200
        - Novo job_id retornado para processo de geração
        - Job_id da geração é diferente do job_id da análise inicial
    
    Raises:
        AssertionError: Se qualquer validação falhar
    
    Note:
        - Testa workflow completo: análise → geração de código
        - Valida que são processos separados com job_ids distintos
        - Simula caso de uso real de aprovação de relatório seguida de implementação
    """
    # Cria análise inicial para gerar relatório base
    response = client.post("/start-analysis", json=get_payload())
    job_id = response.json()["job_id"]
    
    # Aguarda processamento para garantir relatório disponível
    import time
    time.sleep(2)
    
    # Inicia geração de código baseada no relatório existente
    response2 = client.post(f"/start-code-generation-from-report/{ANALYSIS_NAME}")
    
    # Valida resposta da geração de código
    assert response2.status_code == 200
    assert "job_id" in response2.json()
    
    # Valida que é um novo processo (job_id diferente)
    new_job_id = response2.json()["job_id"]
    assert new_job_id != job_id  # Deve ser processo separado

def test_duplicate_analysis_name_overwrites():
    """
    Testa o comportamento do sistema com nomes de análise duplicados.
    
    Objetivo:
        Verificar se o sistema implementa corretamente a política de
        sobrescrita para nomes duplicados, onde a análise mais recente
        substitui a anterior na busca por nome. Isso evita conflitos
        e garante que usuários sempre acessem a versão mais atual.
    
    Cenário de Teste:
        1. Cria primeira análise com nome específico
        2. Cria segunda análise com o mesmo nome (duplicação intencional)
        3. Verifica se ambas geraram job_ids diferentes (processos distintos)
        4. Valida se busca por nome retorna a análise mais recente
    
    Política Testada:
        Sobrescrita - análises com nomes duplicados fazem com que
        a mais recente seja retornada nas buscas por nome, mantendo
        apenas a referência mais atual ativa.
    
    Validações:
        - Primeira análise criada com sucesso
        - Segunda análise criada com sucesso
        - Job_ids são diferentes (processos independentes)
        - Busca por nome retorna job_id da segunda análise (mais recente)
    
    Raises:
        AssertionError: Se qualquer validação falhar
    
    Note:
        - Testa política de negócio específica de sobrescrita
        - Garante que não há conflitos com nomes duplicados
        - Valida que busca sempre retorna versão mais atual
    """
    payload = get_payload()
    
    # Cria primeira análise com nome específico
    response1 = client.post("/start-analysis", json=payload)
    job_id1 = response1.json()["job_id"]
    
    # Cria segunda análise com o mesmo nome (duplicação intencional)
    response2 = client.post("/start-analysis", json=payload)
    job_id2 = response2.json()["job_id"]
    
    # Valida que são processos distintos
    assert job_id1 != job_id2
    
    # Aguarda processamento mínimo
    import time
    time.sleep(1)
    
    # Busca por nome deve retornar a análise mais recente (política de sobrescrita)
    response3 = client.get(f"/analyses/by-name/{ANALYSIS_NAME}")
    assert response3.status_code == 200
    assert response3.json()["job_id"] == job_id2  # Deve retornar o mais recente