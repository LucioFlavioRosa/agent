# Descritivo Objetivo para o Agente de UI/UX

Aqui está o descritivo objetivo com os elementos visuais da Aegea Saneamento para a construção do protótipo:

### 🎨 1. Paleta de Cores (Brand Colors)

A identidade visual utiliza um alto contraste focado na clareza utilitária, projetando solidez institucional, transparência e compromisso ambiental:

*   **Azul Klein (Brand Primary):** `#0027BD` | RGB (0, 39, 189).[1] *Uso:* Aplique exclusivamente em botões primários de conversão (CTAs de formulários, botões de envio) e hiperlinks em linha para guiar a interatividade do usuário.
*   **Azul Prússia (Brand Secondary):** `#002F59` | RGB (0, 47, 89).[1] *Uso:* Fundos estruturais massivos como cabeçalhos institucionais, Mega-Rodapé e tipografia de exibição (Títulos H1/H2) para maximizar o contraste contra fundos claros.
*   **Branco Absoluto (White):** `#FFFFFF`. *Uso:* Cor de superfície padrão. Domina os espaços em branco (negative space) para garantir respiro visual na leitura de balanços financeiros densos e faturas.[1]
*   **Cores Secundárias (Apoio):** Tons de carvão/escala de cinza (ex: `#333333`, `#F4F5F7`) são usados para parágrafos longos e limites de contêineres modulares. O verde institucional ("ae-verde", ex: `#008000`) é aplicado de forma semântica estrita para destacar marcadores de sustentabilidade e a "Agenda ESG".

### ✍️ 2. Tipografia

A estratégia tipográfica é dupla (Dual Font Strategy), equacionando autoridade corporativa com legibilidade digital extrema [2, 3]:

*   **Família Principal (Display):** **Tipografia Serifada Customizada**. *Uso:* Aplicada estritamente em cabeçalhos macro (H1, H2), Hero Banners institucionais e declarações de propósito (ex: "Nossa natureza movimenta a vida"). Transmite tradição, gravitas corporativa e oficialidade.
*   **Famílias de Apoio (UI & Body Copy):** **Montserrat** e **Open Sans**. *Uso:* Ideais para textos longos, painéis de dados financeiros, extratos de contas e botões.[2] Para garantir contingência e carregamento rápido, utilize cadeias de fallback de sistema (System Sans, como `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`).

### 🔣 3. Iconografia

*   **Biblioteca Padrão:** O sistema utiliza ícones vetoriais de traço limpo (estilo linha), com variação de espessura controlada (1.5px a 2px) para harmonizar perfeitamente com a família *Montserrat/Open Sans*. Símbolos de direcionamento duplo (">>") são marcadores clássicos de hiperlinks longos.[2]
*   **Construção e Estilos:** Ícones focados em reduzir a carga cognitiva, decodificando termos industriais e de saneamento de forma instintiva.
*   **Ativos Exclusivos da Marca:** O uso do logotipo com o símbolo do Infinito ($\infty$) formado pelas letras "A" e "E" é mandatório.[4] Utilize variações *Full Color* (Azul Klein), versão negativa ("ae-branco") no rodapé e selos institucionais de associações (como ABDIB, ABCON, ABES e Trata Brasil) para credenciar excelência.[5]

### 🧩 4. Componentes e Sistema Movimento (Design System)

A arquitetura de interface segue as padronizações baseadas em *Design Tokens*, permitindo escalabilidade multi-marca para as diversas concessionárias do grupo (ex: Águas do Rio, Corsan, etc.):

*   **Botões Interativos:**
    *   *Primários:* Utilizam o fundo na cor "Azul Klein" com textos curtos e focados na ação em branco (fonte em peso Bold).
    *   *Secundários:* Aplicação do estilo "Ghost Button" (fundo transparente apenas com contorno delineado) para ações de suporte cognitivo (ex: "Ver preferências" de cookies).[2]
*   **Estruturas Modulares:** Uso intensivo do padrão de "Cards" levemente sombreados (fundos em branco ou cinza claro `#F4F5F7`) para isolar itens de portfólio e notícias ESG. Para painéis de Relacionamento com Investidores, os dados são organizados em matrizes 2x2.
*   **Design Tokens:** Implementação de variáveis sistêmicas que suportam flexibilidade. O logotipo unifica as concessionárias, enquanto os tokens de layout adaptam a interface sem comprometer o esqueleto principal.

### 💡 5. Diretrizes do Design System

**Conceito Central:** "Fluxo e Transparência" / "Nossa natureza movimenta a vida" – Foco na redução da fricção em processos transacionais (faturas, 2ª via) e clareza monumental para a prestação de contas de investimentos ESG.[4]

### 🔗 6. URL de Componentes

*   **url_logo_aegea:** `https://institutoaegea.com.br/wp-content/uploads/2022/07/Instituto-Aegea.svg` [6]

### 🏗️ 7. Estrutura de UI e Componentes

*   **Layout:** Navegação desobstruída usando espaço em branco intencional, organizando operadoras regionais díspares em grades limpas. Mapas do Brasil interativos com polígonos clicáveis nos 15 estados de atuação.[2]
*   **Dashboards (Central de Resultados):** Prioridade absoluta para o dado numérico bruto. Tipografia em tamanho massivo e peso majestoso, posicionando números de balanços trimestrais e emissões de carbono com hierarquia dominante sobre os rótulos de texto.
*   **Mega-Footer:** É inegociável. Trata-se do reduto de segurança legal (legal hub) estruturado sobre um fundo "Azul Prússia". Deve conter de 5 a 6 colunas lógicas abrigando selos honoríficos, portal institucional, Agenda ESG, portal de fornecedores/investidores, mídias sociais e as chancelas da LGPD e Termos de Uso.

### ♿ 8. Acessibilidade (A11y)

*   O sistema adere às diretrizes WCAG 2.1 (Nível AA). Utilização compulsória de métricas ARIA para leitura sequencial (VoiceOver/TalkBack no "Águas App"), contraste cromático profundo e alertas legíveis para faixas de vulnerabilidade ou baixo letramento digital em fluxos transacionais.

***

Caso precise refinar algum ponto específico do sistema de design ou ajustar os *tokens* CSS para a sua aplicação, me avise!
