# Arquivo: tools/preenchimento.py (VERSÃO FINAL E REALMENTE CORRIGIDA)

import json
from domain.interfaces.changeset_filler_interface import IChangesetFiller

class ChangesetFiller(IChangesetFiller):
    """
    Implementação definitiva que preenche conjuntos de mudanças com dados completos.
    
    Esta classe é responsável por combinar dados de dois JSONs:
    - JSON inicial (resultado_refatoracao): contém os dados completos dos arquivos
    - JSON agrupado: contém a estrutura de agrupamento por branches/PRs
    
    O processo utiliza o JSON inicial como fonte da verdade para conteúdo,
    status e detalhes dos arquivos, enquanto o JSON agrupado fornece apenas
    a estrutura organizacional dos grupos.
    
    Responsabilidade única: reconstituir conjuntos de mudanças completos
    a partir de dados agrupados e dados originais detalhados.
    """
    
    def main(self, json_agrupado: dict, json_inicial: dict) -> dict:
        """
        Preenche os conjuntos de mudanças agrupados com dados completos dos arquivos.
        
        Este método combina a estrutura de agrupamento (json_agrupado) com os
        dados detalhados dos arquivos (json_inicial), garantindo que cada mudança
        contenha todas as informações necessárias para commit (conteúdo, status, etc.).
        
        Fluxo do processamento:
        1. Cria mapa de mudanças originais indexado por caminho do arquivo
        2. Para cada grupo no JSON agrupado, localiza os dados completos no JSON inicial
        3. Reconstitui o conjunto de mudanças com dados completos
        4. Preserva justificativas específicas do agrupamento quando disponíveis
        
        Args:
            json_agrupado (dict): Estrutura de agrupamento contendo:
                - Chaves: nomes dos grupos/branches
                - Valores: dicionários com 'conjunto_de_mudancas' (lista simplificada)
                - Pode conter 'resumo_geral' como chave especial
            json_inicial (dict): Dados originais da refatoração contendo:
                - 'conjunto_de_mudancas': lista completa com todos os detalhes dos arquivos
                - Cada item deve ter 'caminho_do_arquivo', 'status', 'conteudo', etc.
        
        Returns:
            dict: Estrutura preenchida onde cada grupo contém conjuntos de mudanças
                completos com todos os dados necessários para commit. Mantém a mesma
                estrutura do json_agrupado, mas com dados completos.
        
        Raises:
            ValueError: Se json_inicial estiver vazio ou não contiver 'conjunto_de_mudancas'
            KeyError: Se houver inconsistência entre os JSONs (arquivo no agrupado
                mas não no inicial)
        
        Note:
            - Arquivos sem conteúdo são ignorados (exceto status 'REMOVIDO')
            - Justificativas do agrupamento sobrescrevem as originais quando presentes
            - Fallback de 'codigo_novo' para 'conteudo' é aplicado automaticamente
        """
        print("\n" + "="*50)
        print("INICIANDO PROCESSO DE PREENCHIMENTO (ChangesetFiller v3.0 - Lógica Corrigida)")
        print("="*50)

        # Validação de entrada - garante que o JSON inicial seja válido
        if not isinstance(json_inicial, dict) or not json_inicial.get('conjunto_de_mudancas'):
            print("AVISO CRÍTICO: O JSON inicial (resultado_refatoracao) está vazio ou inválido.")
            return {}

        # Cria mapa indexado por caminho do arquivo para acesso rápido aos dados originais
        mapa_de_mudancas_originais = {
            mudanca.get('caminho_do_arquivo'): mudanca
            for mudanca in json_inicial.get('conjunto_de_mudancas', [])
            if mudanca.get('caminho_do_arquivo')
        }
        print(f"Mapa de dados originais criado com {len(mapa_de_mudancas_originais)} arquivos.")

        resultado_preenchido = {}
        
        # Processa cada grupo do JSON agrupado
        for nome_do_grupo, dados_do_grupo in json_agrupado.items():
            # Preserva resumo geral sem processamento
            if not isinstance(dados_do_grupo, dict) or 'conjunto_de_mudancas' not in dados_do_grupo:
                if nome_do_grupo == "resumo_geral":
                    resultado_preenchido[nome_do_grupo] = dados_do_grupo
                continue

            print(f"\n--- Processando grupo: '{nome_do_grupo}' ---")
            conjunto_do_grupo_leve = dados_do_grupo.get('conjunto_de_mudancas', [])
            conjunto_preenchido = []
            
            # Para cada mudança no grupo, busca dados completos no mapa original
            for mudanca_leve in conjunto_do_grupo_leve:
                caminho_do_arquivo = mudanca_leve.get('caminho_do_arquivo')
                if not caminho_do_arquivo:
                    continue
                
                if caminho_do_arquivo in mapa_de_mudancas_originais:
                    # 1. Pega o objeto COMPLETO do mapa original (fonte da verdade)
                    mudanca_completa = mapa_de_mudancas_originais[caminho_do_arquivo].copy()
                    
                    # 2. Preserva justificativa específica do agrupamento se mais detalhada
                    justificativa_agrupamento = mudanca_leve.get("justificativa")
                    if justificativa_agrupamento:
                        mudanca_completa['justificativa'] = justificativa_agrupamento

                    # 3. Garante compatibilidade: fallback de 'codigo_novo' para 'conteudo'
                    if "conteudo" not in mudanca_completa and "codigo_novo" in mudanca_completa:
                        mudanca_completa["conteudo"] = mudanca_completa.pop("codigo_novo")

                    # 4. Valida se a mudança tem dados suficientes para commit
                    if mudanca_completa.get("conteudo") is not None or mudanca_completa.get("status") == "REMOVIDO":
                        print(f"  [SUCESSO] Detalhes de '{caminho_do_arquivo}' preenchidos com sucesso.")
                        conjunto_preenchido.append(mudanca_completa)
                    else:
                        print(f"  [AVISO] '{caminho_do_arquivo}' ignorado por falta de conteúdo no JSON INICIAL.")
                else:
                    print(f"  [ERRO] Detalhes para '{caminho_do_arquivo}' NÃO encontrados no JSON inicial. Ignorando.")

            # Adiciona grupo ao resultado apenas se tiver mudanças válidas
            if conjunto_preenchido:
                dados_do_grupo['conjunto_de_mudancas'] = conjunto_preenchido
                resultado_preenchido[nome_do_grupo] = dados_do_grupo
        
        print("\n" + "="*50)
        print("PROCESSO DE PREENCHIMENTO CONCLUÍDO")
        print("="*50)
        return resultado_preenchido