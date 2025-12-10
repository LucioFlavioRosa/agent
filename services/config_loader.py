import yaml
from models.task_config import TaskConfig

def load_task_config(analysis_type: str) -> TaskConfig:
    with open('config_tasks.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    if analysis_type not in config:
        raise KeyError(f"Analysis type '{analysis_type}' not found in config_tasks.yaml")
    task_cfg = config[analysis_type]
    return TaskConfig(**task_cfg)
