from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import SQLModel, Session, create_engine, select
from schemas import (
    GetCode, UrlTable, UrlAPI,PostURL,
    UserBase, UserRequest, UserTable,
    Token, TokenData

)
import jwt
from contextlib import asynccontextmanager
from pwdlib import PasswordHash
import string
import secrets
from config import user_access
from typing  import Annotated
from jwt.exceptions import InvalidTokenError


sqlite_file_name = "database.db"
sqlite_url=f"sqlite:///{sqlite_file_name}"

connect_args={"check_same_thread":False}
engine=create_engine(sqlite_url, echo=True, connect_args=connect_args)

password_hash = PasswordHash.recommended()
dummy_hash=password_hash.hash("dummypassword")

@asynccontextmanager
async def createdb_and_tables( app : FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

def code_generator():
        sequence = string.ascii_letters + string.digits
        code = ''.join(secrets.choice(sequence) for _ in range(7))
        return code

def get_password_hash(password):
     return password_hash.hash(password)

def verify_password(password, hashed_password):
    return password_hash.verify(password, hashed_password)


app=FastAPI(lifespan=createdb_and_tables)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_session():
    with Session(engine) as session:
        yield session

#To get the exisitng user from the database
def get_user(email: str, session : Session):
    user_present=session.exec(select(UserTable).where(UserTable.email==email)).first()
    return user_present

#To authenticate a user before assigning a token. This is basically the log in process
def authenticate_user(email:str, password:str, session: Session):
    check_user=get_user(email, session)
    if not check_user:
        verify_password(password,dummy_hash)
        return False
    if not verify_password(password, check_user.hashed_password):
        return False
    return check_user

# Create access token and verify it   
def create_access_token(data:dict, expires_delta:timedelta):
    to_encode=data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp":expire})
    encoded_jwt = jwt.encode(to_encode, user_access.SECRET_KEY, algorithm=user_access.ALGORITHM)
    return encoded_jwt

def get_current_user(token:Annotated[str,Depends(oauth2_scheme)], session: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, user_access.SECRET_KEY, algorithms= [user_access.ALGORITHM])
    except InvalidTokenError:
        raise credentials_exception
    email = payload.get("sub")
    if email is None:
        raise credentials_exception
    token_data = TokenData(username=email)
    user=get_user(token_data.username, session)
    if user is None:
        raise credentials_exception
    return user


@app.get("/health")
def get_health_check():
    return{
        "status":"ok"
    }

@app.post("/links",response_model=GetCode)
def assign_code(long_url: UrlAPI, session: Session = Depends(get_session), current_user: UserTable = Depends(get_current_user)):   
    while True:
        table_entry = UrlTable(long_url=str(long_url.long_url))
        table_entry.code = code_generator()
        try:
            session.add(table_entry)            
            session.commit()
            session.refresh(table_entry)
            return table_entry
        except IntegrityError:
            session.rollback()


@app.get("/links/{code}", response_model=PostURL, responses={404:{"description":"No Link exists for this code"}})   
def get_long_url(code: str, session:Session=Depends(get_session)):
    long_url=session.exec(select(UrlTable).where(UrlTable.code==code)).first()
    if long_url is None:
        raise HTTPException(status_code=404, detail= "Code Not Found")
    return long_url

#This is to add a new user to the database
@app.post("/create-user", response_model=UserBase)
def add_user(user_input :UserRequest, session : Session=Depends(get_session)):
    new_user = UserTable.model_validate(user_input, update={'hashed_password': get_password_hash(user_input.password)})
    try:
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail= 'This email ID already exists')
    return new_user

#This is to check credentials and generate token
@app.post("/auth/login")
def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session : Session=Depends(get_session))->Token:
    user = authenticate_user(form_data.username,form_data.password,session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires=timedelta(minutes=user_access.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token= create_access_token(data={"sub":user.email}, expires_delta=access_token_expires)

    return Token(access_token=access_token, token_type="bearer")





