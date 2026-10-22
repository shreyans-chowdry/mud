import time
import uuid
from sqlalchemy import BigInteger, Boolean, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid():
    return str(uuid.uuid4())


def now():
    return int(time.time())


class Base(DeclarativeBase):
    pass


class Checkpoint(Base):
    __tablename__ = 'checkpoints'
    chain_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    block_number: Mapped[int] = mapped_column(BigInteger)
    block_hash: Mapped[str] = mapped_column(String(66))
    updated_at: Mapped[int] = mapped_column(BigInteger, default=now)


class Block(Base):
    __tablename__ = 'blocks'
    chain_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    number: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    hash: Mapped[str] = mapped_column(String(66))
    parent_hash: Mapped[str] = mapped_column(String(66))
    timestamp: Mapped[int] = mapped_column(BigInteger)


class Event(Base):
    __tablename__ = 'events'
    __table_args__ = (UniqueConstraint('chain_id', 'tx_hash', 'log_index', name='uq_chain_tx_log'),
                     Index('ix_events_chain_block', 'chain_id', 'block_number'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tx_hash: Mapped[str] = mapped_column(String(66))
    log_index: Mapped[int] = mapped_column(Integer)
    chain_id: Mapped[int] = mapped_column(BigInteger)
    block_number: Mapped[int] = mapped_column(BigInteger)
    block_hash: Mapped[str] = mapped_column(String(66))
    transaction_index: Mapped[int] = mapped_column(Integer)
    user_address: Mapped[str | None] = mapped_column(String(42))
    mud_amount: Mapped[str] = mapped_column(String(78), default='0')
    collateral_amount: Mapped[str] = mapped_column(String(78), default='0')
    event_type: Mapped[str] = mapped_column(String(64))
    timestamp: Mapped[int] = mapped_column(BigInteger)
    finality_status: Mapped[str] = mapped_column(String(16), default='OBSERVED')
    canonical: Mapped[bool] = mapped_column(Boolean, default=True)
    raw: Mapped[dict] = mapped_column(JSON)


class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    order_hash: Mapped[str] = mapped_column(String(66), unique=True)
    chain_id: Mapped[int] = mapped_column(BigInteger)
    verifying_contract: Mapped[str] = mapped_column(String(42))
    product_id: Mapped[str] = mapped_column(String(78))
    buyer: Mapped[str] = mapped_column(String(42))
    max_mud_amount: Mapped[str] = mapped_column(String(78))
    nonce: Mapped[str] = mapped_column(String(78))
    deadline: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32), default='CREATED')
    fulfillment_status: Mapped[str] = mapped_column(String(32), default='NOT_READY')
    settlement_tx: Mapped[str | None] = mapped_column(String(66))
    settlement_log: Mapped[int | None] = mapped_column(Integer)
    paid_amount: Mapped[str | None] = mapped_column(String(78))
    typed_data: Mapped[dict] = mapped_column(JSON)
    transition_sequence: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    created_at: Mapped[int] = mapped_column(BigInteger, default=now)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=now)


class OrderTransition(Base):
    __tablename__ = 'order_transitions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    order_id: Mapped[str] = mapped_column(String(36), index=True)
    previous: Mapped[str] = mapped_column(String(32))
    current: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(128))
    sequence: Mapped[int | None] = mapped_column(Integer)
    timestamp: Mapped[int] = mapped_column(BigInteger, default=now)


class Outbox(Base):
    __tablename__ = 'outbox'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    dedupe_key: Mapped[str] = mapped_column(String(200), unique=True)
    order_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default='PENDING')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt: Mapped[int] = mapped_column(BigInteger, default=now)
    lease_until: Mapped[int] = mapped_column(BigInteger, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)


class Delivery(Base):
    __tablename__ = 'deliveries'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    outbox_id: Mapped[str] = mapped_column(String(36), index=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    attempted_at: Mapped[int] = mapped_column(BigInteger, default=now)
    status_code: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)


class FulfillmentReceipt(Base):
    __tablename__ = 'fulfillment_receipts'
    idempotency_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    received_at: Mapped[int] = mapped_column(BigInteger, default=now)


class Entitlement(Base):
    __tablename__ = 'entitlements'
    order_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default='ACTIVE')
    source_key: Mapped[str] = mapped_column(String(200))
    tx_hash: Mapped[str | None] = mapped_column(String(66))
    block_hash: Mapped[str | None] = mapped_column(String(66))
    created_at: Mapped[int] = mapped_column(BigInteger, default=now)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=now)
