from sqlalchemy import BigInteger
from sqlalchemy.orm import DeclarativeBase

ID_TYPE = BigInteger()


class Base(DeclarativeBase):
    pass
