# Descritivo Objetivo para o Agente de UI/UX (Centerra Gold)

Abaixo estão as diretrizes e os elementos visuais da Centerra Gold para a construção do protótipo:

## 🎨 1. Paleta de Cores (Brand Colors)
A identidade visual reflete a solidez da empresa no setor de mineração, garantindo segurança institucional e clareza na prestação de contas de investimentos e resultados operacionais:

* **Vermelho Principal (Tall Poppy):** `#BD2426` | RGB (189, 36, 38).
    * *Uso:* Pilar da interface, aplicado extensivamente em botões primários de conversão (CTAs críticos, como inscrições em alertas de investidores) e hiperlinks ativos para guiar a interatividade e projetar urgência focada.
* **Tons Minerais (Ouro e Cobre):** Cores temáticas secundárias.
    * *Uso:* Fundos de destaque, divisores e banners fotográficos (Hero) para reforçar o *core business* industrial que exige altíssimo impacto.
* **Cinza e Carvão:** `#F4F5F7` e `#111111`.
    * *Uso:* Aplicado exclusivamente em fundos do mega-footer, delimitadores de cartões (cards), menus secundários e tipografia de corpo de texto, mimetizando digitalmente a sobriedade corporativa.
* **Branco (White) e Espaço de Respiro:** `#FFFFFF`.
    * *Uso:* Fundo base da aplicação. O uso de amplos espaços em branco (*negative space*) entre os componentes é rigoroso e intencional para evitar fadiga visual e superlotação de informações em painéis financeiros densos.

## ✍️ 2. Tipografia
* **Família Principal e Apoio:** O sistema utiliza primariamente fontes Sans-Serif limpas e geométricas devido ao seu excelente suporte em plataformas de Relações com Investidores (RI) e clareza de leitura.
* **Uso e Pesos:** Os títulos adotam pesos estruturados mais pesados (Bold/Extra-Bold) para transmitir solidez corporativa, modernidade e oficialidade. 
* **Dados Complexos:** Para painéis de balanços, relatórios trimestrais e leitura técnica, é essencial o uso da fonte com formatação de **algarismos tabulares** para garantir alinhamento vertical perfeito na leitura das métricas de performance.

## 🔣 3. Iconografia e Imagens
* **Biblioteca e Estilos:** A iconografia deve ser desenhada de forma estritamente semântica e funcional, garantindo clareza na decodificação de ações rápidas na navegação sem o uso de preenchimentos complexos ou adornos (ex: ícones de privacidade/cookies ou indicadores de reprodução de vídeos para CEOs).
* **Design Emocional:** Para humanizar a interface, utilize fotografia corporativa autêntica e direcional focada nas operações, ativos e no meio ambiente, quebrando a frieza técnica inerente à documentação de arquivamentos SEDAR/EDGAR.
* **Ativos de Trust Design:** O protótipo deve **obrigatoriamente** incluir a logomarca da Centerra Gold reversa (aplicada em fundos escuros), além do logotipo do *World Gold Council* posicionado no rodapé para reforçar a legitimidade, excelência técnica e governança ESG.

## 🧩 4. Componentes e Estrutura de Interface
A arquitetura UI foi construída com absoluto rigor para organizar normas, relatórios de governança e dados complexos:

* **Dashboards de Dados (KPI Grids):** *Inviolável.* Uma matriz focada unicamente no dado numérico bruto, invertendo a hierarquia visual para que os números de performance (ex: produção, fluxo de caixa) se sobreponham majestosamente aos rótulos textuais.
* **Botões Interativos (CTAs):**
    * **Primários:** Blocos preenchidos de forma sólida na cor "Tall Poppy Red" com texto em branco, forçando o clique para conclusões de fluxos como visualização de resultados financeiros e formulários de alertas de e-mail.
    * **Secundários:** Aplicação do estilo "Ghost" (fundo transparente, apenas delineamento sutil de borda) fornecendo caminhos auxiliares exploratórios (ex: "No, thanks" ou encerramento de alertas) sem concorrer com a via transacional primária.
* **Information Cards:** Contêineres modulares com sombreamento levíssimo e fundos isolados (`#F4F5F7`). Usados extensamente para encapsular unidades de negócios (ex: Mount Milligan, Öksüt) e agrupar pilares de desenvolvimento e projetos.

## 🎯 Diretrizes Estratégicas e Arquitetura
* **Conceito Central ("Transparência Responsável"):** Focar em entregar ao investidor e regulador o acesso informacional instantâneo no segundo zero de interação, separando a navegação de Relações com Investidores (RI) da navegação operacional e técnica, sempre através de forte hierarquia visual.

## 🔗 5. URL de Componentes
* **url_logo_centerra:** `https://s205.q4cdn.com/276554285/files/images/Centerra-Reversed-Logo.png`

## 📱 6. Estrutura de UI e UX
* **Layout em Carrossel (Hero Banners):** A página principal de aterrissagem requer o uso de imensos banners funcionais, isolando o indivíduo que busca dados trimestrais imediatos do usuário focado em análises de relatórios de Sustentabilidade de longo prazo.
* **Mega-Footer (Inegociável):** É a "rede de segurança estrutural" regulatória. Deve agrupar colunas densas dedicadas a:
    * Canal direto de inscrições para acionistas (Email Sign Up).
    * Escritórios corporativos globais.
    * Malha de links legais (Privacy, Accessibility).
    * Chancela oficial do *World Gold Council*.

## ♿ 7. Acessibilidade (A11y)
* **Conformidade:** O design deve respeitar estritamente as diretrizes da **WCAG 2.1 (Nível AA)** e reportar conformidade com a legislação **AODA**.
* **Navegação Assistida:** Suportar navegação invisível por teclado ("Skip to main content") para não prejudicar usuários com vulnerabilidades visuais ou motoras na leitura de relatórios densos.
* **Privacidade e Ética:** A interface exige um robusto painel flutuante de preferências de cookies e privacidade, que possua hierarquia de consentimento clara e rejeite expressamente práticas desleais de UI (*Dark Patterns*) no momento da navegação.
