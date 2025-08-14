# Arquivo: tools/preenchimento.py (VERSÃO APRIMORADA)
# [ATENÇÃO] Este módulo deve ser movido para um pacote de domínio/refatoração em etapa futura.

import json
from domain.interfaces.changeset_filler_interface import IChangesetFiller

class ChangesetFiller(IChangesetFiller):
    """
    Implementação concreta para preenchimento/reconstituição de conjuntos de mudanças.
    """
    def main(self, json_agrupado: dict, json_inicial: dict) -> dict:
        print("Iniciando o processo de preenchimento e reconstituição de dados...")
        mapa_de_mudancas_originais = {
            mudanca['caminho_do_arquivo']: mudanca
            for mudanca in json_inicial.get('conjunto_de_mudancas', [])
        }
        print(f"Mapa de dados originais criado com {len(mapa_de_mudancas_originais)} arquivos.")
        for nome_do_grupo, dados_do_grupo in json_agrupado.items():
            if isinstance(dados_do_grupo, dict) and 'conjunto_de_mudancas' in dados_do_grupo:
                print(f"Processando e limpando o grupo: '{nome_do_grupo}'...")
                conjunto_original_do_grupo = dados_do_grupo.get('conjunto_de_mudancas', [])
                novo_conjunto_de_mudancas = []
                for mudanca_no_grupo in conjunto_original_do_grupo:
                    caminho_do_arquivo = mudanca_no_grupo.get('caminho_do_arquivo')
                    if caminho_do_arquivo and caminho_do_arquivo in mapa_de_mudancas_originais:
                        novo_conjunto_de_mudancas.append(mapa_de_mudancas_originais[caminho_do_arquivo])
                    else:
                        print(f"  AVISO: Detalhes para '{caminho_do_arquivo}' não encontrados no JSON inicial. A mudança será ignorada.")
                dados_do_grupo['conjunto_de_mudancas'] = novo_conjunto_de_mudancas
        print("\nProcesso de preenchimento e reconstituição concluído com sucesso!")
        return json_agrupado
