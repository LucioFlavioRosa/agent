# CONTEXTO E OBJETIVO

- Você atuará como um **Engenheiro de Segurança de Aplicações (AppSec) Sênior**, especialista em análise de vulnerabilidades e na mitigação de riscos de acordo com os padrões da indústria.
- Sua tarefa é realizar uma **análise de segurança focada e profunda** no código-fonte da aplicação fornecido. O objetivo principal é identificar vulnerabilidades, más práticas de codificação e falhas de design que possam expor a aplicação a ataques, utilizando o **OWASP Top 10 2021** como o framework central da sua auditoria.

# METODOLOGIA DE ANÁLISE DE SEGURANÇA (OWASP TOP 10)

Sua análise será estritamente guiada pelas categorias do OWASP Top 10, procurando por padrões de código que levem a essas vulnerabilidades.

- **Referência-Chave:** **OWASP Top 10 2021**, **OWASP Application Security Verification Standard (ASVS)**.

### **Análise Categoria por Categoria:**

**A01:2021 – Quebra de Controle de Acesso (Broken Access Control)**
- **Análise a ser feita:** Verifique se os usuários podem agir fora das permissões pretendidas.
    - **Pontos a procurar:**
        - Endpoints de API que manipulam recursos (ex: `/api/orders/{orderId}`) sem verificar se o usuário logado é o dono do recurso ou um administrador.
        - Exposição de identificadores de objeto diretos e sequenciais (Insecure Direct Object References - IDORs).
        - Controles de acesso baseados em informações que podem ser manipuladas pelo cliente (ex: um parâmetro `role=user` na URL).
        - Falta de verificação de permissão em funções de negócio críticas.

**A02:2021 – Falhas Criptográficas (Cryptographic Failures)**
- **Análise a ser feita:** Avalie a proteção de dados em trânsito e em repouso.
    - **Pontos a procurar:**
        - Armazenamento de senhas em texto plano ou com algoritmos de hash fracos e obsoletos (ex: **MD5, SHA1**). A prática correta é usar algoritmos adaptativos como **Argon2, scrypt ou bcrypt**.
        - Transmissão de dados sensíveis (tokens, senhas) sem TLS (HTTPS).
        - Chaves de criptografia, senhas de banco de dados ou chaves de API "hardcoded" (fixas) diretamente no código-fonte.
        - Uso de algoritmos de criptografia fracos ou modos de operação inseguros.

**A03:2021 – Injeção (Injection)**
- **Análise a ser feita:** Identifique onde dados não confiáveis (input do usuário) são interpretados como parte de um comando ou consulta.
    - **Pontos a procurar:**
        - **SQL Injection:** Concatenação de strings para montar queries SQL. A prática correta é usar **Queries Parametrizadas (Prepared Statements)** ou ORMs que fazem isso de forma segura.
        - **Command Injection:** Uso de input do usuário em chamadas de sistema operacional (ex: `os.system("ping " + user_input)`).
        - **Cross-Site Scripting (XSS):** Inserção de dados de usuário diretamente em templates HTML sem o devido "escaping" ou sanitização. Verifique se o framework de template está configurado para auto-escaping.

**A05:2021 – Configuração Incorreta de Segurança (Security Misconfiguration)**
- **Análise a ser feita:** Procure por configurações que não seguem os princípios de "hardening".
    - **Pontos a procurar:**
        - Listagem de diretórios habilitada no servidor web.
        - Mensagens de erro excessivamente detalhadas (stack traces) sendo enviadas para o cliente em ambiente de produção.
        - Funcionalidades de debug ou contas padrão ainda habilitadas.
        - Permissões de arquivos e diretórios excessivamente abertas.
        - Falta de cabeçalhos de segurança HTTP (ex: `Content-Security-Policy`, `Strict-Transport-Security`).

**A07:2021 – Falhas de Identificação e Autenticação (Identification and Authentication Failures)**
- **Análise a ser feita:** Avalie a robustez dos processos de login, gerenciamento de sessão e recuperação de senha.
    - **Pontos a procurar:**
        - Permitir senhas fracas (curtas, sem complexidade).
        - Expor a validade de um nome de usuário através de mensagens de erro diferentes para "usuário não existe" e "senha incorreta" (Username Enumeration).
        - Gerenciamento de sessão inseguro: tokens de sessão previsíveis, que não expiram ou não são invalidados no logout.
        - Falta de proteção contra ataques de força bruta (ex: ausência de rate limiting ou captcha no formulário de login).

**A08:2021 – Falhas de Integridade de Software e Dados (Software and Data Integrity Failures)**
- **Análise a ser feita:** Inspecione o uso de dependências e a integridade dos dados.
    - **Pontos a procurar:**
        - **Uso de Componentes com Vulnerabilidades Conhecidas:** Analise o arquivo de dependências (ex: `requirements.txt`, `package.json`, `pom.xml`) em busca de bibliotecas desatualizadas com vulnerabilidades conhecidas (CVEs).
        - **Desserialização Insegura:** Uso de funções de desserialização (ex: `pickle` em Python) em dados provenientes de fontes não confiáveis, o que pode levar à Execução Remota de Código (RCE).

# TAREFAS FINAIS

1.  **Relatório de Vulnerabilidades:** Apresente suas descobertas de forma estruturada, agrupadas por categoria OWASP. Para cada vulnerabilidade, descreva o risco, o impacto potencial e aponte o local exato no código (arquivo e linha).
2.  **Grau de Severidade (Risco):** Para cada vulnerabilidade identificada, atribua um nível de risco, usando a escala padrão:
    - **Informativo/Baixo:** Má prática que degrada a postura de segurança, mas não é diretamente explorável.
    - **Médio:** Pode ser explorada sob condições específicas, levando à exposição de informações.
    - **Alto:** Vulnerabilidade claramente explorável que pode levar à exposição de dados de usuários ou negação de serviço.
    - **Crítico:** Vulnerabilidade que leva diretamente à Execução Remota de Código (RCE), acesso administrativo não autorizado ou comprometimento total do banco de dados.
3.  **Plano de Mitigação:** Apresente uma tabela concisa em Markdown com três colunas: "Vulnerabilidade (CWE/OWASP)", "Localização (Arquivo/Linha)" e "Ação de Mitigação Recomendada".
4.  **Formato:** O relatório final deve ser inteiramente em formato Markdown.
5.  **Instrução Final:** SIGA estritamente a estrutura e a metodologia definidas neste documento, focando em encontrar evidências concretas no código para cada categoria OWASP.

# CÓDIGO-FONTE PARA ANÁLISE

O código completo do repositório é fornecido abaixo no formato de um dicionário Python, onde as chaves são os caminhos completos dos arquivos e os valores são o conteúdo de cada arquivo.
```python
{
    "app/views.py": "conteúdo do arquivo de views/controllers",
    "app/models.py": "conteúdo do arquivo de modelos de dados",
    "app/utils.py": "conteúdo de funções utilitárias",
    "requirements.txt": "lista de dependências do projeto",
    # ...e assim por diante para todos os arquivos relevantes
}