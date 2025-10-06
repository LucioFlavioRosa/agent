import unittest
from unittest.mock import patch
from agents import agente_processador

class TestJobIdLogging(unittest.TestCase):
    def test_job_id_logged_in_application_insights(self):
        job_id = "test-job-123"
        projeto = "projeto-teste"
        resultado_da_ia = {
            'tokens_entrada': 100,
            'tokens_saida': 200
        }
        with patch('agents.agente_processador.AgenteProcessador.llm_provider') as mock_llm_provider:
            mock_llm_provider.executar_prompt.return_value = resultado_da_ia
            with patch('agents.logging_utils.log_custom_data') as mock_log:
                agente = agente_processador.AgenteProcessador(mock_llm_provider)
                agente.main(
                    tipo_analise="relatorio_cleancode",
                    codigo={"arquivo.py": "print('hello')"},
                    repository_type="github",
                    repositorio="repo-teste",
                    nome_branch="main",
                    instrucoes_extras="",
                    usar_rag=False,
                    model_name="gpt-4.1",
                    max_token_out=15000,
                    lista_arquivos=None,
                    retornar_lista_arquivos=False,
                    modo_adicao_incremental=False,
                    usuario_executor="tester",
                    job_id=job_id,
                    projeto=projeto
                )
                # Checa se o log_custom_data foi chamado com o job_id correto
                found = False
                for call in mock_log.call_args_list:
                    if 'job_id' in call.kwargs and call.kwargs['job_id'] == job_id:
                        found = True
                        break
                self.assertTrue(found, "job_id não foi logado corretamente no log_custom_data")

if __name__ == '__main__':
    unittest.main()
