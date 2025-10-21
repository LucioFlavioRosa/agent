class IncrementalStepExecutorService:
    @staticmethod
    def execute_incremental_workflow(job_id, job_info, workflow, start_from_step, repo_reader):
        max_steps_per_batch = job_info['data'].get('MAX_STEPS_PER_BATCH', 3)
        if 'STEP_BATCHES' not in job_info['data'] or not job_info['data']['STEP_BATCHES']:
            report_text = job_info['data'].get('analysis_report')
            if not report_text or not report_text.strip():
                raise ValueError(f"{job_id} ERRO: Relatório aprovado não encontrado para parsing incremental.")
            step_batches = IncrementalStepExecutorService.get_step_batches_from_report(report_text, max_steps_per_batch=max_steps_per_batch)
            job_info['data']['STEP_BATCHES'] = step_batches
            job_info['data']['CURRENT_BATCH_INDEX'] = 0
            job_info['data']['BATCH_RESULTS'] = []
        batch_results = job_info['data'].get('BATCH_RESULTS', [])
        current_batch_index = job_info['data'].get('CURRENT_BATCH_INDEX', 0)
        total_batches = len(job_info['data']['STEP_BATCHES'])
        previous_step_result = None
        for batch_idx in range(current_batch_index, total_batches):
            batch = job_info['data']['STEP_BATCHES'][batch_idx]
            agent_params = {'current_batch': batch, 'total_batches': total_batches}
            # Aqui você pode usar StepStrategyFactory e executar cada step do batch
            # Supondo que cada batch é uma lista de steps
            batch_result = []
            for step in batch:
                step_result = step  # Placeholder para execução real
                batch_result.append(step_result)
            batch_results.append(batch_result)
            job_info['data']['BATCH_RESULTS'] = batch_results
            job_info['data']['CURRENT_BATCH_INDEX'] = batch_idx + 1
        return batch_results

    @staticmethod
    def get_step_batches_from_report(report_text, max_steps_per_batch=3):
        # Implementação simplificada para exemplo
        steps = report_text.split('\n')
        batches = [steps[i:i+max_steps_per_batch] for i in range(0, len(steps), max_steps_per_batch)]
        return batches

    @staticmethod
    def merge_all_batches(batch_results):
        merged = []
        for batch in batch_results:
            merged.extend(batch)
        return merged
