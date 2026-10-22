// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
interface IMudToken is IERC20 {
    function burn(uint256 amount) external;
    function getSpotPrice() external view returns (uint256);
    function collateralDecimals() external view returns (uint8);
    function collectFees() external returns (uint256);
}
