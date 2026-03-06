import io
import logging
from docx import Document
from docx.document import Document as _Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.text.paragraph import Paragraph
from docx.table import Table

logger = logging.getLogger("mcp_doc_structured")

def iterar_blocos_sequenciais(parent):
    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    else:
        raise ValueError("Suporte apenas para o objeto Document principal.")
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

def extrair_texto_docx_em_memoria(file_bytes: bytes, job_id: str = None, company_id: str = None, project_id: str = None) -> str:
    contexto_log = f"job_id={job_id} company_id={company_id} project_id={project_id}" if job_id or company_id or project_id else ""
    try:
        logger.info(f"docx_extracao_iniciada | tamanho_bytes={len(file_bytes)} | {contexto_log}")
        file_stream = io.BytesIO(file_bytes)
        documento = Document(file_stream)
        texto_extraido = []
        bloco_idx = 0
        paragrafo_count = 0
        tabela_count = 0
        for bloco in iterar_blocos_sequenciais(documento):
            bloco_idx += 1
            if isinstance(bloco, Paragraph):
                texto = bloco.text.strip()
                if texto:
                    texto_extraido.append(texto)
                    paragrafo_count += 1
            elif isinstance(bloco, Table):
                texto_extraido.append("\n[--- Início da Tabela ---]")
                for linha in bloco.rows:
                    linha_texto = []
                    for celula in linha.cells:
                        texto_celula = celula.text.strip().replace('\n', ' ')
                        linha_texto.append(texto_celula)
                    texto_extraido.append(" | ".join(linha_texto))
                texto_extraido.append("[--- Fim da Tabela ---]\n")
                tabela_count += 1
        resultado = "\n".join(texto_extraido)
        logger.info(f"docx_extracao_finalizada | caracteres_extraidos={len(resultado)} | paragrafos={paragrafo_count} | tabelas={tabela_count} | {contexto_log}")
        return resultado
    except Exception as e:
        logger.error(f"docx_extracao_erro | {contexto_log} | erro={str(e)}")
        raise
