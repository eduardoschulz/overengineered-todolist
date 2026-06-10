from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from modules.auth.interface.router import router as auth_router
from modules.auth.interface.users_router import users_router
from modules.todo.interface.router import router as todo_router
from modules.todo.interface.task_router import tasks_router
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


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(todo_router)
app.include_router(tasks_router)


# @app.get("/users/")
# def read_users(db: Session = Depends(get_db)):
#     return db.query(User).all()
