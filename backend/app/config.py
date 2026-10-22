from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='MUD_', env_file=ROOT / '.env', extra='ignore')
    environment: Literal['local', 'testnet', 'production'] = 'local'
    chain_id: int = 31337
    rpc_http: str = 'http://127.0.0.1:8545'
    rpc_ws: str = 'ws://127.0.0.1:8545'
    database_url: str = 'postgresql+asyncpg://mud:mud@127.0.0.1:5432/mud'
    redis_url: str | None = None
    deployment_file: Path | None = None
    eligibility_file: Path | None = None
    start_block: int = Field(default=0, ge=0)
    batch_size: int = Field(default=100, ge=1, le=1000)
    confirmations: int = Field(default=1, ge=1)
    finality_depth: int = Field(default=3, ge=1)
    max_reorg_depth: int = Field(default=256, ge=1, le=10000)
    cors_origins: list[str] = ['http://localhost:3000', 'http://127.0.0.1:3000']
    requests_per_minute: int = Field(default=120, ge=1)
    cache_ttl: int = Field(default=5, ge=1, le=30)
    webhook_url: str | None = None
    webhook_secret: str | None = None
    webhook_allow_hosts: list[str] = ['127.0.0.1', 'localhost', 'fulfillment']
    webhook_max_attempts: int = Field(default=8, ge=1, le=20)
    run_workers: bool = False

    @field_validator('eligibility_file', mode='before')
    @classmethod
    def optional_eligibility(cls, value):
        if value in ('', None):
            return None
        path = Path(value)
        return path if path.is_absolute() else ROOT / path

    @model_validator(mode='after')
    def validate_environment(self):
        if self.chain_id not in (31337, 84532, 421614, 8453, 42161):
            raise ValueError('unsupported chain')
        if self.finality_depth < self.confirmations:
            raise ValueError('finality depth must cover confirmation depth')
        expected_environment = 'local' if self.chain_id == 31337 else ('testnet' if self.chain_id in (84532, 421614) else 'production')
        if self.environment != expected_environment:
            raise ValueError('environment does not match chain')
        if self.environment != 'local':
            if self.chain_id == 31337 or not self.redis_url or not self.database_url.startswith('postgresql+'):
                raise ValueError('remote environment requires PostgreSQL, Redis, remote chain')
            if urlparse(self.rpc_http).scheme != 'https' or urlparse(self.rpc_ws).scheme != 'wss':
                raise ValueError('remote RPC requires HTTPS and WSS')
            if self.eligibility_file and 'tests/fixtures' in self.eligibility_file.as_posix():
                raise ValueError('test eligibility fixtures are forbidden in remote environments')
            if self.confirmations < 5 or self.finality_depth < 64:
                raise ValueError('remote confirmation policy too weak')
        if self.webhook_secret and len(self.webhook_secret) < 32:
            raise ValueError('webhook secret must have at least 32 characters')
        return self

    @property
    def manifest_path(self):
        return self.deployment_file or ROOT / f'deployments/{self.chain_id}.json'


@lru_cache
def get_settings():
    return Settings()
