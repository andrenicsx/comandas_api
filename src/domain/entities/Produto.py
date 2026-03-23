from pydantic import BaseModel
# André Nícolas Granemann Coelho

class Produto(BaseModel):
    id_produto: int = None
    nome: str
    descricao: str = None
    valor_unitario: float