from pydantic import BaseModel, HttpUrl


class CodeUrl(BaseModel):
    long_url: HttpUrl
