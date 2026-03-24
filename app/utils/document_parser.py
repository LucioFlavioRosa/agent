import io
import logging
from docx import Document
from docx.document import Document as _Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.text.paragraph import Paragraph
from docx.table import Table

from llama_cloud import AsyncLlamaCloud
from app.utils.log_formatter import StructuredLogger

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

# Garanta que a instância do logger está assim no topo do arquivo:
logger = StructuredLogger("mcp_doc_structured")

def extrair_texto_docx_em_memoria(file_bytes: bytes, job_id: str = None, company_id: str = None, project_id: str = None) -> str:
    try:
        # 🚀 CORREÇÃO: Usando log_info_negocio
        logger.log_info_negocio(
            "docx_extracao_iniciada", 
            f"Tamanho bytes={len(file_bytes)}", 
            job_id=job_id, 
            company_id=company_id
        )
        
        file_stream = io.BytesIO(file_bytes)
        documento = Document(file_stream)
        texto_extraido = []
        paragrafo_count = 0
        tabela_count = 0
        
        for bloco in iterar_blocos_sequenciais(documento):
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
        
        # 🚀 CORREÇÃO: Usando log_info_negocio
        logger.log_info_negocio(
            "docx_extracao_finalizada", 
            f"Caracteres extraidos={len(resultado)} | paragrafos={paragrafo_count} | tabelas={tabela_count}", 
            job_id=job_id, 
            company_id=company_id
        )
        
        return resultado
        
    except Exception as e:
        # 🚀 AQUI ESTAVA O CRASH! Corrigido para log_erro
        logger.log_erro(
            "docx_extracao_erro", 
            f"Erro ao extrair texto do DOCX: {str(e)}", 
            job_id=job_id, 
            company_id=company_id
        )
        raise



#logger = StructuredLogger("pdf_parser")

async def extrair_texto_pdf_em_memoria(file_bytes: bytes, api_key: str, job_id=None, company_id=None, project_id=None) -> str:
    """
    Recebe os bytes de um PDF do Blob Storage e envia para o LlamaParse em memória.
    """
    logger.log_info_negocio("inicio_parse_pdf", "Iniciando LlamaParse para PDF em memória", job_id=job_id, company_id=company_id)
    
    # Inicializa o client com a chave injetada pelo Vault
    client = AsyncLlamaCloud(api_key=api_key)

    file_tuple = ("documento_referencia.pdf", file_bytes)

    try:
        # Faz o upload
        file_obj = await client.files.create(file=file_tuple, purpose="parse")

        # Inicia o parse com os seus parâmetros otimizados
        result = await client.parsing.parse(
            file_id=file_obj.id,
            tier="agentic",
            version="latest",
            output_options={
                "markdown": {
                    "tables": {
                        "output_tables_as_markdown": True,
                    },
                },
            },
            processing_options={
                "ignore": {
                    "ignore_diagonal_text": True,
                },
                "ocr_parameters": {
                    "languages": ["pt"]
                }
            },
            expand=["text", "markdown", "items", "images_content_metadata"],
        )

        # Junta as páginas
        paginas_markdown = [page.markdown for page in result.markdown.pages]
        texto_unico = "\n\n".join(paginas_markdown)
        
        logger.log_info_negocio("sucesso_parse_pdf", f"PDF processado com sucesso. {len(paginas_markdown)} páginas lidas.", job_id=job_id, company_id=company_id)
        
        return texto_unico

    except Exception as e:
        logger.log_erro("erro_llamaparse", f"Falha ao processar PDF no LlamaCloud: {e}", job_id=job_id, company_id=company_id)
        return ""
