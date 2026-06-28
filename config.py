from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str = "dev-secret-key"
    allowed_origins: str = "http://localhost:8081"
    groq_api_key: str = ""

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
