from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # sets path to where pydantics will look for the .env file; in this case outside of app/
    model_config = SettingsConfigDict(env_file=".env")

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_TTL_MINUTES: int = 30


settings = Settings()
