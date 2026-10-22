"""Local-only destructive RPC snapshot test; uses an isolated projection DB."""
import os
import pytest
from sqlalchemy import select
from web3 import Web3
from app.blockchain import Chain
from app.config import Settings
from app.models import Event
from app.workers.indexer import Indexer


@pytest.mark.asyncio
@pytest.mark.skipif(os.environ.get('MUD_LIVE_TEST') != '1', reason='requires local snapshot-capable EVM')
async def test_real_chain_snapshot_reorganization_reconciles(db):
    chain = Chain(Settings(chain_id=31337))
    snapshot = None
    try:
        assert await chain.w3.eth.chain_id == 31337
        await chain.validate()
        buyer = Web3.to_checksum_address('0x70997970C51812dc3A010C7d01b50e0d17dc79C8')
        token = chain.contract('token')
        collateral = chain.w3.eth.contract(address=chain.manifest['contracts']['collateral'], abi=[{
            'type': 'function', 'name': 'approve', 'inputs': [{'name': 'spender', 'type': 'address'},
            {'name': 'amount', 'type': 'uint256'}], 'outputs': [{'type': 'bool'}], 'stateMutability': 'nonpayable'}])
        await collateral.functions.approve(token.address, 10000).transact({'from': buyer})
        worker = Indexer(chain, db, chain.settings)
        await worker.catch_up()
        snapshot = (await chain.w3.provider.make_request('evm_snapshot', []))['result']
        timestamp = (await chain.block('latest'))['timestamp']
        tx_hash = await token.functions.buyTokens(10000, 0, timestamp+300).transact({'from': buyer})
        await chain.w3.eth.wait_for_transaction_receipt(tx_hash)
        await worker.catch_up()
        tx = Web3.to_hex(tx_hash)
        async with db() as session:
            rows = (await session.scalars(select(Event).where(Event.tx_hash == tx))).all()
            assert rows and all(e.canonical for e in rows)
        assert (await chain.w3.provider.make_request('evm_revert', [snapshot]))['result']
        snapshot = None
        await chain.w3.provider.make_request('evm_mine', [])
        await worker.catch_up()
        async with db() as session:
            rows = (await session.scalars(select(Event).where(Event.tx_hash == tx))).all()
            assert rows and all(not e.canonical and e.finality_status == 'ORPHANED' for e in rows)
    finally:
        if snapshot:
            await chain.w3.provider.make_request('evm_revert', [snapshot])
        await chain.close()
