import re

def sanitize_email(email: str) -> str:
    """
    Limpa o email substituindo caracteres problemáticos por '_'.
    Exemplo: 'user.name+test@example.com' -> 'user_name_test_example_com'
    """
    if not isinstance(email, str):
        raise ValueError("Email deve ser uma string.")
    # Substitui '@', '.', '+', '-', etc. por '_'
    return re.sub(r'[^a-zA-Z0-9]', '_', email)

def build_blob_path(company_id: str, email: str, project_id: str, job_id: str, filename: str) -> str:
    """
    Retorna o caminho do blob no formato:
    {email_sanitizado}/{project_id}/{job_id}/{filename}
    """
    email_sanitizado = sanitize_email(email)
    return f"{email_sanitizado}/{project_id}/{job_id}/{filename}"
