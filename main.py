from random import randint

from fastapi import FastAPI
from .schemas import CodeUrl

app=FastAPI()

links={12709: "https://www.google.com/", 12710: "https://www.youtube.com/"}

def code_generator():
    while True:
        new_code=randint(1,1000000)
        if new_code not in links:
            return new_code
        
@app.get("/health")
def get_health_check():
    return{
        "status":"ok"
    }

@app.post("/links")
def assign_code(url: CodeUrl):
    new_code=code_generator()
    links[new_code]=str(url.long_url)
    return new_code