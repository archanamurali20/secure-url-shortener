from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import SQLModel, Session, create_engine, select
from schemas import GetCode, UrlTable, UrlAPI,PostURL
from contextlib import asynccontextmanager


sqlite_file_name = "database.db"
sqlite_url=f"sqlite:///{sqlite_file_name}"

connect_args={"check_same_thread":False}
engine=create_engine(sqlite_url, echo=True, connect_args=connect_args)

@asynccontextmanager
async def createdb_and_tables( app : FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

app=FastAPI(lifespan=createdb_and_tables)


def get_session():
    with Session(engine) as session:
        yield session

@app.get("/health")
def get_health_check():
    return{
        "status":"ok"
    }

@app.post("/links",response_model=GetCode)
def assign_code(long_url: UrlAPI, session: Session = Depends(get_session)):
    table_entry = UrlTable(long_url=str(long_url.long_url))
    session.add(table_entry)            
    session.commit()
    session.refresh(table_entry)
    return table_entry

@app.get("/links/{code}", response_model=PostURL, responses={404:{"description":"No Link exists for this code"}})   
def get_long_url(code: str, session:Session=Depends(get_session)):
    long_url=session.exec(select(UrlTable).where(UrlTable.code==code)).first()
    if long_url is None:
        raise HTTPException(status_code=404, detail= "Code Not Found")
    return long_url
