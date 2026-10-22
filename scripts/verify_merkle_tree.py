#!/usr/bin/env python3
"""Independent construction and per-claim proof verification; no generator imports."""
import hashlib
import json
import sys
from eth_abi import encode
from eth_utils import keccak, to_checksum_address


def verify(manifest):
    hashes = []
    canonical_rows = []
    for row in manifest['claims']:
        leaf = keccak(keccak(encode(['uint256', 'address', 'uint256'],
            [row['index'], row['address'], int(row['allocation'])])))
        assert '0x'+leaf.hex() == row['leaf']
        value = leaf
        for sibling in row['proof']:
            pair = sorted([value, bytes.fromhex(sibling[2:])])
            value = keccak(pair[0]+pair[1])
        assert '0x'+value.hex() == manifest['root'], 'invalid proof'
        hashes.append(leaf)
        canonical_rows.append({'index': row['index'], 'address': to_checksum_address(row['address']), 'allocation': row['allocation']})
    hashes.sort()
    while len(hashes) > 1:
        hashes = [hashes[i] if i+1 == len(hashes) else keccak(min(hashes[i], hashes[i+1])+max(hashes[i], hashes[i+1]))
                  for i in range(0, len(hashes), 2)]
    assert '0x'+hashes[0].hex() == manifest['root']
    canonical = json.dumps({'version': manifest['datasetVersion'], 'entries': sorted(canonical_rows, key=lambda r:r['index'])},
                           separators=(',', ':'), sort_keys=True).encode()
    assert hashlib.sha256(canonical).hexdigest() == manifest['datasetSha256']
    assert sum(int(r['allocation']) for r in manifest['claims']) == int(manifest['totalAllocation'])
    return True


if __name__ == '__main__':
    verify(json.load(open(sys.argv[1])))
    print('All leaves, proofs, total allocation, dataset hash and independently recomputed root verified')
