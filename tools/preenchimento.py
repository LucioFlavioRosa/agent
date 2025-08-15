# Arquivo: tools/preenchimento.py (VERSÃO FINAL E ROBUSTA COM NORMALIZAÇÃO)

import json
from domain.interfaces.changeset_filler_interface import IChangesetFiller

def _normalize_path(path: str) -> str:
    """Função auxiliar para limpar e padronizar um caminho de arquivo."""
    if not isinstance(path, str):
        return ""
    # Remove o prefixo './' se existir
    if path.startswith('./'):
        path = path[2:]
    # Remove espaços em branco no início e no fim
    return path.strip()

class ChangesetFiller(IChangesetFiller):
    """
    Implementação final que normaliza os caminhos dos arquivos para garantir
    uma correspondência robusta entre as saídas dos agentes.
    """
    def main(self, json_agrupado: dict, json_inicial: dict) -> dict:
        print("\n" + "="*50)
        print("INICIANDO PROCESSO DE PREENCHIMENTO (ChangesetFiller v2.0 - com Normalização)")
        print("="*50)

        if not isinstance(json_inicial, dict) or not json_inicial.get('conjunto_de_mudancas'):
            print("AVISO CRÍTICO: O JSON inicial (resultado_refatoracao) está vazio ou inválido.")
            return {}

        # MUDANÇA CRÍTICA: As chaves do mapa agora são os caminhos NORMALIZADOS
        mapa_de_mudancas_originais = {
            _normalize_path(mudanca.get('caminho_do_arquivo')): mudanca
            for mudanca in json_inicial.get('conjunto_de_mudancas', [])
            if mudanca.get('caminho_do_arquivo')
        }
        print(f"Mapa de dados originais criado com {len(mapa_de_mudancas_originais)} arquivos (caminhos normalizados).")

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
                caminho_original = mudanca_leve.get('caminho_do_arquivo')
                if not caminho_original:
                    continue
                
                # MUDANÇA CRÍTICA: Busca no mapa usando o caminho NORMALIZADO
                caminho_normalizado = _normalize_path(caminho_original)
                
                if caminho_normalizado in mapa_de_mudancas_originais:
                    mudanca_completa = mapa_de_mudancas_originais[caminho_normalizado].copy()
                    
                    if "conteudo" not in mudanca_completa and "codigo_novo" in mudanca_completa:
                        mudanca_completa["conteudo"] = mudanca_completa.pop("codigo_novo")

                    if mudanca_completa.get("conteudo") is not None or mudanca_completa.get("status") == "REMOVIDO":
                        print(f"  [SUCESSO] Match encontrado para '{caminho_original}' (normalizado para '{caminho_normalizado}'). Conteúdo preenchido.")
                        conjunto_preenchido.append(mudanca_completa)
                    else:
                        print(f"  [AVISO] Match para '{caminho_original}' encontrado, mas sem conteúdo. Ignorando.")
                else:
                    print(f"  [ERRO] Match para '{caminho_original}' (normalizado para '{caminho_normalizado}') NÃO encontrado no mapa. Ignorando.")

            if conjunto_preenchido:
                dados_do_grupo['conjunto_de_mudancas'] = conjunto_preenchido
                resultado_preenchido[nome_do_grupo] = dados_do_grupo
        
        print("\n" + "="*50)
        print("PROCESSO DE PREENCHIMENTO CONCLUÍDO")
        print("="*50)
        return resultado_preenchido
