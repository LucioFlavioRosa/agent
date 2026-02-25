import io
import logging
from docx import Document
from docx.document import Document as _Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.text.paragraph import Paragraph
from docx.table import Table

logger = logging.getLogger("mcp_docx_parser")

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

def extrair_texto_docx_em_memoria(file_bytes: bytes, job_id: str = None, company_id: str = None, project_id: str = None) -> str:
    """
    Recebe os bytes do .docx e extrai o texto mantendo o contexto 
    perfeito entre parágrafos e tabelas.
    Adiciona logs detalhados para rastreabilidade no App Service Azure.
    """
    contexto_log = f"job_id={job_id} company_id={company_id} project_id={project_id}" if job_id or company_id or project_id else ""
    try:
        logger.info(f"[DOCX_PARSER] Entrada no extrair_texto_docx_em_memoria: tamanho={len(file_bytes)} bytes {contexto_log}")
        file_stream = io.BytesIO(file_bytes)
        documento = Document(file_stream)
        logger.info(f"[DOCX_PARSER] Iniciando iteração de blocos do documento {contexto_log}")
        texto_extraido = []
        bloco_idx = 0
        for bloco in iterar_blocos_sequenciais(documento):
            bloco_idx += 1
            if isinstance(bloco, Paragraph):
                texto = bloco.text.strip()
                logger.debug(f"[DOCX_PARSER] Processando parágrafo #{bloco_idx}: '{texto[:60]}' {contexto_log}")
                if texto:
                    texto_extraido.append(texto)
            elif isinstance(bloco, Table):
                logger.info(f"[DOCX_PARSER] Início da tabela #{bloco_idx} {contexto_log}")
                texto_extraido.append("\n[--- Início da Tabela ---]")
                for linha in bloco.rows:
                    linha_texto = []
                    for celula in linha.cells:
                        texto_celula = celula.text.strip().replace('\n', ' ')
                        linha_texto.append(texto_celula)
                    texto_extraido.append(" | ".join(linha_texto))
                texto_extraido.append("[--- Fim da Tabela ---]\n")
                logger.info(f"[DOCX_PARSER] Fim da tabela #{bloco_idx} {contexto_log}")
        resultado = "\n".join(texto_extraido)
        logger.info(f"[DOCX_PARSER] Extração finalizada: {len(resultado)} caracteres extraídos {contexto_log}")
        return resultado
    except Exception as e:
        logger.error(f"[DOCX_PARSER] ERRO ao extrair texto do DOCX {contexto_log}: {str(e)}", exc_info=True)
        raise
