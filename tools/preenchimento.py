import json
from domain.interfaces.changeset_filler_interface import IChangesetFiller

class ChangesetFiller(IChangesetFiller):
    
    def main(self, json_agrupado: dict, json_inicial: dict) -> dict:
        print("\n" + "="*50)
        print("INICIANDO PROCESSO DE PREENCHIMENTO (ChangesetFiller v3.0 - Lógica Corrigida)")
        print("="*50)

        if not isinstance(json_inicial, dict) or not json_inicial.get('conjunto_de_mudancas'):
            print("AVISO CRÍTICO: O JSON inicial (resultado_refatoracao) está vazio ou inválido.")
            return {}

        mapa_de_mudancas_originais = {
            mudanca.get('caminho_do_arquivo'): mudanca
            for mudanca in json_inicial.get('conjunto_de_mudancas', [])
            if mudanca.get('caminho_do_arquivo')
        }
        print(f"Mapa de dados originais criado com {len(mapa_de_mudancas_originais)} arquivos.")

        resultado_preenchido = {}
        
        for nome_do_grupo, dados_do_grupo in json_agrupado.items():
            if not isinstance(dados_do_grupo, dict) or 'conjunto_de_mudancas' not in dados_do_grupo:
                if nome_do_grupo == "resumo_geral":
                    resultado_preenchido[nome_do_grupo] = dados_do_grupo
                continue

            print(f"\n--- Processando grupo: '{nome_do_grupo}' ---")
            conjunto_do_grupo_leve = dados_do_grupo.get('conjunto_de_mudancas', [])
            conjunto_preenchido = []
            
            for mudanca_leve in conjunto_do_grupo_leve:
                caminho_do_arquivo = mudanca_leve.get('caminho_do_arquivo')
                if not caminho_do_arquivo:
                    continue
                
                if caminho_do_arquivo in mapa_de_mudancas_originais:
                    mudanca_completa = mapa_de_mudancas_originais[caminho_do_arquivo].copy()
                    
                    justificativa_agrupamento = mudanca_leve.get("justificativa")
                    if justificativa_agrupamento:
                        mudanca_completa['justificativa'] = justificativa_agrupamento

                    if "conteudo" not in mudanca_completa and "codigo_novo" in mudanca_completa:
                        mudanca_completa["conteudo"] = mudanca_completa.pop("codigo_novo")

                    if mudanca_completa.get("conteudo") is not None or mudanca_completa.get("status") == "REMOVIDO":
                        print(f"  [SUCESSO] Detalhes de '{caminho_do_arquivo}' preenchidos com sucesso.")
                        conjunto_preenchido.append(mudanca_completa)
                    else:
                        print(f"  [AVISO] '{caminho_do_arquivo}' ignorado por falta de conteúdo no JSON INICIAL.")
                else:
                    print(f"  [ERRO] Detalhes para '{caminho_do_arquivo}' NÃO encontrados no JSON inicial. Ignorando.")

            if conjunto_preenchido:
                dados_do_grupo['conjunto_de_mudancas'] = conjunto_preenchido
                resultado_preenchido[nome_do_grupo] = dados_do_grupo
        
        print("\n" + "="*50)
        print("PROCESSO DE PREENCHIMENTO CONCLUÍDO")
        print("="*50)
        return resultado_preenchido