class AzureSecretManager:
    def get_secret(self, secret_name):
        # Implementação real de obtenção de segredo
        pass

    def get_repository_token(self, repository_type: str, repo_name: str) -> str:
        if repository_type == 'azure':
            parts = repo_name.split('/')
            if len(parts) != 3:
                raise ValueError(f"Nome do repositório '{repo_name}' tem formato inválido para Azure.")
            org_name = parts[0]
            platform = 'Azure'
        elif repository_type == 'github':
            org_name = repo_name.strip().split('/')[0]
            platform = 'GitHub'
        elif repository_type == 'gitlab':
            org_name = repo_name.strip().split('/')[0]
            platform = 'GitLab'
        else:
            raise ValueError(f"Tipo de repositório '{repository_type}' não suportado para obtenção de token.")
        token_secret_name = f"{platform.lower()}-token-{org_name}"
        try:
            token = self.get_secret(token_secret_name)
            return token
        except Exception:
            try:
                token = self.get_secret(f"{platform.lower()}-token")
                return token
            except Exception:
                raise ValueError(f"Não foi possível obter token para {platform} ({org_name})")
