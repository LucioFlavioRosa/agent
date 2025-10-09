def _processar_mudancas_comuns(conjunto_de_mudancas):
    mudancas_validas = []
    mudancas_exclusao = []
    for mudanca in conjunto_de_mudancas:
        status = mudanca.get('status', '').upper()
        if status == 'DELETE':
            mudancas_exclusao.append(mudanca)
        elif status in ['CRIADO', 'CRIAR', 'MODIFICADO', 'MODIFICAR', 'CREATE', 'MODIFY']:
            mudancas_validas.append(mudanca)
    return mudancas_validas, mudancas_exclusao
