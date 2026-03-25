# André Nícolas Granemann Coelho

from fastapi import APIRouter
from domain.entities.Produto import Produto

router = APIRouter()

@router.get("/produto/", tags=["Produto"], status_code=200)
async def get_produto():
    return {"msg": "produto get todos executado"}

@router.post("/produto/", tags=["Produto"], status_code=200)
async def post_produto(corpo: Produto):
    return {"msg": "produto post executado", "nome": corpo.nome, "valor": corpo.valor_unitario}

@router.put("/produto/{id}", tags=["Produto"], status_code=200)
async def put_produto(id: int, corpo: Produto):
  return {"msg": "produto put executado", "id": id, "nome": corpo.nome, "cpf": corpo.cpf, "telefone": corpo.telefone}

@router.delete("/produto/{id}", tags=["Produto"], status_code=200)
async def delete_produto(id: int):
  return {"msg": "produto delete executado", "id":id}