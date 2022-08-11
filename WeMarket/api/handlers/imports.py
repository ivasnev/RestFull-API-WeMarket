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
            if 'price' in product and req['type'] == 'OFFER':
                req['price'] = product['price']
            else:
                req['price'] = None
            yield req

    @classmethod
    def make_relations_table_rows(cls, products) -> Generator:
        """
        Генерирует данные готовые для вставки в таблицу relations.
        """
        for prod in products:
            if prod['parentId']:
                yield {
                    'unit_id': prod['parentId'],
                    'relative_id': prod['id'],
                }

    @classmethod
    async def update_product(cls, conn, _id, data):
        prod_rel_id = await conn.fetchrow(products_table.select().where(products_table.c.id == _id))
        if prod_rel_id:
            prod_rel_id = prod_rel_id['parentId']
            if prod_rel_id != data['parentId']:
                query = relations_table.delete().where(
                    and_(relations_table.c.unit_id == prod_rel_id,
                         relations_table.c.relative_id == _id))
                await conn.execute(query)
                query = relations_table.insert().values({
                    'unit_id': data['parentId'],
                    'relative_id': data['id'],
                })
                await conn.execute(query)
        query = products_table.update().values(data).where(
            products_table.c.id == _id
        )
        await conn.execute(query)

    async def update_cost_for_category(self, unit_id, conn):
        unit = await conn.fetchrow(products_table.select().where(products_table.c.id == unit_id))
        if unit['type'] == 'OFFER':
            return unit['price'], 1
        children = await conn.fetch(relations_table.select().where(relations_table.c.unit_id == unit_id))
        unit = dict(unit)

        # res_cost = 0
        # for child in children:
        #     cost = await self.update_cost_for_category(child['relative_id'], conn)
        #     res_cost += cost
        # res_cost = res_cost // len(children)
        # unit['price'] = res_cost

        total_cost = 0
        count_offers = 0
        for child in children:
            cost, offers = await self.update_cost_for_category(child['relative_id'], conn)
            total_cost += cost
            count_offers += offers
        unit['price'] = total_cost // count_offers
        query = products_table.update().values(unit).where(
            products_table.c.id == unit_id
        )
        await conn.execute(query)

        return total_cost, count_offers

    @staticmethod
    async def get_roots_categories(conn, set_of_categories: set, date):
        result = set()
        seen_categories = set()
        for _cat in set_of_categories:
            seen_categories.add(_cat)
            _cur = _cat
            _next = await conn.fetchrow(relations_table.select().where(relations_table.c.relative_id == _cur))
            if not _next:
                result.add(_cur)
            while _next:
                _next = _next['unit_id']
                if _next in seen_categories:
                    break
                seen_categories.add(_next)
                _cur = _next
                _next = await conn.fetchrow(relations_table.select().where(relations_table.c.relative_id == _cur))
            else:
                result.add(_cur)
        for category_id in seen_categories:
            unit = await conn.fetchrow(products_table.select().where(products_table.c.id == category_id))
            if not unit:
                continue
            unit = dict(unit)
            unit['date'] = date
            query = products_table.update().values(unit).where(
                products_table.c.id == category_id
            )
            await conn.execute(query)
        return result

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
            categories_to_update = set()
            for prod in products:
                if await conn.fetchrow(products_table.select().where(products_table.c.id == prod['id'])):
                    parent_before = await conn.fetchrow(
                        relations_table.select().where(relations_table.c.relative_id == prod['id']))
                    await self.update_product(conn, prod['id'], prod)
                    parent_after = await conn.fetchrow(
                        relations_table.select().where(relations_table.c.relative_id == prod['id']))
                    if parent_before and parent_after and parent_before['unit_id'] == parent_after['unit_id']:
                        categories_to_update.add(parent_before['unit_id'])
                    else:
                        if parent_after:
                            categories_to_update.add(parent_after['unit_id'])
                        if parent_before:
                            categories_to_update.add(parent_before['unit_id'])
                else:
                    products_to_ins.append(prod)
                    if prod['parentId']:
                        categories_to_update.add(prod['parentId'])
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

            if len(categories_to_update) != 0:
                categories_to_update = await self.get_roots_categories(conn, categories_to_update, date)
                for cat_id in categories_to_update:
                    await self.update_cost_for_category(cat_id, conn)
        return Response(status=200)
