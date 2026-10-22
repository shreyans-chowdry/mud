// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

/// @notice Discrete antiderivative; units and error bounds are in docs/ECONOMIC_MODEL.md.
library CurveMath {
    uint256 internal constant WAD = 1e18;
    function potential(uint256 supply, uint256 p0, uint256 k) internal pure returns (uint256) {
        uint256 root = Math.sqrt(supply * WAD);
        uint256 power = Math.mulDiv(supply, root, WAD);
        return Math.mulDiv(p0, supply, WAD) + Math.mulDiv(2 * k, power, 3 * WAD);
    }
    function spot(uint256 supply, uint256 p0, uint256 k) internal pure returns (uint256) {
        return p0 + Math.mulDiv(k, Math.sqrt(supply * WAD), WAD);
    }
    function target(uint256 supply, uint256 budget, uint256 cap, uint256 p0, uint256 k)
        internal pure returns (uint256)
    {
        uint256 base = potential(supply, p0, k);
        uint256 lo = supply;
        uint256 hi = cap;
        while (lo < hi) {
            uint256 mid = lo + (hi - lo + 1) / 2;
            if (potential(mid, p0, k) - base <= budget) lo = mid;
            else hi = mid - 1;
        }
        return lo - supply;
    }
}
