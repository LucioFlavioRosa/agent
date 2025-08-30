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
        1. Valida rigorosamente os dados de entrada
        2. Cria mapa de mudanças originais indexado por caminho do arquivo
        3. Para cada grupo no JSON agrupado, localiza os dados completos no JSON inicial
        4. Reconstitui o conjunto de mudanças com dados completos
        5. Preserva justificativas específicas do agrupamento quando disponíveis
        
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
            ValueError: Se json_inicial estiver vazio, não contiver 'conjunto_de_mudancas',
                ou se json_agrupado for inválido
            TypeError: Se os parâmetros não forem dicionários
        
        Note:
            - Arquivos sem conteúdo são ignorados (exceto status 'REMOVIDO')
            - Justificativas do agrupamento sobrescrevem as originais quando presentes
            - Fallback de 'codigo_novo' para 'conteudo' é aplicado automaticamente
            - Validação rigorosa previne erros de integração em etapas posteriores
        """
        print("\n" + "="*50)
        print("INICIANDO PROCESSO DE PREENCHIMENTO (ChangesetFiller v4.0 - Com Validação Rigorosa)")
        print("="*50)

        # VALIDAÇÃO CRÍTICA 1: Verificar tipos dos parâmetros
        if not isinstance(json_inicial, dict):
            raise TypeError(f"json_inicial deve ser um dicionário, recebido: {type(json_inicial).__name__}")
        
        if not isinstance(json_agrupado, dict):
            raise TypeError(f"json_agrupado deve ser um dicionário, recebido: {type(json_agrupado).__name__}")
        
        # VALIDAÇÃO CRÍTICA 2: Verificar se json_inicial contém dados válidos
        if not json_inicial:
            raise ValueError("ERRO CRÍTICO: O JSON inicial (resultado_refatoracao) está vazio. Não é possível prosseguir sem dados de origem.")
        
        conjunto_mudancas_inicial = json_inicial.get('conjunto_de_mudancas')
        if conjunto_mudancas_inicial is None:
            raise ValueError("ERRO CRÍTICO: O JSON inicial não contém a chave obrigatória 'conjunto_de_mudancas'. Estrutura de dados inválida.")
        
        if not isinstance(conjunto_mudancas_inicial, list):
            raise ValueError(f"ERRO CRÍTICO: A chave 'conjunto_de_mudancas' deve ser uma lista, encontrado: {type(conjunto_mudancas_inicial).__name__}")
        
        if not conjunto_mudancas_inicial:
            raise ValueError("ERRO CRÍTICO: A lista 'conjunto_de_mudancas' no JSON inicial está vazia. Não há dados para processar.")
        
        # VALIDAÇÃO CRÍTICA 3: Verificar se json_agrupado contém dados válidos
        if not json_agrupado:
            print("AVISO: O JSON agrupado está vazio. Retornando estrutura vazia.")
            return {}
        
        print(f"Validação concluída: JSON inicial contém {len(conjunto_mudancas_inicial)} mudanças.")
        print(f"JSON agrupado contém {len(json_agrupado)} grupos para processar.")

        # Cria mapa indexado por caminho do arquivo para acesso rápido aos dados originais
        mapa_de_mudancas_originais = {}
        mudancas_sem_caminho = 0
        
        for mudanca in conjunto_mudancas_inicial:
            caminho = mudanca.get('caminho_do_arquivo')
            if caminho:
                mapa_de_mudancas_originais[caminho] = mudanca
            else:
                mudancas_sem_caminho += 1
        
        if mudancas_sem_caminho > 0:
            print(f"AVISO: {mudancas_sem_caminho} mudanças no JSON inicial não possuem 'caminho_do_arquivo' e serão ignoradas.")
        
        print(f"Mapa de dados originais criado com {len(mapa_de_mudancas_originais)} arquivos válidos.")

        resultado_preenchido = {}
        grupos_processados = 0
        grupos_ignorados = 0
        
        # Processa cada grupo do JSON agrupado
        for nome_do_grupo, dados_do_grupo in json_agrupado.items():
            # Preserva resumo geral sem processamento
            if nome_do_grupo == "resumo_geral":
                resultado_preenchido[nome_do_grupo] = dados_do_grupo
                continue
            
            # Valida estrutura do grupo
            if not isinstance(dados_do_grupo, dict):
                print(f"AVISO: Grupo '{nome_do_grupo}' não é um dicionário. Ignorando.")
                grupos_ignorados += 1
                continue
            
            if 'conjunto_de_mudancas' not in dados_do_grupo:
                print(f"AVISO: Grupo '{nome_do_grupo}' não contém 'conjunto_de_mudancas'. Ignorando.")
                grupos_ignorados += 1
                continue

            print(f"\n--- Processando grupo: '{nome_do_grupo}' ---")
            conjunto_do_grupo_leve = dados_do_grupo.get('conjunto_de_mudancas', [])
            
            if not isinstance(conjunto_do_grupo_leve, list):
                print(f"AVISO: 'conjunto_de_mudancas' do grupo '{nome_do_grupo}' não é uma lista. Ignorando grupo.")
                grupos_ignorados += 1
                continue
            
            conjunto_preenchido = []
            mudancas_processadas = 0
            mudancas_ignoradas = 0
            
            # Para cada mudança no grupo, busca dados completos no mapa original
            for mudanca_leve in conjunto_do_grupo_leve:
                if not isinstance(mudanca_leve, dict):
                    mudancas_ignoradas += 1
                    continue
                
                caminho_do_arquivo = mudanca_leve.get('caminho_do_arquivo')
                if not caminho_do_arquivo:
                    mudancas_ignoradas += 1
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
                        mudancas_processadas += 1
                    else:
                        print(f"  [AVISO] '{caminho_do_arquivo}' ignorado por falta de conteúdo no JSON INICIAL.")
                        mudancas_ignoradas += 1
                else:
                    print(f"  [ERRO] Detalhes para '{caminho_do_arquivo}' NÃO encontrados no JSON inicial. Ignorando.")
                    mudancas_ignoradas += 1

            # Adiciona grupo ao resultado apenas se tiver mudanças válidas
            if conjunto_preenchido:
                dados_do_grupo['conjunto_de_mudancas'] = conjunto_preenchido
                resultado_preenchido[nome_do_grupo] = dados_do_grupo
                grupos_processados += 1
                print(f"Grupo '{nome_do_grupo}' processado: {mudancas_processadas} mudanças válidas, {mudancas_ignoradas} ignoradas.")
            else:
                print(f"AVISO: Grupo '{nome_do_grupo}' não contém mudanças válidas e será omitido do resultado.")
                grupos_ignorados += 1
        
        print("\n" + "="*50)
        print("PROCESSO DE PREENCHIMENTO CONCLUÍDO COM VALIDAÇÃO RIGOROSA")
        print(f"Grupos processados: {grupos_processados}")
        print(f"Grupos ignorados: {grupos_ignorados}")
        print("="*50)
        
        # VALIDAÇÃO FINAL: Garantir que o resultado não está vazio se havia dados para processar
        if not resultado_preenchido and json_agrupado:
            print("AVISO CRÍTICO: Nenhum grupo foi processado com sucesso. Verifique a compatibilidade entre os JSONs.")
        
        return resultado_preenchido