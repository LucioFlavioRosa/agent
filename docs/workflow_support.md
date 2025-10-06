# Suporte e Detalhes Técnicos do Workflow - MCP Server

Este documento complementa `docs/workflow.md`, fornecendo explicações técnicas adicionais sobre como os workflows são carregados, validados e utilizados pelo MCP Server.

---

## 1. Carregamento dos Workflows

Os workflows são definidos em arquivos YAML (por padrão, `workflows.yaml`) e carregados pelo serviço `WorkflowRegistryLoader`. O carregamento suporta múltiplos documentos YAML no mesmo arquivo (streaming YAML), permitindo a definição de vários workflows.

### Código-chave
python
class WorkflowRegistryLoader:
    def __init__(self, workflow_file_path: str = "workflows.yaml"):
        self.workflow_file_path = workflow_file_path
    
    def load_workflows(self) -> Dict[str, Any]:
        print(f"Carregando workflows do arquivo: {self.workflow_file_path}")
        workflows = {}
        
        try:
            with open(self.workflow_file_path, 'r', encoding='utf-8') as f:
                for document in yaml.safe_load_all(f):
                    if document:
                        workflows.update(document)
        except yaml.YAMLError as e:
            print(f"Erro ao processar YAML em streaming: {e}")
            with open(self.workflow_file_path, 'r', encoding='utf-8') as f:
                workflows = yaml.safe_load(f)
        
        return workflows


- **Resiliência:** Se o carregamento em streaming falhar, faz fallback para leitura padrão.
- **Extensibilidade:** Novos tipos de workflow podem ser adicionados facilmente ao YAML.

---

## 2. Serviço de Registro de Workflows

O serviço `WorkflowRegistryService` encapsula o loader e expõe métodos para acessar workflows e tipos válidos de análise:

python
class WorkflowRegistryService:
    def __init__(self, workflow_file_path: str = "workflows.yaml"):
        self._workflow_registry = None
        self._loader = WorkflowRegistryLoader(workflow_file_path)
        self._analysis_type_provider = AnalysisTypeProvider()
    
    def load_workflow_registry(self) -> Dict[str, Any]:
        if self._workflow_registry is None:
            self._workflow_registry = self._loader.load_workflows()
        
        return self._workflow_registry
    
    def get_valid_analysis_types(self):
        workflow_registry = self.load_workflow_registry()
        return self._analysis_type_provider.get_valid_analysis_types(workflow_registry)
    
    def get_workflow_registry(self) -> Dict[str, Any]:
        return self.load_workflow_registry()


- **Cache:** O registro de workflows é carregado uma vez e mantido em cache na instância.
- **Integração:** Fornece tipos válidos de análise para validação de payloads da API.

---

## 3. Integração com a API FastAPI

No arquivo `mcp_server_fastapi.py`, o serviço de workflow é inicializado e os tipos válidos de análise são usados para validar o payload da rota `/start-analysis`:

python
workflow_registry_service = container.get_workflow_registry_service()
ValidAnalysisTypes = workflow_registry_service.get_valid_analysis_types()

class StartAnalysisPayload(BaseModel):
    ...
    analysis_type: ValidAnalysisTypes
    ...


- **Validação Dinâmica:** O campo `analysis_type` do payload só aceita valores definidos nos workflows carregados.

---

## 4. Pontos de Extensão

- **Adicionar Novo Workflow:** Basta incluir um novo documento YAML em `workflows.yaml`.
- **Novo Step:** Adicione um novo step na lista de steps do workflow desejado.
- **Novo Agente:** Implemente um novo executor/estratégia e referencie no YAML.

---

## 5. Recomendações

- Sempre valide o YAML antes de subir para evitar falhas de parsing.
- Mantenha a documentação dos workflows atualizada para facilitar a colaboração.
- Utilize o diagrama Mermaid em `docs/workflow.md` para alinhar entendimento entre desenvolvedores e stakeholders.

---

## Referências
- `services/workflow_registry_loader.py`
- `services/workflow_registry_service.py`
- `mcp_server_fastapi.py`
- `workflows.yaml`
