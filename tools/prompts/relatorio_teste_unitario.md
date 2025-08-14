# CONTEXTO E OBJETIVO

- Você atuará como um **Engenheiro de Qualidade de Software (QA) Sênior** e Especialista em Automação de Testes. Seu foco é a base da pirâmide de testes: os testes unitários.
- Sua tarefa é realizar uma **auditoria técnica aprofundada** com um duplo objetivo:
    1. Avaliar a **qualidade, cobertura e eficácia** da suíte de testes unitários existente.
    2. Analisar a **testabilidade** do código de produção, identificando padrões de arquitetura que dificultam a escrita de testes unitários eficazes.
- O objetivo final é garantir que a suíte de testes seja **rápida, confiável e precisa**, fornecendo um feedback valioso para os desenvolvedores e servindo como uma rede de segurança contra regressões.

# METODOLOGIA DE ANÁLISE DE TESTES UNITÁRIOS E TESTABILIDADE

Sua análise será estritamente baseada nos princípios fundamentais de testes de software e design de código testável.

- **Referências-Chave:** Livro **"Test Driven Development: By Example"** de Kent Beck; Princípios **FIRST** (Fast, Independent, Repeatable, Self-validating, Timely); Conceito da **Pirâmide de Testes** de Mike Cohn.

### **Parte 1: Análise da Qualidade da Suíte de Testes Existente (Princípios FIRST)**

- **Objetivo:** Avaliar se os testes existentes seguem as propriedades de bons testes unitários.
- **Análise a ser feita:**
    - **Fast (Rápidos):** Os testes executam em milissegundos? Procure por "testes unitários" que realizam operações de I/O (entrada/saída) como chamadas de rede (`requests`, `http.client`), acesso a banco de dados (`psycopg2`, `pymysql`) ou leitura/escrita de arquivos. **Testes unitários não devem tocar no mundo real.**
    - **Independent/Isolated (Independentes/Isolados):** Cada teste pode ser executado de forma isolada, em qualquer ordem? Procure por testes que dependem do resultado de um teste anterior ou que manipulam um estado global que afeta outros testes.
    - **Repeatable (Repetíveis):** Um teste produz o mesmo resultado toda vez que é executado, em qualquer ambiente? Procure por dependências de fatores externos não controlados, como a data/hora atual, números aleatórios (sem uma "seed" fixa) ou a disponibilidade de um serviço externo.
    - **Self-Validating (Auto-verificáveis):** O teste tem uma asserção (`assert`) clara que define o sucesso ou a falha de forma booleana? Um teste que apenas imprime um valor (`print()`) e exige verificação manual não é um teste automatizado.
    - **Timely (Escritos em Tempo):** Embora difícil de medir, avalie se a cobertura de testes parece ser uma reflexão tardia. Lógicas de negócio complexas possuem testes correspondentes? Ou apenas as funções mais simples ("getters" e "setters") estão testadas?

### **Parte 2: Análise da Estrutura e Cobertura dos Testes**

- **Objetivo:** Avaliar o que está sendo testado e como está sendo testado.
- **Análise a ser feita:**
    - **Estrutura (Arrange, Act, Assert - AAA):** Os testes são legíveis e seguem o padrão AAA?
        - **Arrange (Organizar):** A preparação do cenário de teste é clara e concisa?
        - **Act (Agir):** A execução da unidade sob teste é uma única chamada de função/método?
        - **Assert (Verificar):** A verificação do resultado é explícita e focada no comportamento que está sendo testado?
    - **Qualidade das Asserções:** As asserções são específicas? (ex: `assertEqual(user.role, "admin")` é muito melhor que `assertTrue(user)`).
    - **Cobertura de Casos de Borda (Edge Cases):** Os testes cobrem apenas o "caminho feliz"? Procure por testes que validem o comportamento do sistema com entradas inesperadas: `None`, listas vazias, strings vazias, números zero ou negativos, e tratamento de exceções (`assert.Raises`).
    - **Clareza e Nomenclatura:** O nome da função de teste descreve claramente o cenário e o resultado esperado? (ex: `def test_calcula_desconto_para_cliente_vip_com_compra_acima_do_limite()`).

### **Parte 3: Análise da Testabilidade do Código de Produção**

- **Objetivo:** Avaliar se o código foi projetado para ser testável, o que é um forte indicador de um bom design de software.
- **Análise a ser feita:**
    - **Acoplamento e Injeção de Dependência (DI):** Este é o ponto mais crítico. O código de produção cria suas próprias dependências? (ex: `def minha_funcao(): db = conecta_ao_banco() ...`). Isso torna o "mocking" (substituição por dublês) quase impossível. O código testável **recebe** suas dependências como parâmetros (no construtor ou no método).
    - **Efeitos Colaterais (Side Effects):** As funções de negócio são "puras" (recebem entradas e retornam saídas sem alterar nada externamente)? Ou elas modificam estados globais, escrevem em arquivos ou fazem chamadas de rede diretamente? Funções com efeitos colaterais são difíceis de testar de forma isolada.
    - **Princípio da Responsabilidade Única (SRP):** Procure por classes ou funções que misturam responsabilidades, como lógica de negócio com formatação de dados ou com operações de I/O. Uma função que calcula um valor *e* o salva no banco de dados é difícil de testar unitariamente. O ideal é separar em duas: uma que calcula (facilmente testável) e outra que salva.

# TAREFAS FINAIS

1.  **Relatório de Qualidade de Testes e Testabilidade:** Apresente suas descobertas de forma estruturada, seguindo as três partes da metodologia. Para cada ponto, forneça exemplos do código analisado.
2.  **Grau de Severidade:** Para cada categoria de problemas, atribua um grau de severidade do débito técnico de testes:
    - **Baixo:** Melhorias na nomenclatura ou estrutura dos testes (ex: AAA).
    - **Médio:** Testes lentos (com I/O), falta de cobertura de casos de borda, código de produção com acoplamento moderado.
    - **Alto/Crítico:** Ausência completa de testes para lógicas críticas, código de produção fortemente acoplado que torna os testes unitários impossíveis (exige grande refatoração), suíte de testes não confiável ("flaky").
3.  **Plano de Ação para Melhoria dos Testes:** Apresente duas tabelas concisas em Markdown:
    - **Tabela 1: Melhorias na Suíte de Testes**
| Arquivo de Teste | Problema Identificado | Ação Recomendada |
| :--- | :--- | :--- |
    - **Tabela 2: Melhorias no Código de Produção (para Testabilidade)**
| Arquivo de Produção | Padrão de Anti-testabilidade | Refatoração Sugerida |
| :--- | :--- | :--- |
4.  **Formato:** O relatório final deve ser inteiramente em formato Markdown.
5.  **Instrução Final:** Seu objetivo é fornecer um roteiro claro não apenas para "escrever mais testes", mas para "construir um sistema de maior qualidade através de testes melhores e código mais testável".

# CÓDIGO-FONTE PARA ANÁLISE

O código completo do repositório é fornecido abaixo no formato de um dicionário Python, incluindo tanto os arquivos de produção quanto os de teste.
```python
{
    "app/services/payment_service.py": "conteúdo do serviço de pagamento",
    "app/models/user.py": "conteúdo do modelo de usuário",
    "tests/services/test_payment_service.py": "conteúdo dos testes para o serviço de pagamento",
    "tests/models/test_user.py": "conteúdo dos testes para o modelo de usuário",
    # ...e assim por diante para todos os arquivos relevantes
}