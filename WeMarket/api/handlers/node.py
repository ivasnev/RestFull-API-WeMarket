from datetime import date, datetime, timedelta, timezone

from asyncpg.pgproto.pgproto import UUID

from aiohttp.web_response import Response
from aiohttp_apispec import docs, request_schema

from WeMarket.api.schema import ErrorSchema, SalesSchema
from WeMarket.db.schema import products_table
from sqlalchemy import and_
from .base import BaseView

import pytz
import json


class SalesView(BaseView):
    URL_PATH = r'/node/{id}/statistic'

    @property
    def unit_id(self):
        return self.request.match_info.get('id')

    @staticmethod
    def json_serial(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat(timespec='milliseconds')[:-6] + "Z"
        if isinstance(obj, UUID):
            return str(obj)
        raise TypeError("Type %s not serializable" % type(obj))

    @docs(summary='Получить информацию о скидках',
          parameters=[{
              'in': 'query',
              'name': 'dateStart',
              'schema': SalesSchema,
              'required': 'true'
          }, {
              'in': 'query',
              'name': 'dateEnd',
              'schema': SalesSchema,
              'required': 'true'
          }],
          responses={
              200: {"description": "Success operation"},
              400: {"schema": ErrorSchema,
                    "description": "Validation error"},
              404: {"schema": ErrorSchema,
                    "description": "Item not found"},
          })

    async def get(self):
        async with self.pg.transaction() as conn:
            tz = pytz.timezone("UTC")
            _date = tz.localize(datetime.fromisoformat(
                self.request.rel_url.query.get('date')[:-1]))
            date_after = _date - timedelta(1)
            date_before = _date
            query = products_table.select().where(
                and_(products_table.c.date >= date_after,
                     products_table.c.date <= date_before))
            res = await conn.fetch(query)
            items = [dict(item) for item in res]
            data = json.dumps({'items': items}, default=self.json_serial)
        return Response(status=200, body=data)
