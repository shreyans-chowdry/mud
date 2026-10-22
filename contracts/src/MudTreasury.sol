// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {SafeERC20, IERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IMudToken} from "./interfaces/IMudToken.sol";
contract MudTreasury is Ownable2Step, ReentrancyGuard {
    using SafeERC20 for IERC20;
    IERC20 public immutable collateral;
    uint256 public collected;
    uint256 public withdrawn;
    event FeesReceived(address indexed source, uint256 amount);
    event TreasuryWithdrawal(address indexed recipient, uint256 amount);
    error InvalidOperation();
    constructor(address owner_, address collateral_) Ownable(owner_) {
        if (collateral_.code.length == 0) revert InvalidOperation();
        collateral = IERC20(collateral_);
    }
    function collect(address amm) external onlyOwner nonReentrant {
        uint256 beforeBalance = collateral.balanceOf(address(this));
        uint256 amount = IMudToken(amm).collectFees();
        if (collateral.balanceOf(address(this)) != beforeBalance + amount) revert InvalidOperation();
        collected += amount;
        emit FeesReceived(amm, amount);
    }
    function withdraw(address to, uint256 amount) external onlyOwner nonReentrant {
        if (to == address(0) || amount == 0 || amount > collateral.balanceOf(address(this))) revert InvalidOperation();
        withdrawn += amount;
        collateral.safeTransfer(to, amount);
        emit TreasuryWithdrawal(to, amount);
    }
    function renounceOwnership() public view override onlyOwner { revert InvalidOperation(); }
}
