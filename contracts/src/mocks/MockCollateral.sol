// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
/// @notice Unrestricted faucet ONLY for chain 31337; deployment reverts elsewhere.
contract MockCollateral is ERC20 {
    uint16 public taxBps;
    bool public failTransfers;
    address public callbackTarget;
    bytes public callbackData;
    bool public callbackSucceeded;
    uint8 private immutable precision;
    constructor(uint8 d) ERC20("LOCAL Mock Collateral", "mUSD") { require(block.chainid == 31337); precision = d; }
    function decimals() public view override returns (uint8) { return precision; }
    function mint(address to, uint256 amount) external { _mint(to, amount); }
    function confiscate(address from, uint256 amount) external { _burn(from, amount); }
    function setTax(uint16 bps) external { require(bps <= 10000); taxBps = bps; }
    function setFail(bool fail) external { failTransfers = fail; }
    function setCallback(address target, bytes calldata data) external { callbackTarget = target; callbackData = data; }
    function _update(address from, address to, uint256 amount) internal override {
        if (from != address(0) && to != address(0)) {
            require(!failTransfers, "mock transfer failure");
            uint256 tax = amount * taxBps / 10000;
            super._update(from, to, amount - tax);
            if (tax > 0) super._update(from, address(0), tax);
            if (callbackTarget != address(0)) {
                address target = callbackTarget;
                callbackTarget = address(0);
                (callbackSucceeded,) = target.call(callbackData);
            }
        } else super._update(from, to, amount);
    }
}
