from ipaddress import ip_address

from pydantic import BaseModel, EmailStr, HttpUrl, field_validator
from sqlmodel import Field, SQLModel

# User Table

class UserBase(SQLModel):
     name: str = Field(index=True, max_length=100)
     email: EmailStr = Field(index=True, unique=True)

class UserRequest(UserBase):
     password: str = Field(min_length=8, max_length=120)


class UserTable(UserBase, table=True):
     id: int | None = Field(default=None, primary_key=True)
     hashed_password : str 

# Urls
class UrlAPI(SQLModel):
    long_url: HttpUrl = Field(max_length=2048)

    @field_validator("long_url")
    @classmethod
    def validate_url_host(cls, value: HttpUrl) -> HttpUrl:
        host = value.host

        if host is None:
            raise ValueError("URL must contain a hostname")

        normalized_host = host.lower()

        if (
            normalized_host == "localhost" or normalized_host.endswith((".local", ".internal"))
        ):
            raise ValueError("Local or internal hostnames are not allowed")

        # Pydantic may retain brackets around an IPv6 address.
        ip_host = normalized_host.strip("[]")

        try:
            address = ip_address(ip_host)
        except ValueError:
            # It is an ordinary hostname.
            return value

        if any(
            (
                address.is_private,
                address.is_loopback,
                address.is_link_local,
                address.is_reserved,
                address.is_multicast,
                address.is_unspecified,
            )
        ):
            raise ValueError("Private or non-public IP addresses are not allowed")

        return value

class UrlTable(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    long_url:str = Field(max_length=2048)
    code:str=Field(unique=True, index=True, max_length=7)
    owner_id: int = Field(foreign_key="usertable.id",  index=True)

class GetCode(SQLModel):
    code:str
    short_url:str


class GetAllLinks(SQLModel):
     long_url:str
     code: str


# Token
class Token(BaseModel):
     access_token:str
     token_type:str

class TokenData(BaseModel):
     email: str


    
