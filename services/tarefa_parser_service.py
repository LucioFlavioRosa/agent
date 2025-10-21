import json
from typing import List, Optional
from models import TarefaCard

class TarefaParserService:
    @staticmethod
    def parse_tarefas_from_report(report_text: str, epico_id: Optional[str] = None, epico_nome: Optional[str] = None) -> List[TarefaCard]:
        if not report_text:
            print(f"[TarefaParserService] Report text vazio.")
            return []
        tarefas = []
        try:
            # Busca por bloco JSON que contenha 'lista_de_tarefas'
            start = report_text.find('{')
            end = report_text.rfind('}')
            if start != -1 and end != -1:
                json_str = report_text[start:end+1]
                try:
                    report_json = json.loads(json_str)
                except Exception as e:
                    print(f"[TarefaParserService] Erro ao decodificar JSON do relatório: {e}")
                    return []
                lista_de_tarefas = report_json.get('lista_de_tarefas', [])
                if not isinstance(lista_de_tarefas, list):
                    print(f"[TarefaParserService] 'lista_de_tarefas' não é uma lista: {lista_de_tarefas}")
                    return []
                for tarefa_dict in lista_de_tarefas:
                    try:
                        id_tarefa = tarefa_dict.get('id')
                        titulo = tarefa_dict.get('titulo')
                        descricao = tarefa_dict.get('descricao')
                        criterios_aceite = tarefa_dict.get('criterios_de_aceite')
                        perfis = tarefa_dict.get('perfis_sugeridos', [])
                        estimativa_sp = tarefa_dict.get('estimativa_sp')
                        tarefa = TarefaCard(
                            id=id_tarefa,
                            titulo_tarefa=titulo,
                            descricao_tarefa=descricao,
                            epico_id=epico_id if epico_id else '',
                            estimativa_tempo=estimativa_sp,
                            criterios_aceite=criterios_aceite,
                            epico_nome=epico_nome
                        )
                        tarefas.append(tarefa)
                    except Exception as e:
                        print(f"[TarefaParserService] Erro ao parsear tarefa: {e}")
            else:
                print(f"[TarefaParserService] Não foi encontrado bloco JSON válido no relatório.")
        except Exception as e:
            print(f"[TarefaParserService] Erro inesperado no parsing: {e}")
        print(f"[TarefaParserService] Tarefas encontradas para epico_id='{epico_id}', epico_nome='{epico_nome}': {len(tarefas)}")
        return tarefas
