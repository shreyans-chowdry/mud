#!/usr/bin/env python3
"""Versioned, double-hashed ABI leaves; sorted leaves/pairs; odd nodes promoted unchanged."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from eth_abi import encode
from eth_utils import is_address, keccak, to_checksum_address


def generate(dataset):
    if not isinstance(dataset.get('version'), str) or not dataset['version'].strip():
        raise ValueError('dataset version required')
    entries = dataset.get('entries', [])
    if not 1 <= len(entries) <= 10000:
        raise ValueError('1..10000 entries required')
    rows, indices, accounts = [], set(), set()
    for entry in entries:
        index, account, amount = entry.get('index'), entry.get('address'), entry.get('allocation')
        if type(index) is not int or not 0 <= index < 10000 or index in indices:
            raise ValueError('invalid or duplicate index')
        if not isinstance(account, str) or not is_address(account) or int(account, 16) == 0:
            raise ValueError('invalid address')
        if account.lower() in accounts:
            raise ValueError('ambiguous duplicate address')
        if not isinstance(amount, str) or not re.fullmatch(r'[1-9][0-9]*', amount) or int(amount) >= 2**256:
            raise ValueError('allocation must be positive uint256 decimal string')
        indices.add(index)
        accounts.add(account.lower())
        address = to_checksum_address(account)
        leaf = keccak(keccak(encode(['uint256', 'address', 'uint256'], [index, address, int(amount)])))
        rows.append({'index': index, 'address': address, 'allocation': amount, 'leaf': '0x'+leaf.hex()})
    rows.sort(key=lambda r: bytes.fromhex(r['leaf'][2:]))
    layers = [[bytes.fromhex(r['leaf'][2:]) for r in rows]]
    while len(layers[-1]) > 1:
        layer, nxt = layers[-1], []
        for i in range(0, len(layer), 2):
            nxt.append(keccak(b''.join(sorted(layer[i:i+2]))) if i+1 < len(layer) else layer[i])
        layers.append(nxt)
    for pos, row in enumerate(rows):
        proof, p = [], pos
        for layer in layers[:-1]:
            sibling = p ^ 1
            if sibling < len(layer):
                proof.append('0x'+layer[sibling].hex())
            p //= 2
        row['proof'] = proof
    canonical = json.dumps({'version': dataset['version'], 'entries': sorted(
        [{k: r[k] for k in ('index', 'address', 'allocation')} for r in rows], key=lambda r:r['index'])},
        separators=(',', ':'), sort_keys=True).encode()
    total = sum(int(r['allocation']) for r in rows)
    if total >= 2**256:
        raise ValueError('total allocation overflow')
    first = rows[0]
    return {'encoding': 'keccak256(keccak256(abi.encode(uint256,address,uint256))); sorted leaves and pairs; odd promoted',
            'datasetVersion': dataset['version'], 'datasetSha256': hashlib.sha256(canonical).hexdigest(),
            'root': '0x'+layers[-1][0].hex(), 'totalAllocation': str(total), 'claims': sorted(rows, key=lambda r:r['index']),
            'testVectors': {'valid': first, 'modifiedAmount': {**first, 'allocation': str(int(first['allocation'])+1)},
                            'invalidProof': {**first, 'proof': ['0x'+'00'*32]},
                            'duplicateClaim': {'index': first['index'], 'expected': 'revert after first successful claim'}}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = generate(json.loads(args.dataset.read_text()))
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(result['root'])
