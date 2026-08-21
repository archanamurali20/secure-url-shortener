from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlmodel import SQLModel, Session, create_engine, select
from schemas import (
    GetCode, UrlTable, UrlAPI,
    UserBase, UserRequest, UserTable,
    Token, TokenData, GetAllLinks

)
import jwt
from contextlib import asynccontextmanager
from pwdlib import PasswordHash
import string
import secrets
from config import settings
from typing  import Annotated
from jwt.exceptions import InvalidTokenError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

engine=create_engine(settings.DATABASE_URL, echo=True)

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

limiter = Limiter(key_func=get_remote_address)
app=FastAPI(lifespan=createdb_and_tables)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_current_user(token:Annotated[str,Depends(oauth2_scheme)], session: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms= [settings.ALGORITHM])
    except InvalidTokenError:
        raise credentials_exception
    email = payload.get("sub")
    if email is None:
        raise credentials_exception
    token_data = TokenData(email=email)
    user=get_user(token_data.email, session)
    if user is None:
        raise credentials_exception
    return user


@app.get("/health")
def get_health_check():
    return{
        "status":"ok"
    }

@app.post("/links",response_model=GetCode)
@limiter.limit("10/minute")
def assign_code(request :Request, long_url: UrlAPI, session: Session = Depends(get_session), current_user: UserTable = Depends(get_current_user)):   
    for _ in range(5):
        table_entry = UrlTable(long_url=str(long_url.long_url), code=code_generator(), owner_id= current_user.id)        
        try:
            session.add(table_entry)            
            session.commit()
            session.refresh(table_entry)
            return GetCode(code=table_entry.code,short_url=settings.BASE_URL+'/' +table_entry.code)
        except IntegrityError:
            session.rollback()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


@app.get("/links/{code}", response_class=RedirectResponse, responses={404:{"description":"No Link exists for this code"}},status_code=status.HTTP_302_FOUND )  
@limiter.limit("50/minute") 
def get_long_url(request :Request, code: str, session:Session=Depends(get_session)):
    url_row=session.exec(select(UrlTable).where(UrlTable.code==code)).first()
    if url_row is None:
        raise HTTPException(status_code=404, detail= "Code Not Found")
    return RedirectResponse(url=str(url_row.long_url), status_code=status.HTTP_302_FOUND)

#To add a new user to the database
@app.post("/auth/register", response_model=UserBase)
@limiter.limit("5/hour")
def add_user(request: Request, user_input :UserRequest, session : Session=Depends(get_session)):
    new_user = UserTable.model_validate(user_input, update={'hashed_password': get_password_hash(user_input.password)})
    try:
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail= 'This email ID already exists')
    return new_user

#To check credentials and generate token
@app.post("/auth/login")
@limiter.limit("5/minute")
def login_for_access_token(request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session : Session=Depends(get_session))->Token:
    user = authenticate_user(form_data.username,form_data.password,session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token= create_access_token(data={"sub":user.email}, expires_delta=access_token_expires)

    return Token(access_token=access_token, token_type="bearer")

@app.delete("/links/{code}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
def delete_links(request : Request, code : str, session: Session=Depends(get_session), current_user : UserTable = Depends(get_current_user)):
    code_in_db = session.exec(select(UrlTable).where(UrlTable.code==code)).first()
    if code_in_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code not found",
            )
    if(code_in_db.owner_id!=current_user.id):
        
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail = "Not authorized to perform this action",
            )
    session.delete(code_in_db)
    session.commit()

@app.get("/links", response_model=list[GetAllLinks])
@limiter.limit("50/minute") 
def get_all_links_for_current_user(request: Request, current_user: UserTable = Depends(get_current_user), session : Session = Depends(get_session)):
    all_links = session.exec(select(UrlTable).where(UrlTable.owner_id==current_user.id)).all()
    return all_links
    





