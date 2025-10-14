import requests
import json
from tools.repo_committers.base_committer import BaseCommitter
from tools.repo_committers.path_normalizer import PathNormalizer

class AzureCommitter(BaseCommitter):
    def __init__(self, repository_provider, organization, project, repository_id, branch, token):
        super().__init__(repository_provider)
        self.organization = organization
        self.project = project
        self.repository_id = repository_id
        self.branch = branch
        self.token = token

    def _build_push_payload(self, changes, commit_message, base_commit_id):
        payload_changes = []
        for change in changes:
            action = change.get('action')
            file_path = change.get('path')
            before_path = file_path
            normalized_path = PathNormalizer.normalize(file_path)
            print(f"[DEBUG][AZURE] Normalizando caminho: antes='{before_path}', depois='{normalized_path}'")
            if action in ('add', 'edit'):
                payload_changes.append({
                    'changeType': 'add' if action == 'add' else 'edit',
                    'item': {'path': normalized_path},
                    'newContent': {
                        'content': change.get('content', ''),
                        'contentType': 'raw'
                    }
                })
            elif action == 'delete':
                payload_changes.append({
                    'changeType': 'delete',
                    'item': {'path': normalized_path}
                })
        payload = {
            'refUpdates': [{
                'name': f'refs/heads/{self.branch}',
                'oldObjectId': base_commit_id
            }],
            'commits': [{
                'comment': commit_message,
                'changes': payload_changes
            }]
        }
        return payload

    def push(self, changes, commit_message, base_commit_id):
        url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/git/repositories/{self.repository_id}/pushes?api-version=6.0"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {self.token}'
        }
        payload = self._build_push_payload(changes, commit_message, base_commit_id)
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        return response