// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {IAggregator} from "./interfaces/IAggregator.sol";
contract MudPriceOracle {
    IAggregator public immutable feed;
    IAggregator public immutable sequencer;
    uint256 public immutable maxAge;
    uint256 public immutable minAnswer;
    uint256 public immutable maxAnswer;
    uint256 public constant GRACE_PERIOD = 1 hours;
    uint8 public immutable feedDecimals;
    error InvalidOracle();
    error InvalidPrice();
    error SequencerUnavailable();
    constructor(address feed_, address sequencer_, uint256 age_, uint256 min_, uint256 max_) {
        if (feed_.code.length == 0 || age_ == 0 || min_ == 0 || max_ <= min_) revert InvalidOracle();
        feed = IAggregator(feed_);
        if (sequencer_ != address(0) && sequencer_.code.length == 0) revert InvalidOracle();
        if (block.chainid != 31337 && sequencer_ == address(0)) revert InvalidOracle();
        sequencer = IAggregator(sequencer_);
        uint8 d = feed.decimals();
        if (d == 0 || d > 18) revert InvalidOracle();
        feedDecimals = d;
        maxAge = age_;
        minAnswer = min_;
        maxAnswer = max_;
    }
    function read() public view returns (uint256 price8, uint256 updatedAt) {
        if (address(sequencer) != address(0)) {
            (, int256 status, uint256 since, uint256 reported,) = sequencer.latestRoundData();
            if (status != 0 || since == 0 || since > block.timestamp || reported < since || reported > block.timestamp
                || block.timestamp - since <= GRACE_PERIOD) revert SequencerUnavailable();
        }
        (uint80 round, int256 answer,, uint256 timestamp, uint80 answeredRound) = feed.latestRoundData();
        if (round == 0 || answer <= 0 || timestamp == 0 || timestamp > block.timestamp
            || block.timestamp - timestamp > maxAge || answeredRound < round) revert InvalidPrice();
        price8 = Math.mulDiv(uint256(answer), 1e8, 10 ** feedDecimals);
        if (price8 < minAnswer || price8 > maxAnswer) revert InvalidPrice();
        updatedAt = timestamp;
    }
}
