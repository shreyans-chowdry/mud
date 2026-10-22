import json
from eth_abi import encode
from eth_utils import keccak
from ..config import ROOT


class AirdropService:
    def __init__(self, path):
        self.path = path

    def dataset(self):
        # Read on each request: file replacements cannot leave an old eligibility cache.
        import importlib.util
        spec = importlib.util.spec_from_file_location('mud_merkle_verifier', ROOT / 'scripts/verify_merkle_tree.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if self.path is None or not self.path.is_file():
            raise FileNotFoundError('eligibility dataset is not configured')
        data = json.loads(self.path.read_text())
        module.verify(data)
        return data

    def eligibility(self, address):
        data = self.dataset()
        claim = next((c for c in data['claims'] if c['address'].lower() == address.lower()), None)
        return {'eligible': claim is not None, 'claim': claim, 'root': data['root'],
                'dataset_version': data['datasetVersion'], 'dataset_hash': data['datasetSha256'],
                'meaning': 'dataset membership only; chain root, expiry and claimed bitmap are checked separately'}

    def verify(self, request):
        expected = self.eligibility(request.address)
        value = keccak(keccak(encode(['uint256', 'address', 'uint256'],
                                   [request.index, request.address, int(request.allocation)])))
        for sibling in request.proof:
            a, b = sorted([value, bytes.fromhex(sibling[2:])])
            value = keccak(a+b)
        claim = expected['claim']
        valid = bool(claim and claim['index'] == request.index and claim['allocation'] == request.allocation
                     and '0x'+value.hex() == expected['root'])
        return {'valid': valid, 'eligible': valid, 'root': expected['root'], 'dataset_version': expected['dataset_version']}
