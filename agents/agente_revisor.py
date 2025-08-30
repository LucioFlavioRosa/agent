import json
import time
from typing import Optional, Dict, Generator, Any, List
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.llm_provider_interface import ILLMProvider
from tools.repository_provider_factory import get_repository_provider
from tools.github_reader import GitHubRepositoryReader

TAMANHO_LOTE = 10
ATRASO_ENTRE_LOTES_SEGUNDOS = 60

class AgenteRevisor:
    """
    Orquestrador especializado em análise de código via IA com integração a repositórios.
    
    Este agente é responsável por coordenar a leitura de repositórios GitHub, GitLab
    e Azure DevOps e iniciar análises de código através de provedores de LLM. Sua responsabilidade
    única é orquestrar o fluxo: repositório → detecção de provider → leitura → análise → resultado.
    
    Características principais:
    - Detecção automática do tipo de repositório (GitHub, GitLab, Azure DevOps)
    - Integração com repositórios através de interface abstrata
    - Processamento de código via provedores de LLM
    - Tratamento robusto de erros de leitura de repositório
    - Suporte a diferentes tipos de análise configuráveis
    - Validação robusta de retornos do provedor LLM
    
    Attributes:
        repository_reader (IRepositoryReader): Interface para leitura de repositórios
        llm_provider (ILLMProvider): Provedor de LLM para análise do código
    
    Example:
        >>> from tools.requisicao_openai import OpenAILLMProvider
        >>> llm = OpenAILLMProvider()
        >>> agente = AgenteRevisor(llm_provider=llm)
        >>> resultado = agente.main(
        ...     tipo_analise="refatoracao",
        ...     repositorio="org/projeto",  # GitHub detectado automaticamente
        ...     nome_branch="main"
        ... )
        >>> 
        >>> # Também funciona com GitLab e Azure DevOps
        >>> resultado = agente.main(
        ...     tipo_analise="refatoracao",
        ...     repositorio="gitlab-org/gitlab",  # GitLab detectado automaticamente
        ...     nome_branch="main"
        ... )
    """
    
    def __init__(
        self,
        repository_reader: Optional[IRepositoryReader] = None,
        llm_provider: Optional[ILLMProvider] = None
    ):
        """
        Inicializa o agente com as dependências necessárias.
        
        Args:
            repository_reader (Optional[IRepositoryReader]): Implementação de leitor de repositório.
                Se None, usa GitHubRepositoryReader com detecção automática de provider
            llm_provider (Optional[ILLMProvider]): Implementação de provedor de LLM que será
                usado para análise do código obtido. Deve ser fornecido para funcionamento
        
        Raises:
            TypeError: Se as dependências não implementarem as interfaces esperadas
        
        Note:
            O repository_reader padrão (GitHubRepositoryReader) agora suporta detecção
            automática de provedores, funcionando transparentemente com GitHub, GitLab
            e Azure DevOps baseado no formato do nome do repositório.
        """
        self.repository_reader = repository_reader or GitHubRepositoryReader()
        
        # Validação do provedor LLM
        if llm_provider is not None and not hasattr(llm_provider, 'executar_prompt'):
            raise TypeError("llm_provider deve implementar ILLMProvider com método executar_prompt")
        self.llm_provider = llm_provider

    def _validar_e_extrair_resposta(self, resultado_llm: Any) -> str:
        """
        Valida e extrai a resposta final do retorno do provedor LLM.
        
        Este método garante compatibilidade com diferentes implementações de ILLMProvider,
        tratando tanto retornos diretos (string) quanto estruturados (dict).
        
        Args:
            resultado_llm (Any): Retorno do método executar_prompt do provedor
            
        Returns:
            str: Resposta final extraída e validada
            
        Raises:
            ValueError: Se o retorno não contiver dados válidos
            TypeError: Se o retorno não for do tipo esperado
        """
        # Caso 1: Retorno direto como string
        if isinstance(resultado_llm, str):
            if not resultado_llm.strip():
                raise ValueError("Provedor LLM retornou string vazia")
            return resultado_llm.strip()
        
        # Caso 2: Retorno estruturado como dict (conforme interface ILLMProvider)
        if isinstance(resultado_llm, dict):
            # Verifica se contém a chave obrigatória 'reposta_final'
            if 'reposta_final' not in resultado_llm:
                raise ValueError(
                    "Retorno do provedor LLM não contém chave obrigatória 'reposta_final'. "
                    f"Chaves disponíveis: {list(resultado_llm.keys())}"
                )
            
            resposta_final = resultado_llm['reposta_final']
            
            # Valida se a resposta final é uma string não vazia
            if not isinstance(resposta_final, str):
                raise TypeError(
                    f"Chave 'reposta_final' deve ser string, recebido: {type(resposta_final).__name__}"
                )
            
            if not resposta_final.strip():
                raise ValueError("Chave 'reposta_final' contém string vazia")
            
            return resposta_final.strip()
        
        # Caso 3: Tipo não suportado
        raise TypeError(
            f"Retorno do provedor LLM deve ser string ou dict, recebido: {type(resultado_llm).__name__}"
        )

    def _get_code(
        self,
        repositorio: str,
        nome_branch: Optional[str],
        tipo_analise: str
    ) -> Dict[str, str]:
        """
        Obtém código-fonte de um repositório usando detecção automática de provider.
        
        Este método privado encapsula a lógica de leitura de repositório com
        detecção automática do tipo de provider (GitHub, GitLab, Azure DevOps),
        fornecendo tratamento de erro consistente e logging para debugging.
        
        Args:
            repositorio (str): Nome do repositório. Formatos suportados:
                - GitHub: 'org/repo' ou 'user/repo'
                - GitLab: 'grupo/projeto' (detectado por heurísticas)
                - Azure DevOps: 'organization/project/repository'
            nome_branch (Optional[str]): Nome da branch a ser lida. Se None,
                usa a branch padrão do repositório
            tipo_analise (str): Tipo de análise que determina quais arquivos
                serão filtrados durante a leitura
        
        Returns:
            Dict[str, str]: Dicionário mapeando caminhos de arquivo para seu conteúdo.
                Formato: {"caminho/arquivo.py": "conteúdo do arquivo"}
        
        Raises:
            RuntimeError: Se houver falha na leitura do repositório, encapsulando
                a exceção original para contexto adicional
            ValueError: Se o formato do repositório for inválido ou tipo_analise
                não for reconhecido
        
        Note:
            - O tipo_analise é usado pelo repository_reader para filtrar arquivos relevantes
            - Logging é feito para facilitar debugging de problemas de conectividade
            - A detecção de provider é automática baseada no nome do repositório
            - Suporta GitHub, GitLab e Azure DevOps transparentemente
        """
        try:
            print(f"Iniciando a leitura do repositório: {repositorio}, branch: {nome_branch}")
            print(f"Detecção automática de provider será aplicada baseada no formato do repositório.")
            
            # Delega a leitura para a implementação injetada
            # O GitHubRepositoryReader agora detecta automaticamente o provider correto
            codigo_para_analise = self.repository_reader.read_repository(
                nome_repo=repositorio,
                tipo_analise=tipo_analise,
                nome_branch=nome_branch
            )
            
            return codigo_para_analise
            
        except Exception as e:
            # Encapsula exceções com contexto adicional para debugging
            raise RuntimeError(f"Falha ao ler o repositório: {e}") from e
            
    def _create_batches(self, data: dict, size: int) -> Generator[Dict[str, str], None, None]:
        """
        Divide um dicionário grande em geradores de lotes menores.
        """
        all_keys = list(data.keys())
        for i in range(0, len(all_keys), size):
            batch_keys = all_keys[i:i + size]
            yield {k: data[k] for k in batch_keys}


    def main(
        self,
        tipo_analise: str,
        repositorio: str,
        nome_branch: Optional[str] = None,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        """
        Orquestra a obtenção de código de repositório e análise via IA com suporte multi-provedor.
        
        Este é o método principal que coordena todo o fluxo do agente:
        1. Detecta automaticamente o tipo de repositório (GitHub, GitLab, Azure DevOps)
        2. Obtém código do repositório através do repository_reader
        3. Valida se código foi encontrado
        4. Serializa código em formato JSON
        5. Envia para análise via llm_provider
        6. Valida e extrai resposta do provedor
        7. Retorna resultado estruturado
        
        Args:
            tipo_analise (str): Tipo de análise a ser executada. Deve corresponder
                a um prompt disponível no sistema (ex: 'refatoracao', 'revisao')
            repositorio (str): Nome do repositório. Formatos aceitos:
                - GitHub: 'org/repo', 'user/repo' (formato padrão)
                - GitLab: 'grupo/projeto' (detectado por heurísticas como 'gitlab-org/gitlab')
                - Azure DevOps: 'organization/project/repository' (3 partes)
            nome_branch (Optional[str], optional): Nome da branch a ser analisada.
                Se None, usa a branch padrão. Defaults to None
            instrucoes_extras (str, optional): Instruções adicionais do usuário
                que complementam a análise. Defaults to ""
            usar_rag (bool, optional): Se deve usar Retrieval-Augmented Generation
                para enriquecer o contexto da análise. Defaults to False
            model_name (Optional[str], optional): Nome específico do modelo de LLM.
                Se None, usa o modelo padrão do provedor. Defaults to None
            max_token_out (int, optional): Limite máximo de tokens na resposta
                do LLM. Defaults to 15000
        
        Returns:
            Dict[str, Any]: Resultado estruturado da análise contendo:
                - resultado (Dict): Contém 'reposta_final' com a análise do LLM
                - Se nenhum código for encontrado, retorna estrutura vazia
                - Formato: {"resultado": {"reposta_final": <analise_do_llm>}}
        
        Raises:
            RuntimeError: Se houver falha na leitura do repositório ou comunicação com LLM
            ValueError: Se tipo_analise for inválido, repositorio mal formatado,
                formato de repositório não suportado, ou retorno do provedor inválido
            TypeError: Se o retorno do provedor LLM não for do tipo esperado
            Exception: Erros de comunicação com o provedor de LLM são propagados
        
        Note:
            - Detecção automática de provider baseada no formato do repositório
            - Se nenhum código for encontrado, retorna resultado vazio sem erro
            - O código é serializado em JSON com formatação legível
            - Avisos são impressos para facilitar debugging
            - Suporta GitHub, GitLab e Azure DevOps transparentemente
            - Funciona com qualquer repository_reader que implemente IRepositoryReader
            - Validação robusta do retorno do provedor LLM
        """
        # Validação de entrada (mantida)
        if not tipo_analise or not isinstance(tipo_analise, str):
            raise ValueError("tipo_analise deve ser uma string não vazia")
        if not repositorio or not isinstance(repositorio, str):
            raise ValueError("repositorio deve ser uma string não vazia")
        if self.llm_provider is None:
            raise ValueError("llm_provider é obrigatório para análise de código")
        
        # Etapa 1: Obter código do repositório (mantida)
        codigo_para_analise = self._get_code(
            repositorio=repositorio, nome_branch=nome_branch, tipo_analise=tipo_analise
        )

        if not codigo_para_analise:
            print(f"AVISO: Nenhum código encontrado para a análise '{tipo_analise}'.")
            return {"resultado": {"reposta_final": {"reposta_final": "{}"}}}

        # Etapa 3: Divide o código em lotes
        lotes = list(self._create_batches(codigo_para_analise, TAMANHO_LOTE))
        print(f"Código dividido em {len(lotes)} lotes de até {TAMANHO_LOTE} arquivos cada.")

        resultados_parciais: List[Dict] = []
        tokens_entrada_total = 0
        tokens_saida_total = 0

        for i, lote in enumerate(lotes):
            print(f"  Processando lote {i + 1}/{len(lotes)}...")
            
            try:
                codigo_str_lote = json.dumps(lote, indent=2, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                print(f"  AVISO: Erro ao serializar o lote {i + 1}. Pulando. Erro: {e}")
                continue
    
            # --- ESTRUTURA TRY/EXCEPT CORRIGIDA ---
            try:
                # Tenta executar a chamada à IA e processar a resposta
                resultado_lote_ia = self.llm_provider.executar_prompt(
                    tipo_tarefa=tipo_analise,
                    prompt_principal=codigo_str_lote,
                    instrucoes_extras=instrucoes_extras,
                    usar_rag=usar_rag,
                    model_name=model_name,
                    max_token_out=max_token_out
                )
                
                resposta_validada_lote_str = self._validar_e_extrair_resposta(resultado_lote_ia)
                parsed_response = json.loads(resposta_validada_lote_str)
                resultados_parciais.append(parsed_response)
                
                tokens_entrada_total += resultado_lote_ia.get('tokens_entrada', 0)
                tokens_saida_total += resultado_lote_ia.get('tokens_saida', 0)
    
            # O 'except' deve estar alinhado com o 'try' acima
            except json.JSONDecodeError as e:
                print(f"  AVISO: Lote {i + 1} retornou um JSON inválido. Erro: {e}.")
            except Exception as e:
                print(f"  AVISO: Falha geral ao processar o lote {i + 1} com a IA. Erro: {e}. Continuando...")
        # --- FIM DA CORREÇÃO ---

            if i < len(lotes) - 1:
                print(f"  Pausa de {ATRASO_ENTRE_LOTES_SEGUNDOS} segundos...")
                time.sleep(ATRASO_ENTRE_LOTES_SEGUNDOS)
        
        # --- AGREGAÇÃO DE RESULTADOS (SEM MUDANÇAS, MAS AGORA RECEBE DADOS) ---
        print("Agregando resultados de todos os lotes...")
        resultado_final_agregado = {
            "relatorio": "# Relatório Agregado\n\n", 
            "conjunto_de_mudancas": []
        }

        
        # Etapa 5: Agregação dos resultados (mantida)
        print("Agregando resultados de todos os lotes...")
        resultado_final_agregado = {"relatorio": "# Relatório Agregado\n\n", "conjunto_de_mudancas": []}
        
        for parcial in resultados_parciais:
            relatorio_parcial = parcial.get("relatorio", "")
            if "##" in relatorio_parcial:
                relatorio_parcial = "\n".join(relatorio_parcial.splitlines()[1:])
            resultado_final_agregado["relatorio"] += relatorio_parcial + "\n"
            resultado_final_agregado["conjunto_de_mudancas"].extend(parcial.get("conjunto_de_mudancas", []))

        json_final_agregado_str = json.dumps(resultado_final_agregado, indent=2, ensure_ascii=False)
        resultado_da_ia_final = {'reposta_final': json_final_agregado_str, 'tokens_entrada': tokens_entrada_total, 'tokens_saida': tokens_saida_total}

        # Etapa 6: Retorno padronizado (mantida)
        return {"resultado": {"reposta_final": resultado_da_ia_final}}
