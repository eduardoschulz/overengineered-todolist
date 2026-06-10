import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from modules.auth.interface.router import router as auth_router
from modules.auth.interface.users_router import users_router
from modules.todo.interface.router import router as todo_router
from modules.todo.interface.task_router import tasks_router
from shared.exceptions import AppError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("app")

app = FastAPI()


def _extract_user_id(request: Request) -> str | None:
    """Extrai o user_id do token JWT no header Authorization, se presente."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    try:
        from modules.auth.infrastructure.jwt_provider import PyJWTTokenProvider

        token = auth.removeprefix("Bearer ")
        payload = PyJWTTokenProvider().decode(token)
        return payload.get("sub")
    except Exception:
        return None


@app.middleware("http")
async def log_requests(request: Request, call_next):
    user_id = _extract_user_id(request)
    user_info = f"user={user_id}" if user_id else "user=anon"
    logger.info("%s %s (%s)", request.method, request.url.path, user_info)

    try:
        response = await call_next(request)
    except Exception:
        logger.error(
            "%s %s -> 500\n%s",
            request.method,
            request.url.path,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    if response.status_code >= 500:
        logger.error("%s %s -> %d", request.method, request.url.path, response.status_code)
    elif response.status_code >= 400:
        logger.warning("%s %s -> %d", request.method, request.url.path, response.status_code)
    else:
        logger.info("%s %s -> %d", request.method, request.url.path, response.status_code)

    return response


@app.get("/")
def root():
    return {"message": "Hello World!"}


@app.get("/health", status_code=200)
def health():
    return {"status": "ok"}


@app.exception_handler(AppError)
def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "AppError: %s (status=%d, path=%s)",
        str(exc),
        exc.status_code,
        request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc)},
    )


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(todo_router)
app.include_router(tasks_router)
