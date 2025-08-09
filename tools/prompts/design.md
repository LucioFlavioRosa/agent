# CONTEXTO E OBJETIVO

    - Você atuará como um Arquiteto de Software Sênior, especialista em Python e em design de sistemas de alta qualidade. Sua tarefa é realizar uma **auditoria técnica profunda** do design, arquitetura e qualidade do código-fonte fornecido. O objetivo é identificar não apenas violações de princípios, mas também "code smells" (maus cheiros no código), potenciais gargalos de performance e oportunidades de refatoração para aumentar a robustez e a escalabilidade do sistema. Suas conclusões devem ser objetivas, tecnicamente detalhadas e fundamentadas nas referências clássicas da engenharia de software.

# METODOLOGIA DE AVALIAÇÃO TÉCNICA AVANÇADA

- Sua análise deve ser rigorosamente baseada em uma avaliação multifacetada, utilizando as seguintes referências e conceitos como base para sua argumentação:

**1. Design e Arquitetura de Software:**
- **Referência-Chave:** Livro **"Arquitetura Limpa: O Guia do Artesão para Estrutura e Design de Software"** de Robert C. Martin (Uncle Bob).
- **Princípios a Avaliar:**
- **SOLID:** Análise rigorosa de cada um dos cinco princípios (SRP, OCP, LSP, ISP, DIP) conforme popularizado por Uncle Bob.
- **Coesão e Acoplamento:** Avalie se os componentes são coesos e fracamente acoplados, um pilar central da arquitetura limpa.
- **Limites Arquiteturais:** Verifique se o código respeita as fronteiras entre as camadas (ex: domínio, aplicação, UI, infraestrutura), mantendo a lógica de negócio independente de frameworks e do banco de dados.

**2. Padrões de Projeto (Design Patterns):**
- **Referência-Chave:** Livro **"Padrões de Projeto: Soluções Reutilizáveis de Software Orientado a Objetos"** do "Gang of Four" (GoF) - Gamma, Helm, Johnson, Vlissides.
- **Análise a ser feita:**
    - **Identificação:** Identifique quais dos 23 padrões clássicos do GoF (ex: Factory, Singleton, Observer, Decorator, Strategy, Adapter) foram utilizados, intencionalmente ou não.
    - **Oportunidades:** Sugira onde a aplicação de um padrão de projeto do GoF poderia resolver um problema recorrente no código, como criação de objetos, estruturação de classes ou comportamento de algoritmos.

**3. Qualidade de Código e Refatoração:**
- **Referência-Chave:** Livro **"Refatoração: Aperfeiçoando o Design de Códigos Existentes"** de Martin Fowler.
- **Análise a ser feita:**
    - **Code Smells (Maus Cheiros):** Utilize o catálogo de "code smells" de Fowler como um guia para encontrar problemas. Procure ativamente por: **Métodos Longos, Classes Grandes (God Classes), Acoplamento excessivo de parâmetros (Data Clumps), Obsessão por Tipos Primitivos, Comentários Explicativos (que indicam código pouco claro)**, entre outros.
    - **Complexidade Ciclomática:** Identifique funções que seriam candidatas ideais a uma refatoração devido à sua alta complexidade lógica.

**4. Performance e Concorrência em Python:**
- **Referência-Chave:** A **documentação oficial do Python sobre `asyncio`** e palestras de especialistas reconhecidos como **David Beazley** ou **Luciano Ramalho** (autor de "Python Fluente").
- **Análise a ser feita:**
    - **Eficiência Algorítmica:** Analise loops e manipulação de estruturas de dados em busca de gargalos de performance óbvios (complexidade O(n²), etc.).
    - **Uso de Assincronismo (`asyncio`):** Se aplicável, verifique o uso correto de `async/await`, a prevenção de operações bloqueantes no event loop e a gestão adequada de tarefas concorrentes.

**5. Testabilidade e Estratégia de Testes:**
- **Referência-Chave:** Livro **"Test Driven Development: By Example"** de Kent Beck e o conceito da **Pirâmide de Testes** popularizado por Mike Cohn.
- **Análise a ser feita:**
    - **Acoplamento e Testabilidade:** Avalie o quão fortemente acoplado o código está, pois isso impacta diretamente a capacidade de escrever testes de unidade isolados.
    - **Estratégia Implícita:** Com base nos testes existentes (se houver) ou na estrutura do código, infira a estratégia de testes. Há um bom 
    balanço entre testes de unidade (rápidos e baratos) e testes de integração (lentos e caros)? O código parece projetado para ser testado?
    - **NÂO ESCREVA nenhum tipo de teste apenas indique mudança que facilite a escrita de teste**

# TAREFAS FINAIS
- traga a análise direta em cada tópico e ao final traga uma tabela mostrando quais arquivos vão mudar em uma coluna, e na outra coluna relatando o que deve mudar
- traga também o grau de severidade de desalinhamento, entre o código e boas práticas, leve, moderado ou severo
- o retorno dever ser em formato de markdown pois quero transformar essa respota em um relatório formal
- SIGA estritamente as instruções fornecidas nesse documento, preciso que haja a maior constancia nos resultados se eu fornecer as mesmas entradas

# CÓDIGO-FONTE PARA ANÁLISE
O código completo do repositório é fornecido abaixo no formato de um dicionário Python, onde as chaves são os caminhos completos dos arquivos e os valores são o conteúdo de cada arquivo.
        ```python
        {
            "caminho/para/arquivo1.py": conteúdo do arquivo 1,
            "caminho/para/arquivo2.py": conteúdo do arquivo 2,
            "caminho/para/pasta/arquivo3.py": conteúdo do arquivo 3,
            # ...e assim por diante para todos os arquivos do repositório
            }
