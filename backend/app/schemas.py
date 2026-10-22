import re
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, field_validator
from web3 import Web3

Uint = Annotated[str, Field(pattern=r'^[1-9][0-9]{0,77}$')]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class CreateOrder(StrictModel):
    product_id: Uint
    buyer: str
    max_mud_amount: Uint
    ttl_seconds: int = Field(default=300, ge=30, le=900)

    @field_validator('product_id', 'max_mud_amount')
    @classmethod
    def uint256(cls, value):
        if int(value) >= 2**256:
            raise ValueError('uint256 overflow')
        return value

    @field_validator('buyer')
    @classmethod
    def valid_address(cls, value):
        if not Web3.is_address(value) or int(value, 16) == 0:
            raise ValueError('nonzero Ethereum address required')
        return Web3.to_checksum_address(value)


class VerifyProof(StrictModel):
    address: str
    index: int = Field(ge=0, lt=10000)
    allocation: Uint
    proof: list[str] = Field(max_length=14)

    @field_validator('allocation')
    @classmethod
    def uint256(cls, value):
        if int(value) >= 2**256:
            raise ValueError('uint256 overflow')
        return value

    @field_validator('address')
    @classmethod
    def valid_address(cls, value):
        return CreateOrder.valid_address(value)

    @field_validator('proof')
    @classmethod
    def valid_proof(cls, value):
        if any(not re.fullmatch(r'0x[0-9a-fA-F]{64}', p) for p in value):
            raise ValueError('bytes32 proof required')
        return value


def parse_amount(value: str):
    if not re.fullmatch(r'[1-9][0-9]{0,77}', value) or int(value) >= 2**256:
        raise ValueError('positive uint256 decimal string required')
    return int(value)
