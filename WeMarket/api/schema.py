"""
Модуль содержит схемы для валидации данных в запросах и ответах.

Схемы валидации запросов используются в бою для валидации данных отправленных
клиентами.

Схемы валидации ответов *ResponseSchema используются только при тестировании,
чтобы убедиться что обработчики возвращают данные в корректном формате.
"""
# from datetime import date

from marshmallow import Schema, ValidationError, validates, validates_schema
from marshmallow.fields import DateTime, UUID, Dict, Float, Int, List, Nested, Str
from marshmallow.validate import Length, OneOf, Range
from WeMarket.db.schema import UnitType

DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%zZ'


class ShopUnit(Schema):
    id = UUID(required=True)
    name = Str(validate=Length(min=1, max=256), required=True)
    type = Str(validate=OneOf([type.value for type in UnitType]), required=True)
    parentId = UUID(allow_none=True, required=False)
    price = Int(validate=Range(min=0), strict=True, required=False)


class ImportSchema(Schema):
    items = Nested(ShopUnit, many=True, required=True,
                   validate=Length(max=10000))
    updateDate = DateTime(required=True, timezone=True)


class ErrorSchema(Schema):
    code = Str(required=True)
    message = Int(required=True)


class ErrorResponseSchema(Schema):
    error = Nested(ErrorSchema(), required=True)
