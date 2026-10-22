// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
contract MockFeed {
    uint8 public immutable decimals;
    int256 public answer;
    uint256 public startedAt;
    uint256 public updatedAt;
    uint80 public roundId = 1;
    uint80 public answeredInRound = 1;
    constructor(uint8 d, int256 initial) {
        require(block.chainid == 31337);
        decimals = d;
        answer = initial;
        startedAt = block.timestamp;
        updatedAt = block.timestamp;
    }
    function set(int256 value, uint256 started, uint256 updated, uint80 round, uint80 answered) external {
        answer = value; startedAt = started; updatedAt = updated; roundId = round; answeredInRound = answered;
    }
    function latestRoundData() external view returns (uint80, int256, uint256, uint256, uint80) {
        return (roundId, answer, startedAt, updatedAt, answeredInRound);
    }
}
