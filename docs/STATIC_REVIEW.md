# Static analysis review

Slither 0.11.3 analyzed 36 contracts using 100 detectors against the pinned Hardhat artifacts. The actual scan returned 12 findings: **0 high, 2 medium, 10 low**. The complete machine-readable report is in evidence/slither.json. A successful --fail-high exit does not mean no findings.

| Finding | Count | Disposition |
|---|---:|---|
| unused-return (medium) | 2 | Oracle round tuple fields are intentionally unused: the price round uses answer, updatedAt and answeredInRound checks; the sequencer check uses answer and startedAt. Review feed-specific semantics independently before deployment. No suppression applied. |
| timestamp (low) | 9 | Deadlines, claim expiry, parameter timelocks and oracle/sequencer freshness intentionally compare block.timestamp. Chain timestamp assumptions and configured margins remain part of the threat model. |
| reentrancy-benign (low) | 1 | Treasury.collect updates its collection counter after calling the AMM. Owner authorization and nonReentrant guard protect this path, and the actual balance delta is checked. Independent review is still required. |

These are engineering triage observations, not an independent audit or proof that each finding is harmless. Remaining dependency advisories are reported separately in VERIFICATION.md and still block release. No real-fund deployment is authorized by these checks.
