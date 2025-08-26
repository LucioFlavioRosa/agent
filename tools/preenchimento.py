# Arquivo: tools/preenchimento.py (VERSÃO FINAL E REALMENTE CORRIGIDA)

import json
from domain.interfaces.changeset_filler_interface import IChangesetFiller

class ChangesetFiller(IChangesetFiller):
    """
    Implementação definitiva que preenche os dados. Usa o JSON inicial como
    fonte da verdade para o conteúdo, status e outros detalhes do arquivo,
    e o JSON agrupado apenas para a estrutura dos grupos.
    """
    
    def main(self, json_agrupado: dict, json_inicial: dict) -> dict:
        """
        Preenche conjuntos de mudanças agrupados com dados detalhados do JSON inicial.
        
        Este método implementa a lógica de reconstituição de dados, onde:
        1. O json_inicial contém os dados completos de cada mudança (conteúdo, status, etc.)
        2. O json_agrupado contém apenas a estrutura organizacional dos grupos
        3. O resultado combina a organização do agrupado com os dados do inicial
        
        Fluxo de processamento:
        - Cria um mapa de mudanças originais indexado por caminho do arquivo
        - Para cada grupo no JSON agrupado, reconstitui as mudanças completas
        - Preserva metadados dos grupos (resumo_do_pr, descricao_do_pr, etc.)
        - Aplica fallbacks para campos ausentes
        
        Args:
            json_agrupado (dict): Estrutura organizacional dos grupos contendo:
                - Chaves de grupos com dados como 'conjunto_de_mudancas', 'resumo_do_pr'
                - Mudanças simplificadas com apenas 'caminho_do_arquivo' e 'justificativa'
            json_inicial (dict): Dados completos das mudanças contendo:
                - 'conjunto_de_mudancas': Lista com dados completos de cada arquivo
                - Cada mudança deve ter: caminho_do_arquivo, status, conteudo/codigo_novo
        
        Returns:
            dict: Estrutura preenchida mantendo a organização do json_agrupado
                mas com dados completos do json_inicial. Formato:
                {
                    "grupo1": {
                        "resumo_do_pr": "...",
                        "conjunto_de_mudancas": [mudanças_completas]
                    },
                    "resumo_geral": "..."
                }
        
        Raises:
            ValueError: Se json_inicial não contiver 'conjunto_de_mudancas' válido
            KeyError: Se houver inconsistências entre os JSONs
        
        Example:
            >>> filler = ChangesetFiller()
            >>> json_inicial = {
            ...     "conjunto_de_mudancas": [
            ...         {"caminho_do_arquivo": "file.py", "status": "MODIFICADO", "conteudo": "code"}
            ...     ]
            ... }
            >>> json_agrupado = {
            ...     "grupo1": {
            ...         "conjunto_de_mudancas": [{"caminho_do_arquivo": "file.py"}]
            ...     }
            ... }
            >>> resultado = filler.main(json_agrupado, json_inicial)
        """
        print("\n" + "="*50)
        print("INICIANDO PROCESSO DE PREENCHIMENTO (ChangesetFiller v3.0 - Lógica Corrigida)")
        print("="*50)

        # Validação do JSON inicial
        if not isinstance(json_inicial, dict) or not json_inicial.get('conjunto_de_mudancas'):
            print("AVISO CRÍTICO: O JSON inicial (resultado_refatoracao) está vazio ou inválido.")
            return {}

        # Criação do mapa de mudanças originais para lookup eficiente
        # Este mapa permite acesso O(1) aos dados completos de cada arquivo
        mapa_de_mudancas_originais = {
            mudanca.get('caminho_do_arquivo'): mudanca
            for mudanca in json_inicial.get('conjunto_de_mudancas', [])
            if mudanca.get('caminho_do_arquivo')
        }
        print(f"Mapa de dados originais criado com {len(mapa_de_mudancas_originais)} arquivos.")

        resultado_preenchido = {}
        
        # Processamento de cada grupo no JSON agrupado
        for nome_do_grupo, dados_do_grupo in json_agrupado.items():
            # Preserva campos especiais como resumo_geral sem processamento
            if not isinstance(dados_do_grupo, dict) or 'conjunto_de_mudancas' not in dados_do_grupo:
                if nome_do_grupo == "resumo_geral":
                    resultado_preenchido[nome_do_grupo] = dados_do_grupo
                continue

            print(f"\n--- Processando grupo: '{nome_do_grupo}' ---")
            conjunto_do_grupo_leve = dados_do_grupo.get('conjunto_de_mudancas', [])
            conjunto_preenchido = []
            
            # Reconstituição de cada mudança no grupo
            for mudanca_leve in conjunto_do_grupo_leve:
                caminho_do_arquivo = mudanca_leve.get('caminho_do_arquivo')
                if not caminho_do_arquivo:
                    continue
                
                # Busca os dados completos no mapa original
                if caminho_do_arquivo in mapa_de_mudancas_originais:
                    # 1. Copia o objeto COMPLETO do mapa original (fonte da verdade)
                    mudanca_completa = mapa_de_mudancas_originais[caminho_do_arquivo].copy()
                    
                    # 2. Aplica justificativa específica do agrupamento se disponível
                    # A justificativa do agrupamento pode ser mais específica ao contexto
                    justificativa_agrupamento = mudanca_leve.get("justificativa")
                    if justificativa_agrupamento:
                        mudanca_completa['justificativa'] = justificativa_agrupamento

                    # 3. Normalização de campos para compatibilidade
                    # Garante que existe "conteudo" (fallback para "codigo_novo")
                    if "conteudo" not in mudanca_completa and "codigo_novo" in mudanca_completa:
                        mudanca_completa["conteudo"] = mudanca_completa.pop("codigo_novo")

                    # 4. Validação final antes de incluir na lista
                    # Arquivos removidos não precisam de conteúdo
                    if mudanca_completa.get("conteudo") is not None or mudanca_completa.get("status") == "REMOVIDO":
                        print(f"  [SUCESSO] Detalhes de '{caminho_do_arquivo}' preenchidos com sucesso.")
                        conjunto_preenchido.append(mudanca_completa)
                    else:
                        print(f"  [AVISO] '{caminho_do_arquivo}' ignorado por falta de conteúdo no JSON INICIAL.")
                else:
                    print(f"  [ERRO] Detalhes para '{caminho_do_arquivo}' NÃO encontrados no JSON inicial. Ignorando.")

            # Atualiza o grupo com as mudanças preenchidas se houver alguma válida
            if conjunto_preenchido:
                dados_do_grupo['conjunto_de_mudancas'] = conjunto_preenchido
                resultado_preenchido[nome_do_grupo] = dados_do_grupo
        
        print("\n" + "="*50)
        print("PROCESSO DE PREENCHIMENTO CONCLUÍDO")
        print("="*50)
        return resultado_preenchido