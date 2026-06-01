from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World!"}


@app.get("/health", status_code=200)
async def health():
    return {"status": "ok"}

# @app.get("/users/")
# def read_users(db: Session = Depends(get_db)):
#     return db.query(User).all()
