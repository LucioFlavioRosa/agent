from github import Github
from github.Auth import Token
from google.colab import userdata

def connection(repositorio: str):
    GITHUB_TOKEN = userdata.get('github_token')
    auth = Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    return g.get_repo(repositorio)