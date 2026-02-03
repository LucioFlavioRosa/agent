def extract_user_and_company_from_email(user_email: str):
    """
    Extrai o usuário e a empresa de um email no formato 'nome.sobrenome@empresa.com' ou 'nome@empresa.com'.
    Retorna uma tupla (usuario, empresa).
    """
    if not user_email or '@' not in user_email:
        raise ValueError("user_email inválido ou não informado")
    local, domain = user_email.split('@', 1)
    usuario = local.replace('.', '_')
    empresa = domain.split('.', 1)[0].replace('.', '_')
    return usuario, empresa
