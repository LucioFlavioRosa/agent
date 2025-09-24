import asyncio
import time
import os
from typing import Dict, Any

JOB_TIMEOUT_SECONDS = int(os.getenv('JOB_TIMEOUT_SECONDS', 360))
MONITOR_INTERVAL_SECONDS = 60

RUNNING_STATUSES = ['starting', 'pending_approval', 'workflow_started', 'populating_data', 'committing_to_github']

async def monitor_job_timeouts(job_store, job_handler):
    print(f"[TIMEOUT_MONITOR] Iniciado com timeout de {JOB_TIMEOUT_SECONDS} segundos")
    
    while True:
        try:
            await asyncio.sleep(MONITOR_INTERVAL_SECONDS)
            
            current_time = time.time()
            all_jobs = job_store.get_all_jobs()
            
            if not all_jobs:
                continue
            
            jobs_checked = 0
            jobs_aborted = 0
            
            for job_id, job_data in all_jobs.items():
                if not isinstance(job_data, dict):
                    continue
                
                status = job_data.get('status')
                if status not in RUNNING_STATUSES:
                    continue
                
                jobs_checked += 1
                last_update = job_data.get('last_status_update')
                
                if not last_update:
                    print(f"[TIMEOUT_MONITOR] Job {job_id} sem timestamp, adicionando timestamp atual")
                    job_data['last_status_update'] = current_time
                    job_store.set_job(job_id, job_data)
                    continue
                
                time_since_update = current_time - last_update
                
                if time_since_update > JOB_TIMEOUT_SECONDS:
                    print(f"[TIMEOUT_MONITOR] Job {job_id} excedeu timeout ({time_since_update:.1f}s > {JOB_TIMEOUT_SECONDS}s). Abortando...")
                    
                    try:
                        job_handler.abort_job_due_to_timeout(job_id, job_data)
                        jobs_aborted += 1
                        print(f"[TIMEOUT_MONITOR] Job {job_id} abortado com sucesso")
                    except Exception as e:
                        print(f"[TIMEOUT_MONITOR] ERRO ao abortar job {job_id}: {str(e)}")
            
            if jobs_checked > 0:
                print(f"[TIMEOUT_MONITOR] Verificados {jobs_checked} jobs em execução, {jobs_aborted} abortados por timeout")
                
        except Exception as e:
            print(f"[TIMEOUT_MONITOR] ERRO no monitor de timeout: {str(e)}")
            await asyncio.sleep(30)