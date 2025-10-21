from enum import Enum

class WorkflowStepType(Enum):
    GENERATE_REPORT = "generate_report"
    GENERATE_CODE = "generate_code"
    GENERATE_TASKS = "generate_tasks"
    COMMIT_CODE = "commit_code"
    CREATE_EPIC_AND_TASKS = "create_epic_and_tasks"
