from pydantic import BaseModel

class UserContext(BaseModel):
    email: str
    empresa: str
