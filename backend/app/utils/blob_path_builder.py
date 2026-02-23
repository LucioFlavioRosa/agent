import re

def sanitize_email(email: str) -> str:
    """
    Substitui '@' por '_at_' e '.' por '_', removendo outros caracteres não permitidos.
    """
    sanitized = email.replace('@', '_at_').replace('.', '_')
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', sanitized)
    return sanitized

def build_blob_path(company_id: str, email: str, project_id: str, job_id: str, filename: str) -> str:
    """
    Retorna o caminho estruturado para o blob storage:
    company_id/email/project_id/job_id/filename
    """
    sanitized_email = sanitize_email(email)
    path = f"{company_id}/{sanitized_email}/{project_id}/{job_id}/{filename}"
    return path
