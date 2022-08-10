from enum import EnumMeta
from http import HTTPStatus
from random import choice, randint, randrange, shuffle
from typing import Any, Dict, Iterable, List, Mapping, Optional, Union

import faker
from aiohttp.test_utils import TestClient
from aiohttp.typedefs import StrOrURL
from aiohttp.web_urldispatcher import DynamicResource

from WeMarket.api.handlers import (
    ImportsView,
)
from WeMarket.api.schema import (
    DATE_FORMAT, ProductsResponseSchema,
    ImportResponseSchema, PatchProductResponseSchema,
)
from WeMarket.utils.pg import MAX_INTEGER

fake = faker.Faker('ru_RU')


def url_for(path: str, **kwargs) -> str:
    """
    Генерирует URL для динамического aiohttp маршрута с параметрами.
    """
    kwargs = {
        key: str(value)  # Все значения должны быть str (для DynamicResource)
        for key, value in kwargs.items()
    }
    return str(DynamicResource(path).url_for(**kwargs))


def generate_product(
        id: Optional[int] = None,
        name: Optional[str] = None,
        date: Optional[str] = None,
        type: Optional[str] = None,
        price: Optional[str] = None,
        parentId: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Создает и возвращает продукт, автоматически генерируя данные для не
    указанных полей.
    """
    if id is None:
        id = randint(0, MAX_INTEGER)

    if type is None:
        type = randint(0, MAX_INTEGER)

    if price is None:
        price = randint(0, MAX_INTEGER)

    if parentId is None:
        parentId = randint(0, MAX_INTEGER)

    if name is None:
        name = fake.name_male()

    if date is None:
        date = fake.date_of_birth(
            minimum_age=0, maximum_age=80
        ).strftime(DATE_FORMAT)

    return {
        'id': id,
        'name': name,
        'date': date,
        'type': type,
        'parentId': parentId,
        'price': price,
    }


def generate_products(
        products_num: int,
        start_product_id: int = 0,
        **product_kwargs
) -> List[Dict[str, Any]]:
    """
    Генерирует список продуктов.

    :param products_num: Количество продуктов
    :param start_product_id: С какого product_id начинать
    :param product_kwargs: Аргументы для функции generate_product
    """
    max_product_id = start_product_id + products_num - 1
    products = {}
    for product_id in range(start_product_id, max_product_id + 1):
        products[product_id] = generate_product(id=product_id,
                                                **product_kwargs)
    return list(products.values())
