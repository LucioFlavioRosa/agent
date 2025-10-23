import re

def build_cache_key_for_report(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name):
    def sanitize(s):
        if not s:
            return "unknown"
        return re.sub(r'[<>:"|?*\\\\/]', '_', str(s))
    return f"report:{sanitize(projeto)}:{sanitize(analysis_type)}:{sanitize(repository_type)}:{sanitize(repo_name)}:{sanitize(branch_name)}:{sanitize(analysis_name)}"