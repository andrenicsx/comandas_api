from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from infra.rate_limit import limiter, get_rate_limit
from services.AuditoriaService import AuditoriaService

# Schemas
from domain.schemas.AuthSchema import FuncionarioAuth
from domain.schemas.ProdutoSchema import (
    ProdutoCreate,
    ProdutoUpdate,
    ProdutoResponse
)

# ORM
from infra.orm.ProdutoModel import ProdutoDB
from infra.dependencies import get_current_active_user, require_group

# Database
from infra.database import get_async_db

router = APIRouter()

# GET TODOS PRODUTOS
@router.get(
    "/produto/",
    response_model=List[ProdutoResponse],
    tags=["Produto"],
    status_code=status.HTTP_200_OK
)
async def get_produtos(db: AsyncSession = Depends(get_async_db)):
    try:
        result = await db.execute(select(ProdutoDB))
        return result.scalars().all()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar produtos: {str(e)}"
        )


# GET PRODUTO POR ID
@router.get(
    "/produto/{id}",
    response_model=ProdutoResponse,
    tags=["Produto"],
    status_code=status.HTTP_200_OK
)
async def get_produto(id: int, db: AsyncSession = Depends(get_async_db)):

    try:
        result = await db.execute(select(ProdutoDB).where(ProdutoDB.id == id))
        produto = result.scalar_one_or_none()

        if not produto:
            raise HTTPException(
                status_code=404,
                detail="Produto não encontrado"
            )

        return produto

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar produto: {str(e)}"
        )


# POST PRODUTO
@router.post(
    "/produto/",
    response_model=ProdutoResponse,
    tags=["Produto"],
    status_code=status.HTTP_201_CREATED
)
async def post_produto(
    produto_data: ProdutoCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):

    try:

        novo_produto = ProdutoDB(
            nome=produto_data.nome,
            descricao=produto_data.descricao,
            foto=produto_data.foto,
            valor_unitario=produto_data.valor_unitario
        )

        db.add(novo_produto)
        await db.commit()
        await db.refresh(novo_produto)

        return novo_produto

    except Exception as e:

        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar produto: {str(e)}"
        )


# PUT PRODUTO
@router.put(
    "/produto/{id}",
    response_model=ProdutoResponse,
    tags=["Produto"],
    status_code=status.HTTP_200_OK
)
async def put_produto(
    id: int,
    produto_data: ProdutoUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):

    try:

        produto = db.query(ProdutoDB).filter(
            ProdutoDB.id == id
        ).first()

        if not produto:
            raise HTTPException(
                status_code=404,
                detail="Produto não encontrado"
            )

        update_data = produto_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(produto, field, value)

        await db.commit()
        await db.refresh(produto)

        return produto

    except HTTPException:
        raise
    except Exception as e:

        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar produto: {str(e)}"
        )


# DELETE PRODUTO
@router.delete("/produto/{id}", tags=["Produto"], status_code=status.HTTP_200_OK)
@limiter.limit(get_rate_limit("critical"))

async def delete_produto(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):

    try:

        result = await db.execute(select(ProdutoDB).where(ProdutoDB.id == id))
        produto = result.scalar_one_or_none()

        if not produto:
            raise HTTPException(
                status_code=404,
                detail="Produto não encontrado"
            )

        dados_antigos = produto.__dict__.copy()
        await db.delete(produto)
        await db.commit()

        await AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="DELETE",
            recurso="PRODUTO",
            recurso_id=id,
            dados_antigos=dados_antigos,
            request=request,
        )

        return {"message": "Produto excluído com sucesso"}

    except HTTPException:
        raise
    except Exception as e:

        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao deletar produto: {str(e)}"
        )
