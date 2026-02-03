from pydantic import BaseModel

class UserGroupMapping(BaseModel):
    usuario: str
    empresa: str
    grupo: str
