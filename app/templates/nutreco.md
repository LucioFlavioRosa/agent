# Descritivo Objetivo para o Agente de UI/UX: Nutreco & Trouw Nutrition (Revisado)

Este documento detalha os elementos visuais e diretrizes de design para a construção de protótipos e interfaces institucionais, atualizado com base no design system atual da web.

## 🎨 1. Paleta de Cores (Brand Colors)
A identidade visual baseia-se em fundos limpos (brancos e cinzas claros), fontes escuras para contraste e cores de destaque vibrantes para guiar a atenção do usuário.

| Cor | Aplicação Principal | Evidência Visual |
| :--- | :--- | :--- |
| **Branco e Off-White** | Superfície padrão do site, fundos de seções de texto e contêineres de conteúdo principal, garantindo máximo respiro e legibilidade. | Fundo predominante em todas as telas de leitura. |
| **Magenta Institucional / Rosa Escuro** | **Cor de Ação Primária (Accent/CTA).** Usada em caixas de texto sobrepostas a imagens, botões Flutuantes (FAB), marcadores de linha do tempo e painéis de vídeo. | Box "Our purpose", botões "Read our story", FAB inferior direito, marcador "1899". |
| **Azul Corporativo (Nutreco Blue)** | Logotipo, textos de navegação principal e elementos de texto de apoio estrutural. | Logotipo no cabeçalho e tipografia dos menus. |
| **Verde Limão / Earls Green** | Fundos de cards específicos de divisões de negócios (ex: Skretting, Trouw Nutrition). | Cards "Read more" na página de Transparência. |
| **Paleta de Infográficos (Nutrace)** | Cores semânticas para pilares (Teal, Laranja/Amarelo, Verde, Bordô, Azul Escuro). | Gráfico da página de Qualidade (Nutrace). |

## ✍️ 2. Tipografia
Estratégia focada em clareza, modernidade e legibilidade corporativa.

* **Família Única Sem Serifa (Sans-Serif):** O site utiliza uma tipografia geométrica e limpa (como *Poppins*, *Montserrat* ou *Helvetica*) para **todos** os níveis de texto.
* **Títulos (H1/H2):** Uso de pesos maiores (Bold/Medium) com cores escuras ou branco (quando sobreposto ao Magenta).
* **Corpo de Texto (Body):** Cinza escuro sobre fundo branco, com entrelinhas generoso para facilitar a leitura de blocos longos.
* **Navegação (Menus e Breadcrumbs):** Fontes menores, limpas e com hiperlinks indicados pelo contexto e interatividade (hover).

## 🔣 3. Iconografia e Grafismos
* **Estilo de Ícones UI:** Ícones brancos vazados ou sólidos aplicados sobre fundos coloridos (ex: Ícone de corrente/link no FAB magenta inferior direito, ícone de *Play* de vídeo e lupa de pesquisa).
* **Infográficos (Sistemas/Processos):** Uso de diagramas com linhas degradê, ícones circulares e cores distintas para cada pilar estratégico, indicando processos estruturados (ex: Programa Nutrace).

## 🧩 4. Componentes e Sistema de Movimento
* **Caixas de Sobreposição (Overlay Boxes):** O padrão de UI mais marcante. Caixas retangulares de cor sólida (frequentemente Magenta) sobrepostas a imagens grandes (Hero Images). Elas abrigam o título, subtítulo e chamadas de ação.
* **Navegação em Dois Níveis:**
    * **Topo (Utility Bar):** Fundo cinza super claro com links de negócios, carreiras, notícias e idioma.
    * **Menu Principal (Main Nav):** Fundo branco, com o logo à esquerda e menus em cascata (dropdowns) com indicador visual de seta.
* **Componente de Linha do Tempo (Timeline):** Eixo vertical tracejado central com caixas flutuantes contendo os anos (em Magenta). Abaixo, cards com imagem à esquerda e texto descritivo à direita.
* **Botões Interativos:**
    * **Caixas Clicáveis:** Em vez de botões tradicionais arredondados, muitas áreas clicáveis são blocos retangulares inteiros (ex: blocos "Who we are" nos vídeos).
    * **Botões Secundários:** Botões retangulares brancos com texto escuro sobre fundos coloridos (como nos cards verdes da Skretting/Trouw).

## 💡 5. Diretrizes do Design System
* **Conceito Central:** "Feeding the Future" (Alimentando o Futuro). Focado no lado humano, sustentável e tecnológico.
* **Uso de Imagens:** Fotografias de altíssima qualidade que ocupam toda a largura da tela (edge-to-edge). Mescla de cenários humanos comunitários (pessoas à mesa) e imagens industriais/naturais de precisão (tanques de aquicultura, fazendas).
* **Espaço em Branco (White Space):** Uso abundante de respiros entre os blocos de texto para transmitir uma leitura "clínica", transparente e profissional.

## 🏗️ 6. Estrutura de UI e Navegação
* **Breadcrumbs (Trilha de migalhas):** Presença contínua abaixo do cabeçalho em páginas internas para situar o usuário (ex: *Home > Innovation & investments > Nutreco Exploration*).
* **Floating Action Button (FAB):** Um botão circular persistente no canto inferior direito para acesso rápido a funções contextuais ou comunicação.
* **Layout de Seções Claras:** O conteúdo é dividido em faixas horizontais de largura total, alternando entre imagens de fundo e áreas brancas apenas com texto.

## 🏗️ 7. Logo URL
url_logo_comgas: (https://upload.wikimedia.org/wikipedia/commons/5/50/LogoNutreco_trans.gif)

---

### Principais correções em relação à versão original:
1. **Remoção do foco excessivo no azul e verde como CTA:** A cor interativa principal que guia o usuário no site é nitidamente o **Magenta/Rosa**, não o verde "La Rioja".
2. **Atualização da estrutura dos botões:** O site abusa de *blocos/caixas retangulares inteiros* como CTA sobre imagens, em vez de botões clássicos isolados.
3. **Adição dos Breadcrumbs e do FAB:** Elementos estruturais vitais para a experiência de navegação do usuário.
