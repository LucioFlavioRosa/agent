# Arquivo: tools/preenchimento.py (VERSÃO APRIMORADA)

import json

def main(json_agrupado: dict, json_inicial: dict) -> dict:
    """
    Preenche e reconstitui os dados no JSON agrupado usando o JSON inicial como
    fonte da verdade, garantindo a integridade de todas as chaves de cada mudança.

    :param json_agrupado: Dicionário com os grupos de mudanças, potencialmente incompletos.
    :param json_inicial: Dicionário original com a lista completa e correta das mudanças.
    :return: O dicionário 'json_agrupado' modificado e totalmente preenchido.
    """
    print("Iniciando o processo de preenchimento e reconstituição de dados...")

    # Passo 1: Criar um mapa de consulta para o OBJETO DE MUDANÇA COMPLETO.
    # A chave é o caminho do arquivo, o valor é o dicionário inteiro da mudança.
    mapa_de_mudancas_originais = {
        mudanca['caminho_do_arquivo']: mudanca
        for mudanca in json_inicial.get('conjunto_de_mudancas', [])
    }
    print(f"Mapa de dados originais criado com {len(mapa_de_mudancas_originais)} arquivos.")

    # Passo 2: Iterar sobre cada grupo no JSON agrupado.
    for nome_do_grupo, dados_do_grupo in json_agrupado.items():
        if isinstance(dados_do_grupo, dict) and 'conjunto_de_mudancas' in dados_do_grupo:
            print(f"Processando e limpando o grupo: '{nome_do_grupo}'...")
            
            conjunto_original_do_grupo = dados_do_grupo.get('conjunto_de_mudancas', [])
            novo_conjunto_de_mudancas = [] # Uma nova lista para garantir dados limpos

            # Passo 3: Iterar sobre cada mudança listada pelo agente de agrupamento.
            for mudanca_no_grupo in conjunto_original_do_grupo:
                caminho_do_arquivo = mudanca_no_grupo.get('caminho_do_arquivo')
                
                # Passo 4: Buscar o objeto de mudança completo no mapa original.
                if caminho_do_arquivo and caminho_do_arquivo in mapa_de_mudancas_originais:
                    # Adiciona o objeto original e completo à nova lista.
                    # Isso garante que 'conteudo', 'justificativa', etc., estejam presentes e corretos.
                    novo_conjunto_de_mudancas.append(mapa_de_mudancas_originais[caminho_do_arquivo])
                else:
                    print(f"  AVISO: Detalhes para '{caminho_do_arquivo}' não encontrados no JSON inicial. A mudança será ignorada.")
            
            # Passo 5: Substitui a lista de mudanças potencialmente incompleta pela nova lista reconstituída.
            dados_do_grupo['conjunto_de_mudancas'] = novo_conjunto_de_mudancas
    
    print("\nProcesso de preenchimento e reconstituição concluído com sucesso!")
    return json_agrupado
