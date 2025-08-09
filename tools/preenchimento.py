import json

def main(json_agrupado: dict, json_inicial: dict) -> dict:
    """
    Preenche a chave 'conteudo' no JSON agrupado usando os dados do JSON inicial.

    A função opera "in-place", ou seja, modifica o dicionário 'json_agrupado' diretamente.

    :param json_agrupado: O dicionário com os grupos de mudanças, mas sem o conteúdo.
    :param json_inicial: O dicionário original que contém a lista completa de
                         mudanças com o conteúdo dos arquivos.
    :return: O dicionário 'json_agrupado' modificado e preenchido.
    """
    print("Iniciando o processo de preenchimento de conteúdo...")

    # Passo 1: Criar um mapa de consulta rápida para o conteúdo dos arquivos.
    # Isso é muito mais eficiente do que pesquisar na lista original repetidamente.
    mapa_de_conteudo = {
        mudanca['caminho_do_arquivo']: mudanca['conteudo']
        for mudanca in json_inicial.get('conjunto_de_mudancas', [])
    }
    print(f"Mapa de conteúdo criado com {len(mapa_de_conteudo)} arquivos.")

    # Passo 2: Iterar sobre cada grupo no JSON agrupado.
    # O loop ignora chaves de nível superior que não são grupos (como 'resumo_geral').
    for nome_do_conjunto, dados_do_conjunto in json_agrupado.items():
        if isinstance(dados_do_conjunto, dict) and 'conjunto_de_mudancas' in dados_do_conjunto:
            print(f"Processando o grupo: '{nome_do_conjunto}'...")
            
            # Passo 3: Iterar sobre cada mudança dentro do grupo.
            for mudanca_no_grupo in dados_do_conjunto.get('conjunto_de_mudancas', []):
                caminho_do_arquivo = mudanca_no_grupo.get('caminho_do_arquivo')
                
                # Passo 4: Buscar o conteúdo no mapa e preencher a chave 'conteudo'.
                if caminho_do_arquivo in mapa_de_conteudo:
                    mudanca_no_grupo['conteudo'] = mapa_de_conteudo[caminho_do_arquivo]
                else:
                    # Caso de segurança: se um arquivo no grupo não estiver no original.
                    mudanca_no_grupo['conteudo'] = None
                    print(f"  AVISO: Conteúdo para '{caminho_do_arquivo}' não encontrado no JSON inicial.")
    
    print("\nProcesso de preenchimento concluído com sucesso!")
    return json_agrupado