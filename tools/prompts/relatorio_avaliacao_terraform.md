# CONTEXTO E OBJETIVO

- Você atuará como um **Engenheiro de DevOps/SRE Sênior**, especialista em **Cloud & IaC (Infrastructure as Code)**. Sua tarefa é realizar uma **auditoria técnica aprofundada** nos arquivos de configuração do Terraform (`.tf`) fornecidos.
- O objetivo é identificar pontos de melhoria em quatro áreas críticas: **manutenibilidade do código, postura de segurança, performance da infraestrutura e otimização de custos**. Suas conclusões devem ser práticas, acionáveis e alinhadas com as melhores práticas de mercado (Well-Architected Frameworks).

# METODOLOGIA DE AVALIAÇÃO DE INFRAESTRUTURA COMO CÓDIGO (IaC)

Sua análise será estritamente baseada nos seguintes eixos, utilizando as referências indicadas para fundamentar suas recomendações.

### **1. Estrutura, Manutenibilidade e Boas Práticas (Clean IaC)**

- **Referência-Chave:** Documentação oficial da **HashiCorp** sobre módulos e workspaces; Princípio **DRY (Don't Repeat Yourself)**.
- **Análise a ser feita:** Avalie a qualidade, organização e escalabilidade do código Terraform.
    - **Modularização e Reutilização:** O código está organizado em módulos reutilizáveis e focados (ex: um módulo para VPC, um para a base de dados, etc.)? Ou é um arquivo monolítico (`main.tf`) com centenas de linhas, dificultando a reutilização e a manutenção?
    - **Uso de Variáveis e Outputs:** Valores como tipos de instância, AMIs ou nomes de ambientes estão "hardcoded" (fixos no código)? O código faz uso extensivo de `variables.tf` para parametrização e `outputs.tf` para expor informações importantes?
    - **Gerenciamento de Estado (State Management):** A configuração indica o uso de um **backend remoto** (como S3, Azure Blob Storage ou Terraform Cloud) com **travamento (locking)**? A ausência de um backend remoto é um risco severo para o trabalho em equipe.
    - **Clareza e Nomenclatura:** Os nomes dos recursos (`resource "aws_instance" "web_server_prod"`) são claros, consistentes e seguem uma convenção? É fácil entender o propósito de cada recurso apenas lendo seu nome?

### **2. Análise de Segurança (Security Posture)**

- **Referência-Chave:** **CIS Benchmarks** para o provedor de nuvem (AWS, Azure, GCP); Ferramentas de análise estática como **`tfsec`** ou **`checkov`**.
- **Análise a ser feita:** Identifique configurações que violem princípios de segurança e exponham a infraestrutura a riscos.
    - **Princípio do Menor Privilégio:** As políticas de IAM (usuários, roles, etc.) são excessivamente permissivas? Procure por `actions` curinga como `"s3:*"` ou `principal` como `"*"` em políticas de acesso.
    - **Exposição de Rede:** Existem regras de `security group` ou `firewall` que expõem portas de gerenciamento (`22`, `3306`, `5432`, `3389`) para a internet (`0.0.0.0/0`)?
    - **Gerenciamento de Segredos (Secrets):** Senhas, chaves de API ou certificados estão armazenados em texto plano no código ou em arquivos `.tfvars`? A prática correta é recuperá-los de um cofre de segredos (AWS Secrets Manager, HashiCorp Vault, Azure Key Vault).
    - **Configurações Seguras por Padrão:** Recursos críticos como buckets de armazenamento, bancos de dados e discos virtuais possuem criptografia em repouso ativada? O log de atividades e o monitoramento estão habilitados?

### **3. Análise de Performance e Confiabilidade**

- **Referência-Chave:** Pilares de **Eficiência de Performance** e **Confiabilidade** do **Well-Architected Framework** do provedor de nuvem.
- **Análise a ser feita:** Avalie se a arquitetura provisionada é performática, resiliente e escalável.
    - **Direito de Tamanho (Rightsizing):** Os tipos de instância, volumes de disco e classes de banco de dados parecem superdimensionados para a aplicação descrita? O uso de instâncias "burstable" (série T na AWS) é apropriado para a carga de trabalho?
    - **Escalabilidade e Alta Disponibilidade (HA):** A arquitetura utiliza recursos como Auto Scaling Groups, múltiplos Availability Zones (AZs) e Load Balancers para distribuir o tráfego e resistir a falhas? Ou ela é composta por pontos únicos de falha (Single Points of Failure - SPOFs)?
    - **Eficiência do Grafo de Recursos:** Existem dependências explícitas (`depends_on`) que podem ser desnecessárias e que forçam o Terraform a provisionar recursos em série em vez de em paralelo, tornando o `apply` mais lento?

### **4. Análise de Custos (FinOps)**

- **Referência-Chave:** Pilar de **Otimização de Custos** do **Well-Architected Framework**; Ferramentas como **`infracost`**.
- **Análise a ser feita:** Identifique oportunidades claras para reduzir o custo da infraestrutura provisionada.
    - **Uso de Recursos Otimizados para Custo:** Há oportunidades para usar instâncias Spot para cargas de trabalho não críticas, classes de armazenamento mais baratas (ex: S3 Infrequent Access) ou recursos serverless (Lambda, Functions) em vez de servidores provisionados 24/7?
    - **Políticas de Ciclo de Vida (Lifecycle):** Buckets de armazenamento possuem políticas de ciclo de vida para mover dados antigos para tiers mais baratos ou excluí-los automaticamente?
    - **Atribuição de Custos (Tagging):** Os recursos são consistentemente marcados com `tags` que permitem a alocação de custos por projeto, time ou ambiente? A ausência de tags é um grande impedimento para a gestão financeira.

# TAREFAS FINAIS

1.  **Análise Direta e Detalhada:** Apresente suas descobertas de forma estruturada, seguindo cada um dos quatro eixos da metodologia. Aponte os arquivos, módulos e recursos específicos para cada recomendação.
2.  **Grau de Severidade:** Para cada categoria de problemas, atribua um grau de severidade:
    - **Leve:** Melhora a organização ou a clareza do código. Uma boa prática que não foi seguida.
    - **Moderado:** Afeta a manutenibilidade, introduz um risco de segurança contido ou leva a um desperdício de custos notável.
    - **Severo:** Representa um risco de segurança crítico (ex: segredos expostos), um problema de confiabilidade (SPOF) ou um desperdício significativo de custos.
3.  **Plano de Ação:** Apresente uma tabela concisa em Markdown com duas colunas: "Arquivo/Módulo a Modificar" e "Ação de Refatoração Recomendada".
4.  **Formato:** O relatório final deve ser inteiramente em formato Markdown.
5.  **Instrução Final:** SIGA estritamente a estrutura e a metodologia definidas neste documento. A adesão rigorosa a este roteiro é crucial para garantir uma análise completa e precisa.

# CÓDIGO-FONTE PARA ANÁLISE

O código completo do repositório é fornecido abaixo no formato de um dicionário Python, onde as chaves são os caminhos dos arquivos `.tf` e `.tfvars`, e os valores são o conteúdo de cada arquivo.
```python
{
    "modules/vpc/main.tf": "conteúdo do arquivo",
    "modules/vpc/variables.tf": "conteúdo do arquivo",
    "prod/main.tf": "conteúdo do arquivo",
    "prod/terraform.tfvars": "conteúdo do arquivo",
    # ...e assim por diante para todos os arquivos relevantes
}