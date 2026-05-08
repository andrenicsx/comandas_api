# André Nícolas granemann Coelho

from infra import database
from sqlalchemy import Column, VARCHAR, Integer, FLOAT, LargeBinary

# ORM

class ProdutoDB(database.Base):
    __tablename__ = 'tb_produto'

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nome = Column(VARCHAR(100), nullable=False)
    descricao = Column(VARCHAR(255), nullable=False)
    foto = Column(LargeBinary, nullable=True)
    valor_unitario = Column(FLOAT, nullable=False)

    