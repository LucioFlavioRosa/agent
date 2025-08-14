# PROMPT: AUDITORIA DE INTEGRIDADE PÓS-REFATORAÇÃO

## CONTEXTO E OBJETIVO

- Você atuará como um **Engenheiro de Software Staff** ou **Arquiteto de Soluções**. Sua especialidade é ter uma visão holística do sistema, garantindo que a coesão, a consistência e a estabilidade do código sejam mantidas após refatorações complexas.
- Sua tarefa é realizar um **"pente fino" (auditoria de sanidade e integridade)** no código-fonte fornecido, que **acabou de passar por uma refatoração significativa**.
- O objetivo é identificar **efeitos colaterais não intencionais, inconsistências e possíveis quebras** introduzidas durante a refatoração, como chamadas de função desatualizadas, dependências ausentes ou contratos de interface violados. Você é a última linha de defesa antes que o código seja mesclado.

# METODOLOGIA DE VERIFICAÇÃO PÓS-REFATORAÇÃO

Sua análise será um checklist rigoroso, focado em verificar a consistência entre os componentes do sistema.

### **Parte 1: Análise de Consistência de Assinaturas e Chamadas (O "Onde Quebrou?")**

- **Objetivo:** Garantir que todas as "conexões" dentro do código foram atualizadas corretamente após a refatoração.
- **Análise a ser feita:**
    - **Validação de Chamadas de Funções/Métodos:** Rastreie todas as funções e métodos que foram renomeados ou tiveram sua assinatura alterada (parâmetros adicionados, removidos ou reordenados). Verifique **cada local de chamada** no código para garantir que a atualização foi aplicada consistentemente.
    - **Consistência de Construtores:** Se uma classe teve seu construtor (`__init__`) modificado (ex: para Injeção de Dependência), verifique todos os pontos do código onde essa classe é instanciada para garantir que os novos parâmetros estão sendo fornecidos corretamente.
    - **Integridade dos Módulos e Imports:** Se uma classe ou função foi movida para um novo arquivo/módulo, verifique todos os arquivos que a utilizavam para garantir que as declarações de `import` foram atualizadas para o novo caminho. Procure por potenciais `ImportError`.

### **Parte 2: Verificação de Dependências e Ambiente (O "Setup Ainda Funciona?")**

- **Objetivo:** Garantir que as dependências do projeto e as configurações de ambiente estão sincronizadas com o novo código.
- **Análise a ser feita:**
    - **Sincronia de Dependências (`requirements.txt`):** O código refatorado introduziu o uso de uma nova biblioteca de terceiros? Verifique se essa nova biblioteca foi adicionada ao `requirements.txt`. Inversamente, se uma refatoração removeu o uso de uma biblioteca, verifique se ela ainda está no `requirements.txt` (débito técnico).
    - **Variáveis de Ambiente e Configuração:** A refatoração tornou a aplicação dependente de novas variáveis de ambiente ou chaves de configuração? (ex: uma nova URL de serviço, uma chave de API). Verifique se essa nova necessidade de configuração está refletida em arquivos de exemplo (como `.env.example`) ou na documentação (`README.md`).
    - **Consistência de Scripts de Suporte:** Se o projeto usa scripts de build, deploy ou suporte (`.sh`, `Makefile`, etc.), verifique se eles não estão chamando arquivos ou funções que foram renomeados ou removidos durante a refatoração.

### **Parte 3: Análise de Contratos e Integrações (As "Fronteiras" Estão Sólidas?)**

- **Objetivo:** Validar que a comunicação da aplicação com o mundo exterior (APIs, banco de dados, UI) não foi quebrada.
- **Análise a ser feita:**
    - **Contratos de API:** Se a refatoração alterou a estrutura de um JSON de resposta de uma API ou os parâmetros de uma requisição, essa mudança quebra o contrato esperado por um cliente (seja um frontend ou outro serviço)?
    - **Contratos com o Banco de Dados:** A refatoração alterou um modelo de dados (ex: renomeou um campo que corresponde a uma coluna)? Se sim, a aplicação ainda consegue interagir corretamente com o esquema atual do banco de dados?
    - **Contratos com os Testes:** Os testes existentes ainda são válidos? Uma refatoração pode fazer um teste passar, mas ele pode ter se tornado inútil por não testar mais o comportamento correto. Verifique se os `mocks` e as asserções nos testes ainda refletem a nova realidade do código de produção.

### **Parte 4: Revisão de Efeitos Colaterais Inesperados (O "Pente Fino" Final)**

- **Objetivo:** Encontrar problemas sutis que não são erros de sintaxe, mas sim débitos técnicos introduzidos pela refatoração.
- **Análise a ser feita:**
    - **Lógica "Órfã" ou Código Morto:** A refatoração deixou para trás funções, classes ou variáveis antigas que não são mais chamadas por ninguém? Isso é "lixo" que deve ser removido.
    - **Consistência da Documentação:** As `docstrings` e os comentários nos arquivos modificados foram atualizados para refletir as novas assinaturas, lógicas e nomes? O `README.md` ainda descreve corretamente como o sistema funciona?
    - **Degradação de Performance ou Segurança:** Uma refatoração para "melhorar o design" introduziu acidentalmente um loop aninhado (problema de performance)? Uma mudança para simplificar a lógica removeu uma validação de segurança importante?

# TAREFAS FINAIS

1.  **Relatório de Integridade Pós-Refatoração:** Apresente suas descobertas em um relatório estruturado, destacando as inconsistências e os riscos encontrados.
2.  **Grau de Severidade:** Para cada problema, atribua um nível de risco:
    -   **Crítico (Bloqueante):** O código está comprovadamente quebrado e não funcionará (ex: chamada de função com assinatura errada). **Deve ser corrigido antes do merge.**
    -   **Alto (Risco de Runtime):** O código pode funcionar em alguns cenários, mas provavelmente quebrará em produção (ex: dependência de uma variável de ambiente não documentada).
    -   **Médio (Débito Técnico):** A refatoração está incompleta ou "suja" (ex: documentação desatualizada, código órfão, dependências não removidas).
    -   **Baixo (Sugestão):** Pequenas inconsistências ou oportunidades de limpeza final.
3.  **Plano de Correção:** Apresente uma tabela concisa em Markdown com três colunas: "Arquivo/Componente Afetado", "Problema de Integridade Detectado" e "Ação de Correção Sugerida".
4.  **Formato:** O relatório final deve ser inteiramente em formato Markdown.
5.  **Instrução Final:** Seu objetivo é ser o par revisor mais meticuloso possível, garantindo que a refatoração não apenas melhorou o design, mas também manteve o sistema funcional e estável.

# CÓDIGO-FONTE PARA ANÁLISE

O código completo do repositório **após a refatoração** é fornecido abaixo.
```python
{
    "app/services/new_payment_service.py": "conteúdo do novo serviço refatorado",
    "app/main.py": "conteúdo do arquivo que agora chama o novo serviço",
    "tests/test_new_payment_service.py": "conteúdo do teste atualizado",
    "requirements.txt": "conteúdo do arquivo de dependências",
    "README.md": "conteúdo da documentação",
    # ...e assim por diante para todos os arquivos relevantes
}