# Descritivo Objetivo para o Agente de UI/UX: Serasa & Serasa Experian

Este documento detalha os elementos visuais e diretrizes de design para a construção de protótipos e interfaces institucionais e painéis de usuário (dashboards), com base no design system atual da web da Serasa Experian.

## 🎨 1. Paleta de Cores (Brand Colors)
A identidade visual é construída para transmitir confiança (cores escuras e sólidas) e ação imediata (cores quentes e vibrantes), com alto contraste para acessibilidade.

| Cor | Aplicação Principal | Evidência Visual |
| :--- | :--- | :--- |
| **Branco e Cinza Claro (Off-White)** | Superfície padrão do site e dashboards (fundos ` #F5F6F8 ` ou similar). Garante respiro e destaca os blocos de conteúdo e cards. | Fundo predominante nas áreas de listagem, painel logado e interior de cards. |
| **Magenta / Rosa Vibrante** | **Cor de Ação Primária (Accent/CTA).** Usada no botão principal (ex: "Começar", "Consulte grátis"), links ativos, títulos de seções de destaque e avatar do usuário. | Botões de destaque, sublinhado no menu ativo, títulos como "Conheça os benefícios...". |
| **Roxo Escuro (Deep Purple)** | **Cor Estrutural e de Ação Secundária.** Usada na barra de navegação principal, botões secundários ("Pós-pago"), FAB (Floating Action Button) e barra flutuante de contato. | Menu principal ("Consultas e Relatórios >"), botões secundários nos cards, sticky bar inferior. |
| **Azul Escuro / Marinho** | Fundo de seções de alto impacto, como o Hero Banner, criando contraste absoluto com os botões Magenta e textos brancos. | Fundo da primeira dobra (Hero Section) com o mascote Yeti. |
| **Cores de Apoio (Azul Claro, Verde)** | Azul para botões terciários ("Cadastrar") e Verde exclusivo para ações de sucesso ou contato via WhatsApp. | Botão "Cadastrar" no cabeçalho e botão "WhatsApp" na barra inferior. |

## ✍️ 2. Tipografia
Estratégia focada em clareza, acessibilidade e tom de voz amigável, porém financeiramente seguro.

* **Família Única Sem Serifa (Sans-Serif):** Tipografia geométrica e arredondada (como *Ubuntu*, *Roboto* ou *Inter*), garantindo excelente legibilidade em telas pequenas e grandes.
* **Títulos (H1/H2):** Pesos maiores (Bold). Variam entre Cinza Escuro/Preto para seções padrão e **Magenta** para destacar os benefícios ou passos.
* **Corpo de Texto (Body):** Cinza escuro sobre fundo branco ou cinza muito claro. 
* **Navegação:** Textos em branco nas barras escuras (Roxo) ou cinza escuro nas barras claras (Utility Bar). Estados ativos (Hover/Selected) geralmente ganham sublinhado ou destaque na cor Magenta.

## 🔣 3. Iconografia e Grafismos
* **Mascotes 3D e Ilustrações:** Uso proeminente de personagens 3D (ex: o Yeti, o "bloquinho" retangular roxo com óculos) para humanizar e descontrair a jornada financeira e empresarial.
* **Mockups com "Blobs" Orgânicos:** Telas de aplicativo e notebooks (laptops) são frequentemente apresentados sobrepostos a formas orgânicas/curvas (blobs) nas cores Magenta ou Roxo.
* **Curvas de Interseção:** O design evita cortes retos 100% horizontais no Hero, utilizando curvas acentuadas ou diagonais suaves para separar áreas de cor sólida das fotografias.
* **Estilo de Ícones UI:** Ícones de linha simples (line-art), arredondados. Nas áreas logadas (dashboard), ícones flutuam acima de rótulos em menus de acesso rápido.

## 🧩 4. Componentes e Sistema de Movimento
* **Cards de Produto:** Caixas com fundo branco, cantos bem arredondados (border-radius alto) e sombras sutis (drop-shadow). Estrutura: Imagem/ilustração no topo, título, texto e um grupo de botões na base (muitas vezes divididos em "Pré-pago" Magenta e "Pós-pago" Roxo).
* **Sanfonas (Accordions):** Componentes para FAQ ou Benefícios. Caixas brancas retangulares de largura inteira com ícone de *chevron* (seta) à direita. Ao expandir, revelam o texto interno.
* **Barra Flutuante de Contato (Sticky Bottom Bar):** Um componente crucial (formato "pílula" retangular com cantos arredondados) fixado na parte inferior da tela contendo múltiplos canais de venda: Carrinho, Telefone, Receber Ligação e WhatsApp.
* **Dashboard Logado:** Menu de ícones horizontais circulares/quadrados arredondados para acesso rápido ("Pedir cartão", "Consultar CPF") e banners de publicidade integrados ao layout (ex: LG).

## 💡 5. Diretrizes do Design System
* **Conceito Central:** "Acessibilidade Financeira e Decisões Inteligentes". O design transforma a complexidade de crédito e dívidas em uma interface leve, guiada (step-by-step) e amigável.
* **Espaço e Arredondamento:** Diferente de designs puramente corporativos e "quadrados", a Serasa abusa de cantos arredondados (botões, cards, barras) para passar a sensação de um ambiente "seguro e acolhedor" (B2C e PME).
* **Hierarquia de Ação:** Muito clara. Magenta é o caminho principal que o usuário deve seguir. Roxo é o caminho alternativo. 

## 🏗️ 6. Estrutura de UI e Navegação
* **Navegação em Dois Níveis (Deslogado):**
    * **Topo (Utility Bar):** Fundo branco com abas de segmentação ("Pequenas e Médias Empresas", "Consumidor") e seletor global.
    * **Menu Principal (Main Nav):** Fundo Roxo Escuro, de ponta a ponta, contendo as categorias de produtos com dropdowns indicados por setas. Botões de Login e Cadastro ficam alinhados à direita.
* **Navegação Dashboard (Logado):** Barra branca única com o logo minimalista (S em pontos), links principais centralizados com indicador de página ativa (linha Magenta) e perfil do usuário à direita.
* **Floating Action Button (FAB):** Um botão circular persistente roxo/magenta no canto inferior direito contendo o ícone de chat (atendimento/assistente virtual).

## 🏗️ 7. Logo URL
* **Logo Serasa Experian:** https://pt.wikipedia.org/wiki/Ficheiro:SerasaExperian-TM_Portrait_RGB.svg#/media/Ficheiro:SerasaExperian-TM_Portrait_RGB.svg

---

### Principais atualizações em relação à versão anterior (Nutreco/Trouw):
1. **Mudança da Paleta de Cores:** Substituição do Azul Nutreco/Verde Limão pelo sistema **Magenta + Roxo Escuro** da Serasa.
2. **Arredondamento das Formas:** Transição de caixas (overlay boxes) retangulares de pontas secas para **cards, botões e modais com cantos acentuadamente arredondados** (soft UI).
3. **Introdução de Mascotes e Formas Orgânicas:** Adição de personagens 3D e fundos com "blobs" coloridos em vez de fotografias "edge-to-edge" estritamente corporativas.
4. **Adição de Componentes Específicos:** Inclusão da **Barra Flutuante de Contato Inferior**, estrutura de **Accordions** e o layout dual logado/deslogado.
