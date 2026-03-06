import logging
from datetime import datetime
from app.core.database import db_instance
from app.services.llm_service import generate_html_prototype

logger = logging.getLogger("mcp_prototype.service")

async def fetch_historical_report(job_id: str) -> str:
    if not job_id: return ""
    report = await db_instance.db.project_reports_history.find_one({"job_id": job_id})
    if report and "content" in report:
        return report["content"]
    return ""

async def save_final_report(job_id: str, project_id: str, email: str, category: str, content: str, context_used: dict):
    now = datetime.utcnow()
    report_doc = {
        "job_id": job_id,
        "project_id": project_id,
        "report_category": category,
        "content": content,
        "context_used": context_used,
        "created_by_email": email,
        "created_at": now,
        "status": "done",
        "version": 1
    }
    await db_instance.db.project_reports_history.insert_one(report_doc)
    logger.info(f"💾 [DB] Relatório salvo com sucesso para o Job: {job_id}")

async def process_analysis_task(payload: dict, texto_instrucoes: str, texto_identidade: str):
    job_id = payload.get("job_id")
    project_id = payload.get("project_id")
    email = payload.get("email")
    analysis_type = payload.get("analysis_type", "")
    context_used = payload.get("context_used", {})
    comentario_extra = payload.get("comentario_extra", "")

    logger.info(f"⚙️ [Processamento] Iniciando Job {job_id} | Agente: {analysis_type}")

    # 1. Recuperar Histórico
    texto_epico = await fetch_historical_report(context_used.get("epics_job_id"))
    texto_features = await fetch_historical_report(context_used.get("features_job_id"))
    
    texto_prototipo_base = ""
    is_reviewer = "reviwer" in analysis_type.lower()
    if is_reviewer and "prototype_job_id" in context_used:
        texto_prototipo_base = await fetch_historical_report(context_used.get("prototype_job_id"))

    # 2. Montar Mega Prompt
    mega_prompt = f"""
    Crie um protótipo navegável em HTML, CSS e Javascript (Single-File Component).
    [1. ÉPICOS]\n{texto_epico}\n
    [2. FEATURES]\n{texto_features}
    """
    
    if is_reviewer and texto_prototipo_base:
        mega_prompt += f"\n[3. PROTÓTIPO ANTERIOR (REFINAR)]\n{texto_prototipo_base}"
    if texto_identidade:
        mega_prompt += f"\n[4. IDENTIDADE VISUAL]\n{texto_identidade}"
    if texto_instrucoes:
        mega_prompt += f"\n[5. INSTRUÇÕES GERAIS]\n{texto_instrucoes}"
    if comentario_extra:
        mega_prompt += f"\n[6. PROMPT DO USUÁRIO]\n{comentario_extra}"

    # 3. Chamar IA e Salvar
    html_gerado = await generate_html_prototype(mega_prompt)
    await save_final_report(job_id, project_id, email, "prototype", html_gerado, context_used)
    logger.info(f"✅ [Concluído] Processo finalizado para o Job {job_id}")
