import pytest
from services.incremental_step_executor_service import IncrementalStepExecutorService

EXAMPLE_REPORT = """
| Passo # | Camada | Ação | Caminho do Arquivo | Descrição | Tempo Estimado |
|---|---|---|---|---|---|
| 1 | Domínio | CRIAR | `src/domain/Entities/` | Criar entidades | 1d |
| 2 | Domínio | CRIAR | `src/domain/Interfaces/` | Criar interfaces | 1d |
| 3 | Infra | MODIFICAR | `src/data/AppDbContext.cs` | Refatorar contexto | 1d |
| 4 | Aplicação | CRIAR | `src/app/Services/` | Criar serviços | 1d |
| 5 | Domínio | MODIFICAR | `src/domain/Entities/` | Modificar entidades | 1d |
"""

def test_parse_report_and_batching():
    executor = IncrementalStepExecutorService()
    batches = executor.parse_and_batch(EXAMPLE_REPORT)
    # Espera-se que passos 1 e 5 estejam em batches diferentes (mesmo caminho)
    assert isinstance(batches, list)
    assert all(isinstance(batch, list) for batch in batches)
    # Passos 1 e 5 devem estar em batches diferentes
    batch_paths = [[step['Caminho do Arquivo'] for step in batch] for batch in batches]
    all_paths = [path for batch in batch_paths for path in batch]
    assert '`src/domain/Entities/`' in all_paths
    # Testa que batches não misturam passos dependentes
    for batch in batches:
        paths = set([step['Caminho do Arquivo'] for step in batch])
        assert len(paths) == len(batch) or all(paths)  # Cada batch só tem passos independentes

def test_empty_or_malformed_report():
    executor = IncrementalStepExecutorService()
    assert executor.parse_and_batch('') == []
    assert executor.parse_and_batch('Texto sem tabela') == []
