import io
from docx import Document
from docx.document import Document as _Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.text.paragraph import Paragraph
from docx.table import Table

def iterar_blocos_sequenciais(parent):
    """
    Desce no XML do Word para gerar os blocos (Parágrafos e Tabelas) 
    exatamente na ordem em que aparecem visualmente no documento.
    """
    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    else:
        raise ValueError("Suporte apenas para o objeto Document principal.")

    # Itera sobre os "filhos" do corpo do XML na ordem em que aparecem
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            # Encontrou a tag XML de um Parágrafo (<w:p>)
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            # Encontrou a tag XML de uma Tabela (<w:tbl>)
            yield Table(child, parent)

def extrair_texto_docx_em_memoria(file_bytes: bytes) -> str:
    """
    Recebe os bytes do .docx e extrai o texto mantendo o contexto 
    perfeito entre parágrafos e tabelas.
    """
    file_stream = io.BytesIO(file_bytes)
    documento = Document(file_stream)
    
    texto_extraido = []
    
    for bloco in iterar_blocos_sequenciais(documento):
        
        # Se o bloco for um parágrafo de texto normal
        if isinstance(bloco, Paragraph):
            texto = bloco.text.strip()
            if texto:
                texto_extraido.append(texto)
                
        # Se o bloco for uma tabela
        elif isinstance(bloco, Table):
            texto_extraido.append("\n[--- Início da Tabela ---]")
            
            for linha in bloco.rows:
                linha_texto = []
                for celula in linha.cells:
                    # Limpa quebras de linha para manter a estrutura da célula em uma linha só
                    texto_celula = celula.text.strip().replace('\n', ' ')
                    linha_texto.append(texto_celula)
                
                # Junta as colunas com ' | ' para o LLM entender a formatação
                texto_extraido.append(" | ".join(linha_texto))
                
            texto_extraido.append("[--- Fim da Tabela ---]\n")

    return "\n".join(texto_extraido)
