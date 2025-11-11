import requests

class FeatureReaderService:
    @staticmethod
    def get_feature_title(feature_id: str, organization: str, project: str) -> str:
        url = f"https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/{feature_id}?api-version=7.1-preview.3"
        try:
            print(f"[FeatureReaderService-DEBUG] GET {url}")
            response = requests.get(url)
            print(f"[FeatureReaderService-DEBUG] Status={response.status_code}")
            if response.status_code == 200:
                data = response.json()
                fields = data.get('fields', {})
                title = fields.get('System.Title')
                print(f"[FeatureReaderService-DEBUG] Feature title: {title}")
                return title
            elif response.status_code == 404:
                print(f"[FeatureReaderService-DEBUG] Feature {feature_id} not found (404)")
                raise ValueError(f"Feature {feature_id} not found in Azure DevOps.")
            else:
                print(f"[FeatureReaderService-DEBUG] Error response: {response.text}")
                raise Exception(f"Failed to get feature title: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[FeatureReaderService-DEBUG] Exception: {str(e)}")
            raise
