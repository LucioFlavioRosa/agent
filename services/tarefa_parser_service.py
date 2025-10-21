import re
from typing import List, Optional
from models import TarefaCard

class TarefaParserService:
    @staticmethod
    def parse_tarefas_from_report(report_text: str, epico_id: Optional[str] = None, epico_nome: Optional[str] = None) -> List[TarefaCard]:
        if not report_text:
            print(f"[TarefaParserService] Report text vazio.")
            return []
        tarefas = []
        # Busca por blocos de tarefas agrupados por épico
        # Exemplo: Tarefas aparecem após um cabeçalho como '## Tarefas do Épico E05' ou '## Tarefas do Épico Interface de Validação...'
        # Regex para encontrar blocos por ID ou título
        bloco_regex_id = None
        bloco_regex_nome = None
        if epico_id:
            bloco_regex_id = re.compile(r'(?:##\s*Tarefas do [Éé]pico\s*' + re.escape(epico_id) + r'|###\s*' + re.escape(epico_id) + r')', re.IGNORECASE)
        if epico_nome:
            bloco_regex_nome = re.compile(r'(?:##\s*Tarefas do [Éé]pico\s*' + re.escape(epico_nome) + r'|###\s*' + re.escape(epico_nome) + r')', re.IGNORECASE)
        # Divide por linhas
        lines = report_text.splitlines()
        start_idx = None
        end_idx = None
        for idx, line in enumerate(lines):
            if bloco_regex_id and bloco_regex_id.search(line):
                start_idx = idx
                break
            if bloco_regex_nome and bloco_regex_nome.search(line):
                start_idx = idx
                break
        if start_idx is not None:
            # Busca pelo próximo cabeçalho para delimitar o bloco
            for idx2 in range(start_idx + 1, len(lines)):
                if lines[idx2].startswith('##') or lines[idx2].startswith('| ID |'):
                    end_idx = idx2
                    break
            bloco_tarefas = lines[start_idx:end_idx] if end_idx else lines[start_idx:]
        else:
            bloco_tarefas = lines
        # Regex para linhas de tarefas
        tarefa_regex = re.compile(r'\{\s*"id":\s*"(T\d+)",\s*"titulo":\s*"([^"]+)",\s*"descricao":\s*"([^"]+)",.*?"criterios_de_aceite":\s*"([^"]*)",.*?"perfis_sugeridos":\s*\[(.*?)\],.*?"estimativa_sp":\s*(\d+)', re.DOTALL)
        # Alternativamente, busca por linhas que parecem JSON de tarefa
        tarefa_blocks = []
        buffer = []
        in_tarefa = False
        for line in bloco_tarefas:
            if line.strip().startswith('{'):
                in_tarefa = True
                buffer = [line.strip()]
            elif in_tarefa:
                buffer.append(line.strip())
                if line.strip().endswith('}'):  # fim do bloco
                    tarefa_blocks.append(' '.join(buffer))
                    in_tarefa = False
        for tb in tarefa_blocks:
            try:
                match = tarefa_regex.search(tb)
                if match:
                    id_tarefa = match.group(1)
                    titulo = match.group(2)
                    descricao = match.group(3)
                    criterios_aceite = match.group(4)
                    perfis_raw = match.group(5)
                    estimativa_sp = match.group(6)
                    perfis = [p.strip(' "') for p in perfis_raw.split(',') if p.strip()]
                    tarefa = TarefaCard(
                        id=id_tarefa,
                        titulo_tarefa=titulo,
                        descricao_tarefa=descricao,
                        epico_id=epico_id if epico_id else '',
                        estimativa_tempo=estimativa_sp,
                        criterios_aceite=criterios_aceite,
                        epico_nome=epico_nome
                    )
                    tarefas.append(tarefa)
            except Exception as e:
                print(f"[TarefaParserService] Erro ao parsear tarefa: {e}")
        print(f"[TarefaParserService] Tarefas encontradas para epico_id='{epico_id}', epico_nome='{epico_nome}': {len(tarefas)}")
        return tarefas
