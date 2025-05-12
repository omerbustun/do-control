import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "DO-Control"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/do_control")
    
    # DigitalOcean
    DO_API_TOKEN: str = os.getenv("DO_API_TOKEN")
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_SECURITY_PROTOCOL: str = os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
    KAFKA_SASL_MECHANISM: str = os.getenv("KAFKA_SASL_MECHANISM", "PLAIN")
    KAFKA_SASL_USERNAME: str = os.getenv("KAFKA_SASL_USERNAME", "")
    KAFKA_SASL_PASSWORD: str = os.getenv("KAFKA_SASL_PASSWORD", "")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "development_secret_key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()