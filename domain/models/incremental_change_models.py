from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal

class CodeTask(BaseModel):
    id: str
    step_number: int
    layer: str
    action: str
    file_path: str
    description: str
    dependencies: List[str] = []
    estimated_tokens: int = 0
    status: Literal['pending', 'running', 'completed', 'failed'] = 'pending'

class TaskDependencyGraph(BaseModel):
    tasks: Dict[str, CodeTask]
    adjacency_list: Dict[str, List[str]]

class TaskExecutionContext(BaseModel):
    task: CodeTask
    related_files: Dict[str, str]
    previous_task_results: List[Dict]

class TaskExecutionResult(BaseModel):
    task_id: str
    success: bool
    modified_files: Dict[str, str]
    error_message: Optional[str] = None
    tokens_used: int = 0
