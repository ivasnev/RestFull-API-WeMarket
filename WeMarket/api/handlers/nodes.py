from typing import Generator

from datetime import date, datetime

from aiohttp.web_response import Response
from aiohttp_apispec import docs

from WeMarket.api.schema import ErrorSchema
from WeMarket.db.schema import products_table, relations_table
from sqlalchemy import and_
import json

from .base import BaseView


class NodesView(BaseView):
    URL_PATH = r'/nodes/{id}'

    @property
    def unit_id(self):
        return self.request.match_info.get('id')

    @docs(summary='Получить информацию о продукте или категории',
          responses={
              200: {"description": "Success operation"},
              400: {"schema": ErrorSchema,
                    "description": "Validation error"},
              404: {"schema": ErrorSchema,
                    "description": "Item not found"},
          })
    async def get_children(self, conn, _id):
        children_id = await conn.fetch(relations_table.select().where(relations_table.c.unit_id == _id))
        children = []
        for id in children_id:
            unit_c = await conn.fetchrow(products_table.select().where(products_table.c.id == id['relative_id']))
            unit_c = dict(unit_c)
            unit_c['children'] = await self.get_children(conn, unit_c['id'])
            if len(unit_c['children']) == 0:
                unit_c.pop('children')
            children.append(unit_c)
        return children

    def json_serial(self, obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError("Type %s not serializable" % type(obj))

    async def get(self):
        async with self.pg.transaction() as conn:
            unit = await conn.fetchrow(products_table.select().where(products_table.c.id == self.unit_id))
            if not unit:
                return Response(status=404)
            unit = dict(unit)
            unit['children'] = await self.get_children(conn, self.unit_id)
            if len(unit['children']) == 0:
                unit_c.pop('children')
            print(unit)
            unit = json.dumps(unit, default=self.json_serial)
        return Response(status=200, body=unit)
