from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.exceptions import AppError

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Hello World!"}


@app.get("/health", status_code=200)
def health():
    return {"status": "ok"}


@app.exception_handler(AppError)
def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc)},
    )


# @app.get("/users/")
# def read_users(db: Session = Depends(get_db)):
#     return db.query(User).all()
