from typing import Generator

from aiohttp.web_response import Response
from aiohttp_apispec import docs

from WeMarket.api.schema import ErrorSchema
from WeMarket.db.schema import products_table, relations_table
from sqlalchemy import and_

from .base import BaseView


class DeleteView(BaseView):
    URL_PATH = r'/delete/{id}'

    @property
    def unit_id(self):
        return self.request.match_info.get('id')

    @docs(summary='Удаление продукта или категории',
          responses={
              200: {"description": "Success operation"},
              400: {"schema": ErrorSchema,
                    "description": "Validation error"},
              404: {"schema": ErrorSchema,
                    "description": "Item not found"},
          })
    async def delete(self):
        async with self.pg.transaction() as conn:
            unit = await conn.fetchrow(products_table.select().where(products_table.c.id == self.unit_id))
            if not unit:
                return Response(status=404)

            stack = [self.unit_id]
            while len(stack) != 0:
                _id = stack.pop()
                query = relations_table.select().where(
                    relations_table.c.unit_id == _id)
                res = await conn.fetch(query)
                for row in res:
                    stack.append(row['relative_id'])
                    query = relations_table.delete().where(
                        and_(relations_table.c.unit_id == _id,
                             relations_table.c.relative_id == row['relative_id']))
                    await conn.execute(query)
                    query = relations_table.delete().where(
                             relations_table.c.relative_id == _id)
                    await conn.execute(query)
                    query = products_table.delete().where(
                        products_table.c.id == _id)
                    await conn.execute(query)
                    query = products_table.delete().where(
                        products_table.c.id == row['relative_id'])
                    await conn.execute(query)


        return Response(status=200)
