def merge_file_content(existing_content: str, new_content: str, merge_strategy: str = 'append') -> str:
    if merge_strategy == 'append':
        existing_content = existing_content or ''
        new_content = new_content or ''
        if not existing_content:
            return new_content
        if not new_content:
            return existing_content
        separator = '\n\n# --- Conteúdo Adicionado Automaticamente ---\n\n'
        return f"{existing_content}{separator}{new_content}"
    raise ValueError(f"Estratégia de merge desconhecida: {merge_strategy}")
