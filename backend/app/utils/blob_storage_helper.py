import re


def sanitize_email(email: str) -> str:
    """
    Sanitiza o email para uso em caminhos de blob:
    - Remove caracteres inválidos para path
    - Substitui '@' e '.' por '_'
    """
    if not email or not isinstance(email, str):
        raise ValueError("Email inválido para sanitização.")
    # Substitui '@' e '.' por '_'
    sanitized = email.replace('@', '_').replace('.', '_')
    # Remove caracteres não permitidos em paths (apenas alfanuméricos, '_', '-', e '+')
    sanitized = re.sub(r'[^a-zA-Z0-9_\-+]', '', sanitized)
    return sanitized


def build_blob_path(company_id: str, email: str, project_id: str, job_id: str, filename: str) -> str:
    """
    Monta o caminho completo para o blob:
    company_id/email_sanitizado/project_id/job_id/filename
    Valida que todos os parâmetros são não-nulos e não-vazios.
    """
    params = [company_id, email, project_id, job_id, filename]
    if any(p is None or str(p).strip() == '' for p in params):
        raise ValueError("Todos os parâmetros devem ser não-nulos e não-vazios.")
    email_sanitized = sanitize_email(email)
    path = f"{company_id}/{email_sanitized}/{project_id}/{job_id}/{filename}"
    return path
