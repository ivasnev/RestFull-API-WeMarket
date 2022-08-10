from sqlalchemy import (
    Column, Integer,
    MetaData, String, Table,
    Enum as PgEnum,DateTime,
    ForeignKey, ForeignKeyConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum, unique


@unique
class UnitType(Enum):
    offer = "OFFER"
    category = "CATEGORY"

convention = {
    'all_column_names': lambda constraint, table: '_'.join([
        column.name for column in constraint.columns.values()
    ]),
    'ix': 'ix__%(table_name)s__%(all_column_names)s',
    'uq': 'uq__%(table_name)s__%(all_column_names)s',
    'ck': 'ck__%(table_name)s__%(constraint_name)s',
    'fk': 'fk__%(table_name)s__%(all_column_names)s__%(referred_table_name)s',
    'pk': 'pk__%(table_name)s'
}

metadata = MetaData(naming_convention=convention)

products_table = Table(
    'items',
    metadata,
    Column('id', UUID, primary_key=True),
    Column('name', String, nullable=False),
    Column('type', PgEnum(UnitType, name='type'), nullable=False),
    Column('parentId', String, nullable=True),
    Column('price', Integer, nullable=True),
    Column('date', DateTime(timezone=True), nullable=True),

)

relations_table = Table(
    'relations',
    metadata,
    Column('unit_id', String, primary_key=True),
    Column('relative_id', String, primary_key=True),
)
