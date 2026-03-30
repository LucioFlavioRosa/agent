# Descritivo Objetivo para o Agente de UI/UX (Comgás)

Aqui está o descritivo objetivo com os elementos visuais da Comgás para a construção do protótipo:

### 🎨 1. Paleta de Cores (Brand Colors)

A identidade visual reflete a transição da empresa para provedora de soluções em energia, garantindo segurança institucional e clareza em transações de utilidade pública [1]:

  * **Azul Principal (Deep Cerulean):** `#007CB6` | RGB (0, 106, 167).[2] *Uso:* Pilar da interface, aplicado extensivamente em cabeçalhos institucionais, links e ícones ativos para reduzir a ansiedade e projetar estabilidade.[1]
  * **Azul Escuro (Venice Blue):** `#064C7D` | RGB (6, 76, 125).[3] *Uso:* Fundos do mega-footer, tipografia de títulos primários e áreas de contêineres que exigem altíssimo contraste.[1]
  * **Laranja/Amarelo Energia:** `#F89C1B` (Laranja) e `#FFD600` (Amarelo).[2] *Uso:* Aplique exclusivamente em botões primários de conversão (CTAs críticos, como "Enviar" ou "Solicitar Ligação") e badges de alerta, mimetizando digitalmente a cor da chama de gás.[1]
  * **Verde Sustentabilidade:** `#7FC241` | RGB (132, 189, 0).[2] *Uso:* Cor de suporte semântico para mensagens de sucesso de sistema e áreas temáticas voltadas a práticas ambientais (ESG).[1]
  * **Branco (White) e Espaço de Respiro:** `#FFFFFF`. *Uso:* Fundo base da aplicação. O uso de amplos espaços em branco (negative space) entre os componentes é rigoroso e intencional para evitar fadiga visual e superlotação de informações (Information Overload).[1]

### ✍️ 2. Tipografia

  * **Família Principal e Apoio:** O sistema utiliza primariamente a fonte **Open Sans** devido ao seu excelente suporte a caracteres internacionais e clareza de leitura.[4]
  * *Uso:* Os títulos adotam pesos estruturados mais pesados (Bold/Extra-Bold) frequentemente estilizados em caixa baixa (letras minúsculas) ou *sentence case* (apenas a primeira maiúscula) para abandonar a intimidação corporativa e transmitir maior acessibilidade e proximidade.[1] Para dados complexos (como contas, faturas e leitura técnica), é essencial o uso da fonte com formatação de algarismos tabulares para garantir alinhamento vertical perfeito na leitura.[1]

### 🔣 3. Iconografia

  * **Biblioteca e Estilos:** Os ícones devem ser desenhados com traços limpos (stroke weight de 1.5px a 2px) sobre uma grade de 24x24px, garantindo renderização matemática perfeita sem preenchimentos complexos de cor.[1] Eles são vitais para substituir rótulos de texto longo na navegação primária (ex: o desenho de um fogão para a área de residências).[1]
  * **Design Emocional:** Para humanizar a interface, utilize as ilustrações do avatar da assistente virtual "Cris" nos pontos de contato e suporte (SAC, WhatsApp), quebrando a frieza técnica inerente ao setor de engenharia de gás.[1]
  * **Ativos de Trust Design:** O protótipo deve obrigatoriamente incluir a logomarca da Comgás arredondada e fluida [5], além dos logotipos vetorizados da Compass Gás e Energia (controladora) e da ARSESP (agência reguladora) posicionados no rodapé para reforçar a legitimidade e segurança.[1]

### 🧩 4. Componentes e Estrutura de Interface

A arquitetura UI foi construída com absoluto rigor para organizar normas e dados complexos:

  * **Barra de Emergência Global:** Inviolável. Um banner de largura total (*full width*) fixado no extremo topo da tela em altíssimo contraste, focado unicamente no número de socorro para emergências de rede (08000 110 197), isolando-o de qualquer distração comercial.[1]
  * **Botões Interativos (CTAs):**
      * *Primários:* Blocos preenchidos de forma sólida nas cores "Laranja/Amarelo" com texto em cores densas (preto/azul escuro), forçando o clique para conclusões de fluxos operacionais e relatórios.[1]
      * *Secundários:* Aplicação do estilo "Ghost" (fundo transparente, apenas delineamento sutil da borda) fornecendo caminhos auxiliares exploratórios (ex: "Saiba mais") sem concorrer com a via transacional primária.[1]
  * **Information Cards:** Contêineres brancos com sombra projetada levíssima (*subtle drop shadow*), ícone diretivo alinhado à esquerda e manchetes em negrito. Usados extensamente para encapsular subprodutos ou agrupar os pilares de "Praticidade" e "Segurança".[1]

# Diretrizes Estratégicas e Arquitetura (Comgás)

**Conceito Central:** "Mitigação da Carga Cognitiva" – Focar em segmentar o usuário no segundo zero de interação, separando a navegação técnica burocrática da navegação de convencimento de vendas, sempre através de alto contraste.[1]

**5. URL de Componentes**
url_logo_comgas: [https://pt.wikipedia.org/wiki/Ficheiro:Logotipo_da_Comg%C3%A1s.svg#/media/Ficheiro:Logotipo_da_Comg%C3%A1s.svg](https://upload.wikimedia.org/wikipedia/commons/b/b7/Logotipo_da_Comg%C3%A1s.svg)

**6. Estrutura de UI e UX**

  * **Layout Bifurcado (Action Tiles):** A página principal de aterrissagem requer o uso de imensos *cards* funcionais ("Já sou cliente" vs. "Quero ser cliente"), isolando o indivíduo que precisa de assistência técnica transacional (como boletos ou problemas) do usuário do funil de vendas.[1]
  * **Mega-Footer Inegociável:** É a "rede de segurança estrutural" jurídica. Deve agrupar colunas densas dedicadas: canal direto da Cris (WhatsApp), portal da Comgás Virtual, link de atendimento especializado em Libras/deficientes auditivos e a chancela normativa final.[1]

**7. Acessibilidade (A11y)**

  * O design deve respeitar estritamente as diretrizes da WCAG, suportando testes automatizados robóticos de leitura de constraste (Luminance Contrast Ratio) para não prejudicar usuários com acuidade visual reduzida durante operações sensíveis e financeiras.[1] A interface exige ainda um robusto "Privacy Preference Center" flutuante (banner da LGPD) que possua hierarquia de consentimento clara e rejeite práticas desleais de UI (Dark Patterns) na leitura de aceites de rastreamento.[1][7]
