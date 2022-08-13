import pprint
from typing import Generator

from datetime import date, datetime

from asyncpg.pgproto.pgproto import UUID

from aiohttp_pydantic import PydanticView
from aiohttp.web_response import Response
from aiohttp_apispec import docs
from aiohttp.web import json_response

from WeMarket.api.schema import ErrorSchema, IdSchema
from WeMarket.db.schema import products_table, relations_table
import json

from .base import BaseView


class NodesView(BaseView, PydanticView):
    URL_PATH = r'/nodes/{id}'

    async def get_children(self, conn, _id, type):
        children_id = await conn.fetch(relations_table.select().where(relations_table.c.unit_id == _id))
        children = []
        for id in children_id:
            unit_c = await conn.fetchrow(products_table.select().where(products_table.c.id == id['relative_id']))
            unit_c = dict(unit_c)
            unit_c['children'] = await self.get_children(conn, unit_c['id'], unit_c['type'])
            if len(unit_c['children']) == 0:
                if type == 'CATEGORY':
                    unit_c['children'] = None
            children.append(unit_c)
        return children

    @staticmethod
    def json_serial(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat(timespec='milliseconds')[:-6] + "Z"
        if isinstance(obj, UUID):
            return str(obj)
        raise TypeError("Type %s not serializable" % type(obj))

    async def on_validation_error(self, exception, context):
        errors = {'msg': exception.errors()[0]['msg'],
                  'code': 400}

        return json_response(data=errors, status=400)

    @docs(summary='Получить информацию о продукте или категории',
          parameters=[{
              'in': 'path',
              'name': 'id',
              'schema': IdSchema,
              'required': 'true'
          }],
          responses={
              200: {"description": "Success operation"},
              400: {"schema": ErrorSchema,
                    "description": "Validation error"},
              404: {"schema": ErrorSchema,
                    "description": "Item not found"},
          })
    async def get(self, id: UUID, /):
        async with self.pg.transaction() as conn:
            unit = await conn.fetchrow(products_table.select().where(products_table.c.id == id))
            if not unit:
                return Response(status=404)
            unit = dict(unit)
            unit['children'] = await self.get_children(conn, id, unit['type'])
            if len(unit['children']) == 0:
                if unit['type'] == 'CATEGORY':
                    unit['children'] = None
            pprint.pprint(unit, indent=2)
            unit = json.dumps(unit, default=self.json_serial)
        return Response(status=200, body=unit)
