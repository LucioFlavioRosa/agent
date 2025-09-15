import pytest
from tools.preenchimento import ChangesetFiller


class TestChangesetFiller:
    
    def setup_method(self):
        self.filler = ChangesetFiller()
    
    def test_main_with_valid_data(self):
        json_inicial = {
            "conjunto_de_mudancas": [
                {
                    "caminho_do_arquivo": "file1.py",
                    "status": "MODIFICADO",
                    "conteudo": "print('hello world')",
                    "justificativa": "Initial justification"
                },
                {
                    "caminho_do_arquivo": "file2.py",
                    "status": "CRIADO",
                    "conteudo": "def test(): pass",
                    "justificativa": "New file creation"
                }
            ]
        }
        
        json_agrupado = {
            "resumo_geral": "Test summary",
            "grupo1": {
                "resumo_do_pr": "Group 1 PR",
                "descricao_do_pr": "Description for group 1",
                "conjunto_de_mudancas": [
                    {
                        "caminho_do_arquivo": "file1.py",
                        "justificativa": "Updated justification for file1"
                    }
                ]
            },
            "grupo2": {
                "resumo_do_pr": "Group 2 PR",
                "descricao_do_pr": "Description for group 2",
                "conjunto_de_mudancas": [
                    {
                        "caminho_do_arquivo": "file2.py",
                        "justificativa": "Updated justification for file2"
                    }
                ]
            }
        }
        
        result = self.filler.main(json_agrupado, json_inicial)
        
        assert "resumo_geral" in result
        assert result["resumo_geral"] == "Test summary"
        assert "grupo1" in result
        assert "grupo2" in result
        
        grupo1_mudancas = result["grupo1"]["conjunto_de_mudancas"]
        assert len(grupo1_mudancas) == 1
        assert grupo1_mudancas[0]["caminho_do_arquivo"] == "file1.py"
        assert grupo1_mudancas[0]["conteudo"] == "print('hello world')"
        assert grupo1_mudancas[0]["justificativa"] == "Updated justification for file1"
        assert grupo1_mudancas[0]["status"] == "MODIFICADO"
    
    def test_main_with_empty_json_inicial(self):
        json_inicial = {}
        json_agrupado = {
            "grupo1": {
                "conjunto_de_mudancas": [
                    {"caminho_do_arquivo": "file1.py"}
                ]
            }
        }
        
        result = self.filler.main(json_agrupado, json_inicial)
        
        assert result == {}
    
    def test_main_with_none_json_inicial(self):
        json_inicial = None
        json_agrupado = {
            "grupo1": {
                "conjunto_de_mudancas": [
                    {"caminho_do_arquivo": "file1.py"}
                ]
            }
        }
        
        result = self.filler.main(json_agrupado, json_inicial)
        
        assert result == {}
    
    def test_main_with_missing_conjunto_de_mudancas_in_inicial(self):
        json_inicial = {"other_key": "other_value"}
        json_agrupado = {
            "grupo1": {
                "conjunto_de_mudancas": [
                    {"caminho_do_arquivo": "file1.py"}
                ]
            }
        }
        
        result = self.filler.main(json_agrupado, json_inicial)
        
        assert result == {}
    
    def test_main_with_file_not_found_in_inicial(self):
        json_inicial = {
            "conjunto_de_mudancas": [
                {
                    "caminho_do_arquivo": "existing_file.py",
                    "status": "MODIFICADO",
                    "conteudo": "existing content"
                }
            ]
        }
        
        json_agrupado = {
            "grupo1": {
                "conjunto_de_mudancas": [
                    {"caminho_do_arquivo": "missing_file.py"},
                    {"caminho_do_arquivo": "existing_file.py"}
                ]
            }
        }
        
        result = self.filler.main(json_agrupado, json_inicial)
        
        assert "grupo1" in result
        grupo1_mudancas = result["grupo1"]["conjunto_de_mudancas"]
        assert len(grupo1_mudancas) == 1
        assert grupo1_mudancas[0]["caminho_do_arquivo"] == "existing_file.py"
    
    def test_main_with_codigo_novo_field(self):
        json_inicial = {
            "conjunto_de_mudancas": [
                {
                    "caminho_do_arquivo": "legacy_file.py",
                    "status": "MODIFICADO",
                    "codigo_novo": "new code content"
                }
            ]
        }
        
        json_agrupado = {
            "grupo1": {
                "conjunto_de_mudancas": [
                    {"caminho_do_arquivo": "legacy_file.py"}
                ]
            }
        }
        
        result = self.filler.main(json_agrupado, json_inicial)
        
        grupo1_mudancas = result["grupo1"]["conjunto_de_mudancas"]
        assert grupo1_mudancas[0]["conteudo"] == "new code content"
        assert "codigo_novo" not in grupo1_mudancas[0]
    
    def test_main_with_removed_file_status(self):
        json_inicial = {
            "conjunto_de_mudancas": [
                {
                    "caminho_do_arquivo": "removed_file.py",
                    "status": "REMOVIDO",
                    "conteudo": None
                }
            ]
        }
        
        json_agrupado = {
            "grupo1": {
                "conjunto_de_mudancas": [
                    {"caminho_do_arquivo": "removed_file.py"}
                ]
            }
        }
        
        result = self.filler.main(json_agrupado, json_inicial)
        
        grupo1_mudancas = result["grupo1"]["conjunto_de_mudancas"]
        assert len(grupo1_mudancas) == 1
        assert grupo1_mudancas[0]["status"] == "REMOVIDO"
        assert grupo1_mudancas[0]["conteudo"] is None
    
    def test_main_with_file_without_content(self):
        json_inicial = {
            "conjunto_de_mudancas": [
                {
                    "caminho_do_arquivo": "no_content_file.py",
                    "status": "MODIFICADO"
                }
            ]
        }
        
        json_agrupado = {
            "grupo1": {
                "conjunto_de_mudancas": [
                    {"caminho_do_arquivo": "no_content_file.py"}
                ]
            }
        }
        
        result = self.filler.main(json_agrupado, json_inicial)
        
        assert "grupo1" not in result or len(result["grupo1"].get("conjunto_de_mudancas", [])) == 0
    
    def test_main_with_empty_caminho_do_arquivo(self):
        json_inicial = {
            "conjunto_de_mudancas": [
                {
                    "caminho_do_arquivo": "valid_file.py",
                    "status": "MODIFICADO",
                    "conteudo": "valid content"
                }
            ]
        }
        
        json_agrupado = {
            "grupo1": {
                "conjunto_de_mudancas": [
                    {"caminho_do_arquivo": ""},
                    {"caminho_do_arquivo": "valid_file.py"}
                ]
            }
        }
        
        result = self.filler.main(json_agrupado, json_inicial)
        
        grupo1_mudancas = result["grupo1"]["conjunto_de_mudancas"]
        assert len(grupo1_mudancas) == 1
        assert grupo1_mudancas[0]["caminho_do_arquivo"] == "valid_file.py"
    
    def test_main_with_unicode_file_paths_and_content(self):
        json_inicial = {
            "conjunto_de_mudancas": [
                {
                    "caminho_do_arquivo": "测试文件.py",
                    "status": "MODIFICADO",
                    "conteudo": "# Unicode content 🚀\nprint('测试')"
                }
            ]
        }
        
        json_agrupado = {
            "grupo_unicode": {
                "resumo_do_pr": "Unicode PR 📝",
                "conjunto_de_mudancas": [
                    {
                        "caminho_do_arquivo": "测试文件.py",
                        "justificativa": "Unicode justification 🎯"
                    }
                ]
            }
        }
        
        result = self.filler.main(json_agrupado, json_inicial)
        
        assert "grupo_unicode" in result
        mudancas = result["grupo_unicode"]["conjunto_de_mudancas"]
        assert len(mudancas) == 1
        assert mudancas[0]["caminho_do_arquivo"] == "测试文件.py"
        assert "测试" in mudancas[0]["conteudo"]
        assert "🚀" in mudancas[0]["conteudo"]
        assert mudancas[0]["justificativa"] == "Unicode justification 🎯"
    
    def test_main_with_complex_nested_structure(self):
        json_inicial = {
            "conjunto_de_mudancas": [
                {
                    "caminho_do_arquivo": "complex/nested/file.py",
                    "status": "CRIADO",
                    "conteudo": "complex content",
                    "metadata": {"author": "test", "version": "1.0"}
                }
            ]
        }
        
        json_agrupado = {
            "resumo_geral": "Complex test",
            "complex_grupo": {
                "resumo_do_pr": "Complex changes",
                "descricao_do_pr": "Detailed description",
                "conjunto_de_mudancas": [
                    {
                        "caminho_do_arquivo": "complex/nested/file.py",
                        "justificativa": "Complex justification"
                    }
                ],
                "extra_metadata": {"priority": "high"}
            }
        }
        
        result = self.filler.main(json_agrupado, json_inicial)
        
        assert result["resumo_geral"] == "Complex test"
        assert "complex_grupo" in result
        assert result["complex_grupo"]["extra_metadata"]["priority"] == "high"
        
        mudancas = result["complex_grupo"]["conjunto_de_mudancas"]
        assert mudancas[0]["metadata"]["author"] == "test"
        assert mudancas[0]["justificativa"] == "Complex justification"