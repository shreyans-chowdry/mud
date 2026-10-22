// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
interface IAggregator {
    function decimals() external view returns (uint8);
    function latestRoundData() external view returns (uint80, int256, uint256, uint256, uint80);
}
