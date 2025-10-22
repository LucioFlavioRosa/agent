import re

class BranchNameSanitizer:
    @staticmethod
    def sanitize(branch_name: str) -> str:
        if not branch_name or not isinstance(branch_name, str):
            return "invalid-branch"
        # Remove caracteres inválidos (Git: ~ ^ : ? * [ \ / @ { }, Azure: também não aceita espaço, ponto final, .., @, etc)
        branch = branch_name.strip().lower()
        branch = branch.replace(' ', '-')
        branch = re.sub(r'[^a-z0-9\-_/]', '', branch)
        branch = re.sub(r'-+', '-', branch)
        branch = re.sub(r'/+', '/', branch)
        branch = branch[:50]
        branch = branch.rstrip('-.')
        if not branch:
            return "invalid-branch"
        # Não pode começar com / ou .
        branch = branch.lstrip('./')
        # Não pode conter sequências proibidas
        if branch in ['.', '..', ''] or branch.startswith('.') or branch.startswith('-') or branch.startswith('/'):
            branch = 'branch-' + branch
        return branch