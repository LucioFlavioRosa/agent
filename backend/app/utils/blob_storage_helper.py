import re

def sanitize_email(email: str) -> str:
    """
    Sanitiza o email substituindo caracteres problemáticos para uso em caminhos de blob.
    Substitui '@', '.', '+', '-', e outros por '_'.
    """
    if not isinstance(email, str):
        raise ValueError("Email deve ser uma string")
    # Substitui qualquer caractere não alfanumérico por '_'
    return re.sub(r'[^a-zA-Z0-9]', '_', email)

def build_blob_path(company_id: str, email: str, project_id: str, job_id: str, filename: str) -> str:
    """
    Retorna o caminho formatado para o blob:
    {email_sanitizado}/{project_id}/{job_id}/{filename}
    """
    email_sanitizado = sanitize_email(email)
    return f"{email_sanitizado}/{project_id}/{job_id}/{filename}"
