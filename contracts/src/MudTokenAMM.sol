// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Burnable} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import {IERC20Metadata} from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import {SafeERC20, IERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {CurveMath} from "./libraries/CurveMath.sol";
import {MudProtocolConfig} from "./MudProtocolConfig.sol";

contract MudTokenAMM is ERC20, ERC20Burnable, Ownable2Step, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;
    IERC20 public immutable collateral;
    uint8 public immutable collateralDecimals;
    MudProtocolConfig public immutable config;
    address public immutable treasury;
    address public immutable guardian;
    uint256 public immutable basePrice;
    uint256 public immutable slope;
    uint256 public immutable maxSupply;
    uint256 public accruedFees;
    uint256 public totalFeesCollected;
    event TokensPurchased(address indexed buyer, uint256 collateralIn, uint256 mudOut, uint256 fee, uint256 supply);
    event TokensRedeemed(address indexed seller, uint256 mudIn, uint256 collateralOut, uint256 fee, uint256 supply);
    event FeesCollected(address indexed treasury, uint256 amount);
    error InvalidParameters();
    error InvalidTrade();
    error Expired();
    error Slippage();
    error UnsupportedCollateral();
    error Insolvent();
    error Unauthorized();
    constructor(string memory name_, string memory symbol_, address collateral_, address config_,
        address treasury_, address owner_, address guardian_, uint256 p0_, uint256 k_, uint256 cap_)
        ERC20(name_, symbol_) Ownable(owner_)
    {
        if (collateral_.code.length == 0 || config_.code.length == 0 || treasury_ == address(0) || guardian_ == address(0)
            || p0_ == 0 || p0_ > 1e18 || k_ > 1e18 || cap_ == 0 || cap_ > 1e27 || k_ * cap_ > 1e33)
            revert InvalidParameters();
        uint8 d = IERC20Metadata(collateral_).decimals();
        if (d < 6 || d > 18) revert InvalidParameters();
        collateral = IERC20(collateral_);
        collateralDecimals = d;
        config = MudProtocolConfig(config_);
        treasury = treasury_;
        guardian = guardian_;
        basePrice = p0_;
        slope = k_;
        maxSupply = cap_;
    }
    function curvePotential(uint256 supply) public view returns (uint256) {
        if (supply > maxSupply) revert InvalidParameters();
        return CurveMath.potential(supply, basePrice, slope);
    }
    function getSpotPrice() public view returns (uint256) { return CurveMath.spot(totalSupply(), basePrice, slope); }
    function getCirculatingSupply() external view returns (uint256) { return totalSupply(); }
    function curveAccountedSupply() external view returns (uint256) { return totalSupply(); }
    function getReserveBalance() public view returns (uint256) { return collateral.balanceOf(address(this)); }
    function grossRedemptionLiability() public view returns (uint256) { return curvePotential(totalSupply()); }
    function netRedemptionLiability() external view returns (uint256) {
        uint256 gross = grossRedemptionLiability();
        return gross - Math.mulDiv(gross, config.exitFeeBps(), 10000);
    }
    function reserveHealthy() public view returns (bool) {
        return getReserveBalance() >= grossRedemptionLiability() + accruedFees;
    }
    function quoteBuy(uint256 collateralAmount) public view returns (uint256 mudOut, uint256 fee, uint256 curveCost) {
        if (collateralAmount == 0 || collateralAmount > config.maxTransaction() || totalSupply() == maxSupply)
            revert InvalidTrade();
        fee = Math.mulDiv(collateralAmount, config.buyFeeBps(), 10000);
        if (collateralAmount - fee > curvePotential(maxSupply) - grossRedemptionLiability()) revert InvalidTrade();
        mudOut = CurveMath.target(totalSupply(), collateralAmount - fee, maxSupply, basePrice, slope);
        if (mudOut == 0) revert InvalidTrade();
        curveCost = curvePotential(totalSupply() + mudOut) - grossRedemptionLiability();
    }
    function calculateMintTarget(uint256 collateralAmount) external view returns (uint256) {
        (uint256 output,,) = quoteBuy(collateralAmount);
        return output;
    }
    function buyTokens(uint256 collateralAmount, uint256 minMudOut, uint256 deadline)
        external nonReentrant whenNotPaused returns (uint256 mudOut)
    {
        if (block.timestamp > deadline) revert Expired();
        if (!reserveHealthy()) revert Insolvent();
        uint256 fee;
        (mudOut, fee,) = quoteBuy(collateralAmount);
        if (mudOut < minMudOut) revert Slippage();
        uint256 beforeReserve = getReserveBalance();
        uint256 beforeSender = collateral.balanceOf(msg.sender);
        accruedFees += fee;
        _mint(msg.sender, mudOut);
        collateral.safeTransferFrom(msg.sender, address(this), collateralAmount);
        if (getReserveBalance() != beforeReserve + collateralAmount || collateral.balanceOf(msg.sender) + collateralAmount != beforeSender)
            revert UnsupportedCollateral();
        if (!reserveHealthy()) revert Insolvent();
        emit TokensPurchased(msg.sender, collateralAmount, mudOut, fee, totalSupply());
    }
    function quoteSell(uint256 mudAmount) public view returns (uint256 collateralOut, uint256 fee, uint256 gross) {
        if (mudAmount == 0 || mudAmount > totalSupply()) revert InvalidTrade();
        gross = grossRedemptionLiability() - curvePotential(totalSupply() - mudAmount);
        if (gross == 0 || gross > config.maxTransaction()) revert InvalidTrade();
        fee = Math.mulDiv(gross, config.exitFeeBps(), 10000);
        collateralOut = gross - fee;
    }
    function calculateBurnRefund(uint256 amount) external view returns (uint256) {
        (uint256 output,,) = quoteSell(amount);
        return output;
    }
    function sellTokens(uint256 amount, uint256 minCollateralOut, uint256 deadline)
        external nonReentrant whenNotPaused returns (uint256 collateralOut)
    {
        if (block.timestamp > deadline) revert Expired();
        if (!reserveHealthy()) revert Insolvent();
        uint256 fee;
        (collateralOut, fee,) = quoteSell(amount);
        if (collateralOut < minCollateralOut) revert Slippage();
        _burn(msg.sender, amount);
        accruedFees += fee;
        _transferCollateral(msg.sender, collateralOut);
        if (!reserveHealthy()) revert Insolvent();
        emit TokensRedeemed(msg.sender, amount, collateralOut, fee, totalSupply());
    }
    function collectFees() external nonReentrant returns (uint256 amount) {
        if (msg.sender != treasury) revert Unauthorized();
        if (!reserveHealthy()) revert Insolvent();
        amount = accruedFees;
        accruedFees = 0;
        totalFeesCollected += amount;
        if (amount != 0) _transferCollateral(treasury, amount);
        if (!reserveHealthy()) revert Insolvent();
        emit FeesCollected(treasury, amount);
    }
    function _transferCollateral(address to, uint256 amount) internal {
        uint256 reserve = getReserveBalance();
        uint256 recipient = collateral.balanceOf(to);
        if (reserve < amount) revert Insolvent();
        collateral.safeTransfer(to, amount);
        if (getReserveBalance() + amount != reserve || collateral.balanceOf(to) != recipient + amount)
            revert UnsupportedCollateral();
    }
    function pause() external {
        if (msg.sender != guardian && msg.sender != owner()) revert Unauthorized();
        _pause();
    }
    function unpause() external onlyOwner { _unpause(); }
    function renounceOwnership() public view override onlyOwner { revert Unauthorized(); }
}
