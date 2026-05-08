from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sqlalchemy import select

# Schemas
from domain.schemas.ClienteSchema import (
    ClienteCreate,
    ClienteResponse,
    ClienteUpdate
)
from domain.schemas.AuthSchema import FuncionarioAuth

# ORM
from infra.orm.ClienteModel import ClienteDB

# Database
from infra.database import get_async_db
from infra.dependencies import get_current_active_user, require_group
from infra.rate_limit import limiter, get_rate_limit
from services.AuditoriaService import AuditoriaService

router = APIRouter()


# GET TODOS CLIENTES
@router.get(
    "/cliente/",
    response_model=List[ClienteResponse],
    tags=["Cliente"],
    status_code=status.HTTP_200_OK,
    
)
async def get_clientes(
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user),
):
    try:
        result = await db.execute(select(ClienteDB))
        clientes = result.scalars().all()
        return clientes
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar clientes: {str(e)}"
        )


# GET CLIENTE POR ID
@router.get(
    "/cliente/{id}",
    response_model=ClienteResponse,
    tags=["Cliente"],
    status_code=status.HTTP_200_OK
)
async def get_cliente(
    id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user),
):

    try:
        result = await db.execute(select(ClienteDB).where(ClienteDB.id == id))
        cliente = result.scalar_one_or_none()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        return cliente
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar cliente: {str(e)}")


    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar cliente: {str(e)}"
        )


# POST CLIENTE
@router.post(
    "/cliente/",
    response_model=ClienteResponse,
    tags=["Cliente"],
    status_code=status.HTTP_201_CREATED
)
async def post_cliente(
    cliente_data: ClienteCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3])),
):

    try:

        # Verificar CPF duplicado (Assíncrono)
        result = await db.execute(
            select(ClienteDB).where(ClienteDB.cpf == cliente_data.cpf)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail="Já existe cliente com este CPF"
            )

        novo_cliente = ClienteDB(
            nome=cliente_data.nome, cpf=cliente_data.cpf, telefone=cliente_data.telefone
        )

        db.add(novo_cliente)
        await db.commit()
        await db.refresh(novo_cliente)
        return novo_cliente
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao criar cliente: {str(e)}")


# PUT CLIENTE
@router.put(
    "/cliente/{id}",
    response_model=ClienteResponse,
    tags=["Cliente"],
    status_code=status.HTTP_200_OK,
)
@limiter.limit(get_rate_limit("moderate"))

async def put_cliente(
    id: int,
    request: Request,
    cliente_data: ClienteUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3])),
):

    try:

        result = await db.execute(select(ClienteDB).where(ClienteDB.id == id))
        cliente = result.scalar_one_or_none()

        if not cliente:
            raise HTTPException(
                status_code=404,
                detail="Cliente não encontrado"
            )

        # verificar CPF duplicado
        if cliente_data.cpf and cliente_data.cpf != cliente.cpf:

            existing_cliente = db.query(ClienteDB).filter(
                ClienteDB.cpf == cliente_data.cpf
            ).first()

            if existing_cliente:
                raise HTTPException(
                    status_code=400,
                    detail="Já existe cliente com este CPF"
                )

        dados_antigos = cliente.__dict__.copy()
        update_data = cliente_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(cliente, field, value)

        await db.commit()
        await db.refresh(cliente)

        await AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="UPDATE",
            recurso="CLIENTE",
            recurso_id=id,
            dados_antigos=dados_antigos,
            dados_novos=cliente,
            request=request,
        ) 

        return cliente

    except HTTPException:
        raise
    except Exception as e:

        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar cliente: {str(e)}"
        )


# DELETE CLIENTE
@router.delete(
    "/cliente/{id}",
    tags=["Cliente"],
    status_code=status.HTTP_200_OK
)


async def delete_cliente(
    id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):
    """Remove um cliente"""
    try:

        cliente = db.query(ClienteDB).filter(
            ClienteDB.id == id
        ).first()

        if not cliente:
            raise HTTPException(
                status_code=404,
                detail="Cliente não encontrado"
            )

        await db.delete(cliente)
        await db.commit()

        return {"message": "Cliente deletado com sucesso"}

    except HTTPException:
        raise
    except Exception as e:

        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao deletar cliente: {str(e)}"
        )
