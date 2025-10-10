import pytest
from services.step_dependency_analyzer import StepDependencyAnalyzer

def test_dependency_same_file():
    step1 = {'Caminho do Arquivo': '`src/domain/Entities/Entidade.cs`'}
    step2 = {'Caminho do Arquivo': '`src/domain/Entities/Entidade.cs`'}
    assert StepDependencyAnalyzer.are_steps_dependent(step1, step2)

def test_dependency_subdirectory():
    step1 = {'Caminho do Arquivo': '`src/domain/Entities/`'}
    step2 = {'Caminho do Arquivo': '`src/domain/Entities/Entidade.cs`'}
    assert StepDependencyAnalyzer.are_steps_dependent(step1, step2)

def test_independent_files():
    step1 = {'Caminho do Arquivo': '`src/domain/Entities/EntidadeA.cs`'}
    step2 = {'Caminho do Arquivo': '`src/domain/Interfaces/IRepositorio.cs`'}
    assert not StepDependencyAnalyzer.are_steps_dependent(step1, step2)

def test_edge_case_empty_path():
    step1 = {'Caminho do Arquivo': ''}
    step2 = {'Caminho do Arquivo': '`src/domain/Entities/Entidade.cs`'}
    assert not StepDependencyAnalyzer.are_steps_dependent(step1, step2)
