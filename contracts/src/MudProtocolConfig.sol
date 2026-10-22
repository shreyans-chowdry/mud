// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";

contract MudProtocolConfig is Ownable2Step {
    uint256 public constant DELAY = 48 hours;
    uint16 public buyFeeBps;
    uint16 public exitFeeBps = 50;
    uint256 public maxTransaction;
    uint256 public immutable hardTransactionCap;
    bytes32 public pendingHash;
    uint256 public executableAt;
    event ConfigProposed(bytes32 indexed proposal, uint256 executableAt);
    event ConfigUpdated(uint16 buyFeeBps, uint16 exitFeeBps, uint256 maxTransaction);
    error InvalidConfig();
    constructor(address initialOwner, uint256 cap) Ownable(initialOwner) {
        if (cap == 0 || cap > 1e30) revert InvalidConfig();
        hardTransactionCap = cap;
        maxTransaction = cap;
    }
    function propose(uint16 buyFee, uint16 exitFee, uint256 limit) external onlyOwner {
        _validate(buyFee, exitFee, limit);
        pendingHash = keccak256(abi.encode(buyFee, exitFee, limit));
        executableAt = block.timestamp + DELAY;
        emit ConfigProposed(pendingHash, executableAt);
    }
    function execute(uint16 buyFee, uint16 exitFee, uint256 limit) external onlyOwner {
        _validate(buyFee, exitFee, limit);
        if (pendingHash != keccak256(abi.encode(buyFee, exitFee, limit)) || block.timestamp < executableAt)
            revert InvalidConfig();
        delete pendingHash;
        delete executableAt;
        buyFeeBps = buyFee;
        exitFeeBps = exitFee;
        maxTransaction = limit;
        emit ConfigUpdated(buyFee, exitFee, limit);
    }
    function _validate(uint16 buyFee, uint16 exitFee, uint256 limit) internal view {
        if (buyFee > 100 || exitFee > 500 || limit == 0 || limit > hardTransactionCap) revert InvalidConfig();
    }
    function renounceOwnership() public view override onlyOwner { revert InvalidConfig(); }
}
