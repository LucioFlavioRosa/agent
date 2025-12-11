ANALYSIS_CONTEXT_CONFIG = {
    # Exemplo: para refinamento de épicos, buscar o último estado de 'epicos' e extrair 'epicos_report'
    "refinamento_epicos_azure_devops": [
        {"estado_para_ler": "epicos", "report_para_ler": "epicos_report"}
    ],
    # Exemplo de configuração para outros tipos de refinamento (pode ser expandido futuramente)
    "refinamento_features_azure_devops": [
        {"estado_para_ler": "features", "report_para_ler": "features_report"}
    ],
    "refinamento_times_azure_devops": [
        {"estado_para_ler": "times_descricao", "report_para_ler": "times_descricao_report"}
    ],
    "refinamento_alocacao_azure_devops": [
        {"estado_para_ler": "alocacao_times", "report_para_ler": "alocacao_times_report"}
    ],
    "refinamento_premissas_azure_devops": [
        {"estado_para_ler": "premissas_riscos", "report_para_ler": "premissas_riscos_report"}
    ]
    # Para adicionar novos tipos de análise/refinamento, siga o padrão acima.
}
