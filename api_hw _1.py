import os
import requests
from dotenv import load_dotenv
from functools import wraps
from typing import Callable
import logging
import argparse

__all__ = ['FoursquareParser']

LATITUDE_MIN = -90  # Широта минимум
LATITUDE_MAX = 90  # Широта максимум
LONGITUDE_MIN = -180  # Долгота минимум
LONGITUDE_MAX = 180  # Долгота максимум
RADIUS_MIN = 50  # Радиус минимум (метры)
RADIUS_MAX = 100_000  # Радиус максимум (метры)
LATITUDE_DEF = 55.680351  # Значение по умолчанию при создании экземпляра класса
LONGITUDE_DEF = 37.676439  # Значение по умолчанию при создании экземпляра класса
RADIUS_DEF = 5_000  # Значение по умолчанию при создании экземпляра класса
QUERY_DEF = 'баня'  # Значение по умолчанию при создании экземпляра класса

# Настраиваем логирование
logging.basicConfig(format='%(levelname)-8s - %(asctime)s. %(message)s',
                    filename='log_info.log',
                    filemode='a',
                    encoding='utf-8',
                    level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S')

logger_val = logging.getLogger(__name__)


class UsException(BaseException):
    pass


class ValueException(UsException):
    def __init__(self, self_out, value):
        self.min_value = self_out.min_value
        self.max_value = self_out.max_value
        self.param_name = self_out.param_name[1:]
        self.value = value

    def __str__(self):
        if self.value is not None:
            return (f"Для переменной '{self.param_name}' не соблюдается условие:"
                    f" {self.min_value} <= {self.value} <= {self.max_value}")
        else:
            return f"Не задано значение переменной '{self.param_name}' = {self.value}"


def log_file(logger: logging.Logger):
    def info_func(func: Callable):
        @wraps(func)
        def write_log(*args, **kwargs):
            try:
                result_value = func(*args, **kwargs)
                if func.__name__ == 'get_info':
                    logger.info(result_value)
                return result_value
            except ValueException as e:
                mes = f'Функция "{func.__name__}().", {e}'
                logger.error(mes)

        return write_log

    return info_func


class Value:
    def __init__(self, min_value: float = None, max_value: float = None):
        self.min_value = min_value
        self.max_value = max_value

    def __set_name__(self, owner, name):
        self.param_name = '_' + name

    def __get__(self, instance, owner):
        return getattr(instance, self.param_name)

    @log_file(logger_val)
    def __set__(self, instance, value):
        self.validate(self, value)
        setattr(instance, self.param_name, value)

    @staticmethod
    def validate(self, value):
        if ((self.min_value is not None and self.max_value is not None) and
                (isinstance(value, float) or isinstance(value, int))):
            if not (self.min_value <= value <= self.max_value):
                raise ValueException(self, value)
        else:
            if value is None:
                raise ValueException(self, value)


class FoursquareParser:
    _api_key = Value()  # Изменено на одно подчеркивание
    latitude = Value(LATITUDE_MIN, LATITUDE_MAX)
    longitude = Value(LONGITUDE_MIN, LONGITUDE_MAX)
    radius = Value(RADIUS_MIN, RADIUS_MAX)
    query = Value()

    def __init__(self, api_key: str = ''):
        self._api_key = api_key  # Изменено на одно подчеркивание
        self.latitude = LATITUDE_DEF
        self.longitude = LONGITUDE_DEF
        self.radius = RADIUS_DEF
        self.query = QUERY_DEF

    def __str__(self):
        return (f'Центр окружности поиска (широта, долгота): {self.latitude}, {self.longitude}\n'
                f'                 Радиус окружности поиска: {self.radius:_}\n'
                f'                                   Запрос: "{self.query}"')

    def __repr__(self):
        return f"FoursquareParser(api_key={self._api_key})"  # Изменено на одно подчеркивание

    @log_file(logger_val)
    def get_info(self, query=None, latitude=None, longitude=None, radius=None):
        if query is not None:
            self.query = query
        if latitude is not None:
            self.latitude = latitude
        if longitude is not None:
            self.longitude = longitude
        if radius is not None:
            self.radius = radius

        url = 'https://api.foursquare.com/v3/places/search'
        params = {
            'll': f'{self.latitude},{self.longitude}',
            'radius': self.radius,
            'query': self.query,
            'fields': 'name,location,rating',
        }
        headers = {
            'Authorization': self._api_key,  # Изменено на одно подчеркивание
            'accept': 'application/json',
        }

        response = requests.get(url=url, params=params, headers=headers)
        j_data = response.json()

        res = f'Широта: {self.latitude}, Долгота: {self.longitude}, Радиус {self.radius:_} м., Запрос: "{self.query}" \n'
        for item in j_data.get('results', []):
            name = item.get("name")
            country = item.get("location", {}).get("country")
            address = item.get("location", {}).get("formatted_address")
            rating = item.get("rating")

            list_str = [f"Название: {name}", f"Страна:   {country}", f"Адрес:    {address}", f"Рейтинг:  {rating}"]

            longest = len(max(list_str, key=len))
            list_str.append(f'{"-" * longest}\n')

            res += '\n'.join(list_str)

        return res


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Функция выводит информацию по API запросу c сервиса Foursquare.')
    parser.add_argument('-query', metavar='query', type=str,
                        help='что будем искать (кофейня, магазин и т.д.)', default=None)
    parser.add_argument('-latitude', metavar='latitude', type=float,
                        help='центр круга поиска (широта)', default=None)
    parser.add_argument('-longitude', metavar='longitude', type=float,
                        help='центр круга поиска (долгота)', default=None)
    parser.add_argument('-radius', metavar='radius', type=int,
                        help='радиус круга поиска', default=None)
    args = parser.parse_args()

    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    foursquare_api_key = os.getenv('API_KEY')
    parser_obj = FoursquareParser(api_key=foursquare_api_key)
    print(parser_obj.get_info(query=args.query, latitude=args.latitude, longitude=args.longitude, radius=args.radius))
