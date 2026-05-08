from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from slowapi.errors import RateLimitExceeded
from services.AuditoriaService import AuditoriaService

# Domain Schemas
from domain.schemas.FuncionarioSchema import (
    FuncionarioCreate,
    FuncionarioUpdate,
    FuncionarioResponse,
)
from domain.schemas.AuthSchema import FuncionarioAuth

# Infra
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.database import get_async_db
from infra.security import get_password_hash
from infra.dependencies import get_current_active_user, require_group
from infra.rate_limit import limiter, get_rate_limit


router = APIRouter()

# Criar as rotas/endpoints: GET, POST, PUT, DELETE


@router.get(
    "/funcionario/",
    response_model=List[FuncionarioResponse],
    tags=["Funcionário"],
    status_code=status.HTTP_200_OK,
    summary="Listar todos os funcionários - protegida por autenticação e grupo 1")
@limiter.limit(get_rate_limit("moderate"))

async def get_funcionarios(
    request : Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):
    """Retorna todos os funcionários"""
    try:
        result = await db.execute(select(FuncionarioDB))
        funcionarios = result.scalars().all()
        return funcionarios
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar funcionários: {str(e)}",
        )


@router.get(
    "/funcionario/{id}",
    response_model=FuncionarioResponse,
    tags=["Funcionário"],
    status_code=status.HTTP_200_OK,
    summary="Buscar funcionário por ID",
)
async def get_funcionario(
    id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user),
):
    """Retorna um funcionário específico pelo ID - protegida por autenticação"""
    try:
        result = await db.execute(select(FuncionarioDB).where(FuncionarioDB.id == id))
        funcionario = result.scalar_one_or_none()

        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Funcionário não encontrado",
            )

        return funcionario
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar funcionário: {str(e)}",
        )


@router.post(
    "/funcionario/",
    response_model=FuncionarioResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Funcionário"],
    summary="Criar novo funcionário",
)
async def post_funcionario(
    funcionario_data: FuncionarioCreate,
    request : Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):
    """Cria um novo funcionário - protegida por autenticação e grupo 1"""
    try:
        # Verifica se já existe funcionário com este CPF
        result = await db.execute(
            select(FuncionarioDB).where(FuncionarioDB.cpf == funcionario_data.cpf)
        )
        existing_funcionario = result.scalar_one_or_none()

        if existing_funcionario:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um funcionário com este CPF",
            )

        # Hash da senha
        hashed_password = get_password_hash(funcionario_data.senha)

        # Cria o novo funcionário
        novo_funcionario = FuncionarioDB(
            nome=funcionario_data.nome,
            matricula=funcionario_data.matricula,
            cpf=funcionario_data.cpf,
            telefone=funcionario_data.telefone,
            grupo=funcionario_data.grupo,
            senha=hashed_password,
        )

        db.add(novo_funcionario)
        await db.commit()
        await db.refresh(novo_funcionario)

        # Depois de tudo executado e antes do return, registra a ação na auditoria
        await AuditoriaService.registrar_acao(
        db=db,
        funcionario_id=current_user.id,
        acao="CREATE",
        recurso="FUNCIONARIO",
        recurso_id=novo_funcionario.id,
        dados_antigos=None,
        dados_novos=novo_funcionario, # Objeto SQLAlchemy com dados novos
        request=request # Request completo para capturar IP e user agent
        )

        return novo_funcionario

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar funcionário: {str(e)}",
        )


@router.put(
    "/funcionario/{id}",
    response_model=FuncionarioResponse,
    tags=["Funcionário"],
    status_code=status.HTTP_200_OK,
    summary="Atualizar funcionário",
)
async def put_funcionario(
    id: int,
    funcionario_data: FuncionarioUpdate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):
    """Atualiza um funcionário existente - protegida por autenticação e grupo 1"""
    try:
        result = await db.execute(select(FuncionarioDB).where(FuncionarioDB.id == id))
        funcionario = result.scalar_one_or_none()

        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Funcionário não encontrado",
            )
        # Verifica se está tentando atualizar para um CPF que já existe
        if funcionario_data.cpf and funcionario_data.cpf != funcionario.cpf:
            result_cpf = await db.execute(
                select(FuncionarioDB).where(FuncionarioDB.cpf == funcionario_data.cpf)
            )
            existing_funcionario = result_cpf.scalar_one_or_none()

            if existing_funcionario:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Já existe um funcionário com este CPF",
                )

        # Hash da senha se fornecida nova senha
        if funcionario_data.senha:
            funcionario_data.senha = get_password_hash(funcionario_data.senha)

        # se informado grupo, valida se é um grupo válido
        if funcionario_data.grupo:
            if funcionario_data.grupo not in [1, 2, 3]:
                raise HTTPException( 
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Grupo inválido. Apenas grupo 1 (Admin), 2 (Atendimento Balcão) ou 3 (Atendimento Caixa) são permitidos."
                )

        # armazena uma copia do objeto com os dados atuais, para salvar na auditoria
        # não pode manter referencia com funcionário, para que o auditoria possa comparar
        # por isso a cópia do __dict__
        dados_antigos_obj = funcionario.__dict__.copy()

        # Atualiza apenas os campos fornecidos
        update_data = funcionario_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(funcionario, field, value)

        await db.commit()
        await db.refresh(funcionario)

        # Depois de tudo executado e antes do return, registra a ação na auditoria
        await AuditoriaService.registrar_acao(
        db=db,
        funcionario_id=current_user.id,
        acao="UPDATE",
        recurso="FUNCIONARIO",
        recurso_id=funcionario.id,
        dados_antigos=dados_antigos_obj, # Objeto SQLAlchemy com dados antigos
        dados_novos=funcionario, # Objeto SQLAlchemy com dados novos
        request=request # Request completo para capturar IP e user agent
        )

        return funcionario
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar funcionário: {str(e)}",
        )


@router.delete(
    "/funcionario/{id}",
    status_code=status.HTTP_200_OK,
    tags=["Funcionário"],
    summary="Remover funcionário - protegida por autenticação e grupo 1",
)
@limiter.limit(get_rate_limit("critical"))

async def delete_funcionario(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):
    """Remove um funcionário - protegida por autenticação e grupo 1"""
    try:
        result = await db.execute(select(FuncionarioDB).where(FuncionarioDB.id == id))
        funcionario = result.scalar_one_or_none()

        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Funcionário não encontrado",
            )

        # Impede que admin se auto-exclua
        if current_user.id == id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível excluir seu próprio usuário"
            )

        await db.delete(funcionario)
        await db.commit()

        # Depois de tudo executado e antes do return, registra a ação na auditoria
        await AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="DELETE",
            recurso="FUNCIONARIO",
            recurso_id=funcionario.id,
            dados_antigos=funcionario,
            dados_novos=None,
            request=request
        )

        return {"message": "Funcionario deletado com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar funcionário: {str(e)}",
        )
