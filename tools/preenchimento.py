# Arquivo: tools/preenchimento.py (VERSÃO FINAL, ROBUSTA E COM LOGS)

import json
from domain.interfaces.changeset_filler_interface import IChangesetFiller

class ChangesetFiller(IChangesetFiller):
    """
    Implementação robusta para preenchimento de conjuntos de mudanças,
    com logging detalhado para depuração.
    """
    def main(self, json_agrupado: dict, json_inicial: dict) -> dict:
        print("\n" + "="*50)
        print("INICIANDO PROCESSO DE PREENCHIMENTO (ChangesetFiller)")
        print("="*50)

        # Validação crucial dos inputs
        if not isinstance(json_inicial, dict) or not json_inicial.get('conjunto_de_mudancas'):
            print("AVISO CRÍTICO: O JSON inicial (resultado_refatoracao) está vazio ou não contém 'conjunto_de_mudancas'. Não há dados para preencher.")
            return {}

        if not isinstance(json_agrupado, dict):
            print(f"AVISO CRÍTICO: O JSON agrupado não é um dicionário válido. Tipo recebido: {type(json_agrupado)}. Nada a processar.")
            return {}

        mapa_de_mudancas_originais = {
            mudanca['caminho_do_arquivo']: mudanca
            for mudanca in json_inicial.get('conjunto_de_mudancas', [])
        }
        print(f"Mapa de dados originais criado com {len(mapa_de_mudancas_originais)} arquivos.")

        # Cria uma nova estrutura de resultado para não modificar o input
        resultado_preenchido = {}
        
        # Itera sobre os itens do dicionário de grupos
        for nome_do_grupo, dados_do_grupo in json_agrupado.items():
            # Pula chaves que não são de grupos, como 'resumo_geral'
            if not isinstance(dados_do_grupo, dict) or 'conjunto_de_mudancas' not in dados_do_grupo:
                print(f"Ignorando a chave de alto nível '{nome_do_grupo}' (não parece ser um grupo de mudanças).")
                # Copia a chave para o resultado final, se for útil (como o resumo)
                if nome_do_grupo == "resumo_geral":
                    resultado_preenchido[nome_do_grupo] = dados_do_grupo
                continue

            print(f"\n--- Processando grupo: '{nome_do_grupo}' ---")
            conjunto_do_grupo_leve = dados_do_grupo.get('conjunto_de_mudancas', [])
            conjunto_preenchido = []
            
            print(f"O grupo leve contém {len(conjunto_do_grupo_leve)} arquivos.")

            for mudanca_leve in conjunto_do_grupo_leve:
                caminho_do_arquivo = mudanca_leve.get('caminho_do_arquivo')
                
                if not caminho_do_arquivo:
                    print("  AVISO: Item de mudança sem 'caminho_do_arquivo' será ignorado.")
                    continue
                
                # Procura a mudança completa no mapa original
                if caminho_do_arquivo in mapa_de_mudancas_originais:
                    mudanca_completa = mapa_de_mudancas_originais[caminho_do_arquivo]
                    
                    # Garante que a chave "conteudo" exista
                    if "conteudo" not in mudanca_completa and "codigo_novo" in mudanca_completa:
                        mudanca_completa["conteudo"] = mudanca_completa["codigo_novo"]

                    if mudanca_completa.get("conteudo") is not None:
                        print(f"  [SUCESSO] Detalhes de '{caminho_do_arquivo}' encontrados e preenchidos.")
                        conjunto_preenchido.append(mudanca_completa)
                    else:
                        print(f"  [AVISO] Detalhes de '{caminho_do_arquivo}' encontrados, mas sem conteúdo ('conteudo' ou 'codigo_novo'). Ignorando.")
                else:
                    print(f"  [ERRO] Detalhes para '{caminho_do_arquivo}' NÃO encontrados no JSON inicial. Ignorando.")

            # Cria a estrutura final para este grupo, apenas se houver mudanças preenchidas
            if conjunto_preenchido:
                resultado_preenchido[nome_do_grupo] = {
                    **dados_do_grupo, # Copia outras chaves como 'titulo_pr', etc.
                    'conjunto_de_mudancas': conjunto_preenchido
                }
                print(f"--- Grupo '{nome_do_grupo}' finalizado com {len(conjunto_preenchido)} mudanças preenchidas. ---")
            else:
                print(f"--- Grupo '{nome_do_grupo}' finalizado VAZIO. Nenhuma correspondência encontrada. ---")

        print("\n" + "="*50)
        print("PROCESSO DE PREENCHIMENTO CONCLUÍDO")
        print("="*50)
        return resultado_preenchido
