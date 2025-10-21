import re

class EpicMarkdownParser:
    def parse(self, markdown_table):
        lines = markdown_table.strip().split('\n')
        if not lines or len(lines) < 3:
            return []
        header = lines[0]
        columns = [col.strip() for col in header.split('|') if col.strip()]
        epics = []
        for line in lines[2:]:
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if len(cells) != len(columns):
                continue
            epic_dict = {}
            for idx, col in enumerate(columns):
                key = col.replace(' ', '_').replace('/', '').lower()
                epic_dict[key] = cells[idx]
            # Map required fields
            epic_dict['epic_id'] = epic_dict.get('passo', epic_dict.get('id'))
            epic_dict['epic_title'] = epic_dict.get('epico')
            epic_dict['objetivo_negocio'] = epic_dict.get('objetivo_de_negocio')
            epic_dict['criterios_aceite'] = epic_dict.get('criterios_de_aceite__atividades_chave')
            epic_dict['perfis_envolvidos'] = epic_dict.get('perfis_envolvidos')
            epic_dict['estimativa_esforco'] = epic_dict.get('estimativa_de_esforco')
            # Validation
            required = ['epic_id', 'epic_title', 'objetivo_negocio']
            if all(epic_dict.get(field) for field in required):
                epics.append(epic_dict)
        return epics
