from fastapi import APIRouter, HTTPException, Body, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, Optional
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.project_state_service import ProjectStateService
from backend.app.middleware.auth_middleware import get_current_user, _extract_usuario_executor
import logging

router = APIRouter()

class UpdateReportRequest(BaseModel):
    report_data: Dict[str, Any]

@router.get("/project/{project_id}/reports")
async def get_project_reports(
    project_id: str,
    job_id: Optional[str] = Query(None, description="ID do job para acompanhamento de status do processamento"),
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = _extract_usuario_executor(current_user)
    logger = logging.getLogger("session_api")
    redis_service = RedisSessionService()

    # 1. TENTA CARREGAR O ARQUIVO FINAL (A VERDADE ABSOLUTA)
    # Se o arquivo existe, retornamos ele. Não importa o que o Redis diz sobre datas.
    blob_state = None
    try:
        blob_state = await ProjectStateService.load_all_states_from_blob(usuario_executor, project_id)
        
        # Verificação simples: Se o blob retornou algo que não seja vazio, é sucesso.
        if blob_state:
            # Verifica se tem algum conteúdo real dentro (epicos, features, etc)
            tem_conteudo = False
            chaves_indicadoras = ["epicos_report", "features_report", "resumo_report", "epicos", "features"]
            
            for chave in chaves_indicadoras:
                if blob_state.get(chave) or (isinstance(blob_state.get(chave), list) and len(blob_state.get(chave)) > 0):
                    tem_conteudo = True
                    break
            
            # Se achamos o blob, confiamos nele cegamente.
            if tem_conteudo or blob_state: 
                logger.info(f"✅ Blob encontrado para {project_id}. Retornando 200 (Ignorando datas).")
                return _format_state_response(blob_state)

    except Exception as e:
        logger.warning(f"Erro ao tentar ler blob: {e}")

    # 2. SE NÃO TEM BLOB, VERIFICA O REDIS PARA DAR SATISFAÇÃO (202)
    active_job = redis_service.get_active_job_for_project(project_id)
    latest_done_job = redis_service.get_latest_done_job_for_project(project_id)

    if active_job:
        # Lógica Anti-Zumbi baseada APENAS em ID (Sem datas)
        if latest_done_job and active_job.job_id == latest_done_job.job_id:
            # O job que está "ativo" é exatamente o mesmo que já deu "done".
            # Isso é apenas o Redis desatualizado.
            # Como falhamos em ler o blob acima (talvez delay de propagação), 
            # aqui poderíamos tentar ler de novo ou retornar 404 temporário, 
            # mas NÃO retornamos 202 porque sabemos que acabou.
            logger.info(f"👻 Job {active_job.job_id} consta como ativo mas ID bate com último done. Redis sujo.")
            # Se caiu aqui, é porque o blob falhou ou está vazio, mas o job acabou.
            # Vamos retornar 404 sugerindo retry, ou dict vazio, mas não travamos em 202.
            raise HTTPException(status_code=404, detail="Processamento finalizado, mas arquivo ainda não encontrado no storage. Tente novamente em instantes.")

        # Se IDs são diferentes, é um job novo de verdade.
        return JSONResponse(
            content={
                "status": "processing",
                "message": "O processamento está em andamento.",
                "job_id": active_job.job_id,
                "project_id": project_id
            },
            status_code=status.HTTP_202_ACCEPTED
        )

    # 3. Sem blob e sem job ativo -> 404
    raise HTTPException(status_code=404, detail="Projeto não encontrado ou ainda não iniciado.")

def _format_state_response(state: dict):
    """Garante que a resposta tenha os campos de lista vazios em vez de None"""
    report_fields = ["epicos", "features", "times_descricao", "alocacao_times", "premissas_riscos"]
    for field in report_fields:
        if state.get(field) is None:
            state[field] = {} 
        
        report_key = field + "_report"
        if state.get(report_key) is None:
             if state[field].get(report_key) is None:
                 state[field][report_key] = []
    return state

# ... (Mantenha os outros endpoints inalterados) ...
@router.get("/project/{project_id}/report/{report_type}")
async def get_project_report_state(project_id: str, report_type: str, current_user: dict = Depends(get_current_user)):
    try:
        state = await ProjectStateService.get_report_state(project_id, report_type)
        if not state:
            raise HTTPException(status_code=404, detail=f"Estado do report '{report_type}' não encontrado para project_id '{project_id}'")
        return state
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Erro ao buscar estado do report: {e}")

@router.put("/project/{project_id}/report")
def update_project_report(project_id: str, req: UpdateReportRequest):
    redis_service = RedisSessionService()
    try:
        if not req.report_data or not isinstance(req.report_data, dict) or len(req.report_data) != 1:
            raise HTTPException(status_code=400, detail="report_data deve ser um dicionário com exatamente uma chave de relatório.")
        redis_service.update_report(project_id, req.report_data)
        session = redis_service.get_session_by_project_id(project_id)
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(ProjectStateService.save_state_to_blob(session))
        else:
            loop.run_until_complete(ProjectStateService.save_state_to_blob(session))
        return {"status": "ok", "project_id": project_id, "nome_projeto": session.nome_projeto}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar relatório: {e}")

@router.post("/project/{project_id}/save-state")
async def save_project_state(project_id: str):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session_by_project_id(project_id)
        url = await ProjectStateService.save_state_to_blob(session)
        return {"blob_url": url, "project_id": session.project_id, "nome_projeto": session.nome_projeto}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar estado: {e}")

@router.get("/project/{project_id}/docx-files")
def get_project_docx_files(project_id: str):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session_by_project_id(project_id)
        return {"docx_files": session.docx_files, "project_id": session.project_id, "nome_projeto": session.nome_projeto}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Projeto não encontrado: {e}")
