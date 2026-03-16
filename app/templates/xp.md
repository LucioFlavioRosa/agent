Peço desculpas pela dificuldade em acessar o arquivo anterior. Aqui está o documento completo contendo as diretrizes em formato Markdown bruto. Você pode usar o botão de copiar no canto superior do bloco de código para enviar diretamente ao seu agente:

# Descritivo Objetivo para o Agente de UI/UX

Aqui está o descritivo objetivo com os elementos visuais da XP Investimentos para a construção do protótipo:

### 🎨 1. Paleta de Cores (Brand Colors)

A identidade visual utiliza um alto contraste para garantir clareza, autoridade institucional e boa legibilidade em aplicações financeiras:

* **Amarelo Supernova:** `#FFC60A` | RGB (255, 198, 10). *Uso:* Aplique exclusivamente em botões primários de conversão (CTAs como "Abra sua conta") e para guiar o olhar do usuário a destaques.
* **Preto (Black):** `#000000`. *Uso:* Fundos da interface no modo escuro (Dark Mode), tipografia principal de títulos e bordas estruturais.
* **Branco (White):** `#FFFFFF`. *Uso:* Fundos no modo claro (Light Mode), tipografia em fundos escuros e espaços de respiro (negative space).
* **Cores Secundárias (Apoio):** Tons de carvão/chumbo (ex: `#111111`, `#222222`) são usados em textos longos para reduzir o cansaço visual. Para layouts focados no segmento de alta renda (como o Cartão XP Legacy e contas Unique), a interface utiliza tons metálicos, grafite e detalhes em cobre para transmitir um acabamento premium.

### ✍️ 2. Tipografia
* **Família Principal:** **XP Lighthouse** (ou XP Light Lighthouse). É uma fonte *grotesque sans-serif* (sem serifa) exclusiva da marca, desenvolvida em parceria com o estúdio Plau. Ela se destaca por possuir armadilhas de tinta (*ink traps*) geométricas acentuadas. *Uso:* Títulos grandes (Display, H1) e seções institucionais. Por ser uma *variable font*, permite animações e diferentes pesos e larguras na interface.
* **Famílias de Apoio (Fallback):** **Roboto** e **Roboto Slab**. *Uso:* A fonte Roboto, em seus pesos mais leves, é ideal para o texto dos componentes (body copy), menus de navegação e para manter alinhamento tabular perfeito na leitura de balanços financeiros e painéis de *Home Broker*.

### 🔣 3. Iconografia

* **Biblioteca Padrão:** O design system oficial utiliza a biblioteca **Phosphor Icons**.
* **Construção e Estilos:** Os ícones são desenhados baseados em uma grade de 16x16px, o que garante excelente renderização tanto em micro-botões quanto em escalas maiores. O sistema utiliza variações de peso para demonstrar interatividade: o peso "Regular" é usado para ícones e menus inativos, enquanto o peso "Fill" (preenchido) e "Bold" indica que um item foi favoritado ou selecionado.
* **Ativos Exclusivos da Marca:** Para gerar confiabilidade no protótipo, não se esqueça de usar os logos da XP vetorizados em SVG, incluir "Badges" de download de lojas (Apple Store e Google Play) e os selos obrigatórios de regulamentadores no mega-rodapé (B3, CVM, ANBIMA e proteção FGC).

### 🧩 4. Componentes e SOMA Design System

A arquitetura de interface segue as padronizações do **SOMA Design System**, construído para operar de maneira ágil, consistente e escalável em modo multi-marca.
* **Botões Interativos:**
* *Primários:* Utilizam o fundo na cor "Supernova" com textos curtos e focados na ação.
* *Secundários:* Aplique o estilo "Ghost" (fundo transparente apenas com delineamento de borda) para ações auxiliares como "Saiba mais".

* **Estruturas Modulares:** Use o padrão de "Cards" para agrupar soluções e famílias de fundos. Em relatórios e *dashboards* de mercado, os dados são comumente organizados em grelhas matriciais rígidas (ex: painéis analíticos 2x2 para exibição de performance e taxas) onde os números assumem a hierarquia tipográfica principal.
* **Design Tokens:** A estrutura de desenvolvimento prevê o uso de "Tokens" visuais (variáveis sistêmicas para gerenciar as cores, raios de borda e espaços de preenchimento). Isso assegura flexibilidade extrema, suportando de forma limpa as inversões para *Dark/Light Mode*.

# Diretrizes do SOMA Design System (XP Investimentos)

**Conceito Central:** "Lighthouse" (Farol) – Foco absoluto em clareza, acessibilidade e redução da carga cognitiva, utilizando alto contraste e espaço em branco intencional.

**6. URL de Componentes**
url_logo_xp: https://upload.wikimedia.org/wikipedia/pt/0/0b/XP_Investimentos_logo.png

**5. Estrutura de UI e Componentes**
* **Layout:** Utilize estruturas em *Cards* modulares para separar famílias de fundos e produtos complexos.
* **Dashboards:** Organize em matrizes reticuladas (ex: 2x2). Priorize a escaneabilidade numérica com hierarquia vertical de empilhamento (ex: Nome do Fundo acima do Valor Total em tamanho massivo).
* **Mega-Footer:** É inegociável. Deve conter badges das lojas de aplicativos, matriz de links, contatos de atendimento (incluindo acessibilidade em Libras) e o bloco final com avisos regulatórios e CNPJ.

**6. Acessibilidade (A11y)**

* O sistema deve aderir às diretrizes WCAG. Garanta contraste correto em todos os modos de tela e implemente navegação semântica linear projetada para leitores de tela (VoiceOver/TalkBack).

