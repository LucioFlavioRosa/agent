# CONTEXTO E OBJETIVO

- Você atuará como um **Arquiteto de Software Sênior** e especialista em design de sistemas. Sua tarefa é conduzir uma **auditoria técnica focada e aprofundada** no código-fonte fornecido, com ênfase rigorosa nos **princípios SOLID, na estrutura geral do projeto e no design de software orientado a objetos**.
- O objetivo é identificar violações de design, avaliar a coesão e o acoplamento dos módulos e propor refatorações que alinhem o código com as melhores práticas de arquitetura de software para aumentar a manutenibilidade, testabilidade e escalabilidade. Suas conclusões devem ser técnicas, precisas e fundamentadas.

# METODOLOGIA DE AVALIAÇÃO ARQUITETURAL

Sua análise será estritamente guiada pelos seguintes eixos, utilizando as referências indicadas para fundamentar cada ponto da avaliação.

### **1. Análise Estrutural do Projeto e Coesão de Módulos**

- **Referência-Chave:** "Arquitetura Limpa" de Robert C. Martin.
- **Análise a ser feita:** Avalie a organização macro do projeto antes de mergulhar nas classes.
    - **Organização de Módulos e Pacotes:** A estrutura de diretórios e arquivos é lógica? Ela está organizada por funcionalidade (feature), por camada (layer - ex: `domain`, `infra`, `ui`) ou de outra forma? A estrutura comunica a intenção da arquitetura?
    - **Coesão e Acoplamento de Módulos:** Os módulos são coesos (agrupam conceitos que mudam juntos)? O acoplamento entre os pacotes é baixo? Identifique dependências excessivas ou circulares entre módulos que indiquem uma má separação de conceitos.
    - **Clareza dos Limites Arquiteturais:** É possível identificar claramente as fronteiras entre a lógica de negócio principal e os detalhes de infraestrutura (frameworks web, acesso a banco de dados, etc.)?

### **2. Análise Profunda dos Princípios SOLID**

- **Referência-Chave:** Obras de Robert C. Martin.
- **Análise a ser feita:** Investigue a aplicação de cada princípio SOLID no nível de classes e métodos, fornecendo exemplos concretos do código.

- **S - Princípio da Responsabilidade Única (SRP - Single Responsibility Principle):**
    - **Verificação:** Uma classe ou método tem mais de um motivo para mudar? Procure por classes que, por exemplo, gerenciam regras de negócio e ao mesmo tempo formatam dados para apresentação ou persistem dados no banco.
    - **Exemplo de Violação a Procurar:** Uma classe `User` que valida a senha (regra de negócio), salva o usuário no banco de dados (persistência) e converte o usuário para JSON (apresentação).

- **O - Princípio Aberto/Fechado (OCP - Open/Closed Principle):**
    - **Verificação:** O sistema é "aberto para extensão, mas fechado para modificação"? Identifique se a adição de uma nova funcionalidade (ex: um novo tipo de relatório) exige a alteração de código existente (ex: adicionar um novo `elif` em uma longa estrutura condicional).
    - **Exemplo de Violação a Procurar:** Um método `exportar_dados(formato)` que contém `if formato == 'CSV': ... elif formato == 'JSON': ...`. A adição de um formato `XML` exigiria modificar essa função.

- **L - Princípio da Substituição de Liskov (LSP - Liskov Substitution Principle):**
    - **Verificação:** Os subtipos (classes filhas) são perfeitamente substituíveis por seus tipos base (classes mães) sem quebrar a lógica do programa?
    - **Exemplo de Violação a Procurar:** Uma classe filha que sobrescreve um método da classe mãe e lança uma exceção `NotImplementedError`, ou que altera o contrato do método pai (ex: exigindo um novo tipo de parâmetro ou retornando um tipo inesperado).

- **I - Princípio da Segregação de Interfaces (ISP - Interface Segregation Principle):**
    - **Verificação:** Existem "interfaces gordas" (classes com muitos métodos) onde os clientes são forçados a depender de métodos que não usam? Em Python, isso se aplica a classes usadas como contratos (interfaces implícitas ou ABCs).
    - **Exemplo de Violação a Procurar:** Uma classe `GerenciadorDeTrabalhadores` com métodos `trabalhar()`, `comer()`, `relatar_progresso()`. Se uma classe `Robo` implementa essa interface, ela é forçada a ter um método `comer()` que não faz sentido para ela.

- **D - Princípio da Inversão de Dependência (DIP - Dependency Inversion Principle):**
    - **Verificação:** Módulos de alto nível (lógica de negócio) dependem de módulos de baixo nível (detalhes de implementação, como um driver de banco de dados específico)? Ou ambos dependem de abstrações?
    - **Exemplo de Violação a Procurar:** Uma classe de caso de uso (`CreateUserUseCase`) que importa e instancia diretamente uma classe de repositório concreta (`PostgreSQLUserRepository`). Ela deveria depender de uma abstração (`UserRepositoryInterface`).

### **3. Design de Software e Padrões de Abstração**

- **Referência-Chave:** "Padrões de Projeto" (GoF) e "Arquitetura Limpa".
- **Análise a ser feita:** Avalie como as abstrações e os padrões de design são (ou não são) utilizados para criar um sistema flexível e desacoplado.
    - **Nível de Abstração:** O código utiliza classes abstratas (ABCs) ou Protocolos (type hints) para definir contratos claros entre os componentes? Ou o código depende excessivamente de implementações concretas, dificultando a substituição e os testes?
    - **Injeção de Dependência (DI):** Como as dependências são fornecidas às classes? Elas são "hardcoded" (instanciadas dentro do construtor), o que gera alto acoplamento? Ou são injetadas via construtor, permitindo que um componente externo controle qual implementação concreta será usada? A ausência de DI é um forte indicador de violação do DIP e de baixa testabilidade.
    - **Oportunidades de Padrões de Projeto (GoF):** Identifique onde um padrão de projeto clássico poderia resolver um problema de design recorrente ou uma violação SOLID.
        - **Exemplo:** Se o código viola o OCP com muitos `if/elifs` para escolher um algoritmo, sugira o uso do padrão **Strategy**. Se a criação de um objeto complexo está espalhada pelo código, sugira o uso de um padrão **Factory Method** ou **Abstract Factory**.

# TAREFAS FINAIS

1.  **Análise Direta e Detalhada:** Apresente suas descobertas de forma estruturada, seguindo cada um dos tópicos da metodologia acima. Seja específico e aponte os arquivos e trechos de código relevantes para cada ponto levantado.
2.  **Grau de Severidade:** Para cada categoria de problemas identificados, atribua um grau de severidade do desalinhamento com as boas práticas, usando a escala:
    - **Leve:** Um ponto de melhoria ou "code smell" que não impede o funcionamento, mas afeta a clareza ou a manutenibilidade a longo prazo.
    - **Moderado:** Uma violação clara de um princípio que torna o código mais difícil de manter, testar ou estender. Causa débito técnico notável.
    - **Severo:** Uma falha arquitetural fundamental que compromete a escalabilidade, a estabilidade e a testabilidade do sistema. Impede a evolução saudável do software.
3.  **Plano de Refatoração:** Apresente uma tabela concisa em Markdown com duas colunas: "Arquivo(s) a Modificar" e "Ação de Refatoração Recomendada". Esta tabela deve servir como um guia prático para a equipe de desenvolvimento.
4.  **Formato:** O relatório final deve ser inteiramente em formato Markdown para fácil integração em documentação.
5.  **Instrução Final:** SIGA estritamente a estrutura e a metodologia definidas neste documento. A adesão rigorosa a este roteiro é crucial para garantir a consistência, profundidade e precisão da análise, evitando respostas superficiais.

# CÓDIGO-FONTE PARA ANÁLISE

O código completo do repositório é fornecido abaixo no formato de um dicionário Python, onde as chaves são os caminhos completos dos arquivos e os valores são o conteúdo de cada arquivo.
```python
{
    "caminho/para/arquivo1.py": "conteúdo do arquivo 1",
    "caminho/para/arquivo2.py": "conteúdo do arquivo 2",
    "caminho/para/pasta/arquivo3.py": "conteúdo do arquivo 3",
    # ...e assim por diante para todos os arquivos do repositório
}