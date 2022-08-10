from typing import Generator

from aiohttp.web_response import Response
from aiohttp_apispec import docs, request_schema
from aiomisc import chunk_list

from WeMarket.api.schema import ImportSchema, ErrorSchema
from WeMarket.db.schema import products_table, relations_table
from WeMarket.utils.pg import MAX_QUERY_ARGS
from sqlalchemy import and_

from .base import BaseView


class ImportsView(BaseView):
    URL_PATH = '/imports'
    MAX_PRODUCTS_PER_INSERT = MAX_QUERY_ARGS // len(products_table.columns)
    MAX_RELATIONS_PER_INSERT = MAX_QUERY_ARGS // len(relations_table.columns)

    @classmethod
    def make_products_table_rows(cls, products, date) -> Generator:
        """
        Генерирует данные готовые для вставки в таблицу products.
        """
        for product in products:
            req = {'id': product['id'],
                   'name': product['name'],
                   'date': date,
                   'type': product['type'],
                   'parentId': product['parentId'],
                   }
            if 'price' in product:
                req['price'] = product['price']
            yield req

    @classmethod
    def make_relations_table_rows(cls, products) -> Generator:
        """
        Генерирует данные готовые для вставки в таблицу relations.
        """
        for prod in products:
            yield {
                'unit_id': prod['parentId'],
                'relative_id': prod['id'],
            }

    @classmethod
    async def update_product(cls, conn, id, data):
        prod_rel_id = await conn.fetchrow(products_table.select().where(products_table.c.id == id))
        prod_rel_id = prod_rel_id['parentId']
        if prod_rel_id != data['parentId']:
            query = relations_table.delete().where(
                and_(relations_table.c.unit_id == prod_rel_id,
                     relations_table.c.relative_id == id))
            await conn.execute(query)
            query = relations_table.insert().values({
                'unit_id': data['parentId'],
                'relative_id': data['id'],
            })
            await conn.execute(query)
        query = products_table.update().values(data).where(
            products_table.c.id == id
        )
        await conn.execute(query)

    @docs(summary='Добавить продукты и категории',
          responses={
              200: {"description": "Success operation"},
              400: {"schema": ErrorSchema,
                    "description": "Validation error"},
          }, )
    @request_schema(ImportSchema())
    async def post(self):
        async with self.pg.transaction() as conn:
            products = self.request['data']['items']
            date = self.request['data']['updateDate']
            products_to_ins = []
            for prod in products:
                if await conn.fetchrow(products_table.select().where(products_table.c.id == prod['id'])):
                    await self.update_product(conn, prod['id'], prod)
                else:
                    products_to_ins.append(prod)
            product_rows = self.make_products_table_rows(products_to_ins, date)
            relation_rows = self.make_relations_table_rows(products_to_ins)
            chunked_product_rows = chunk_list(product_rows,
                                              self.MAX_PRODUCTS_PER_INSERT)
            chunked_relation_rows = chunk_list(relation_rows,
                                               self.MAX_RELATIONS_PER_INSERT)
            query = products_table.insert()
            for chunk in chunked_product_rows:
                await conn.execute(query.values(list(chunk)))

            query = relations_table.insert()
            for chunk in chunked_relation_rows:
                await conn.execute(query.values(list(chunk)))
        return Response(status=200)