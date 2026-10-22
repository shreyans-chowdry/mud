// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeERC20, IERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IMudToken} from "./interfaces/IMudToken.sol";
import {MudPriceOracle} from "./MudPriceOracle.sol";

contract MudMarketplace is Ownable2Step, ReentrancyGuard, Pausable, EIP712 {
    using SafeERC20 for IERC20;
    struct Product {
        address merchant;
        uint256 usdPrice6;
        uint256 remaining;
        uint256 perBuyerLimit;
        bool listed;
        string metadataURI;
    }
    struct Order {
        bytes32 orderId;
        uint256 productId;
        address buyer;
        uint256 maxMudAmount;
        uint256 deadline;
        uint256 nonce;
    }
    bytes32 public constant ORDER_TYPEHASH = keccak256("Order(bytes32 orderId,uint256 productId,address buyer,uint256 maxMudAmount,uint256 deadline,uint256 nonce)");
    IMudToken public immutable token;
    MudPriceOracle public immutable oracle;
    address public immutable guardian;
    uint256 public nextProductId = 1;
    mapping(address => bool) public merchants;
    mapping(address => bool) public merchantBlocked;
    mapping(uint256 => Product) public products;
    mapping(uint256 => mapping(address => uint256)) public purchased;
    mapping(address => uint256) public nonces;
    mapping(bytes32 => bool) public usedOrders;
    event MerchantUpdated(address indexed merchant, bool active);
    event MerchantBlocked(address indexed merchant, bool blocked);
    event ProductUpdated(uint256 indexed productId, address indexed merchant, uint256 usdPrice6, uint256 inventory, bool listed, string metadataURI);
    event ItemPurchased(uint256 indexed productId, address indexed buyer, address indexed merchant, uint256 mudPaid, uint256 mudBurned);
    event OrderSettled(bytes32 indexed orderId, uint256 indexed productId, address indexed buyer, uint256 mudPaid);
    error InvalidProduct();
    error InvalidOrder();
    error Unauthorized();
    constructor(address owner_, address guardian_, address token_, address oracle_)
        Ownable(owner_) EIP712("MUD Marketplace", "1")
    {
        if (guardian_ == address(0) || token_.code.length == 0 || oracle_.code.length == 0) revert InvalidProduct();
        guardian = guardian_;
        token = IMudToken(token_);
        oracle = MudPriceOracle(oracle_);
    }
    function registerMerchant() external {
        if (merchantBlocked[msg.sender]) revert Unauthorized();
        merchants[msg.sender] = true;
        emit MerchantUpdated(msg.sender, true);
    }
    function deactivateMerchant() external {
        merchants[msg.sender] = false;
        emit MerchantUpdated(msg.sender, false);
    }
    function setMerchant(address merchant, bool active) external onlyOwner {
        if (merchant == address(0)) revert InvalidProduct();
        merchants[merchant] = active;
        merchantBlocked[merchant] = !active;
        emit MerchantBlocked(merchant, !active);
        emit MerchantUpdated(merchant, active);
    }
    function createProduct(uint256 usdPrice6, uint256 inventory, uint256 perBuyerLimit, string calldata uri)
        external returns (uint256 id)
    {
        if (!merchants[msg.sender]) revert Unauthorized();
        _validate(usdPrice6, inventory, perBuyerLimit, uri);
        id = nextProductId++;
        products[id] = Product(msg.sender, usdPrice6, inventory, perBuyerLimit, true, uri);
        emit ProductUpdated(id, msg.sender, usdPrice6, inventory, true, uri);
    }
    function updateProduct(uint256 id, uint256 usdPrice6, uint256 inventory, uint256 perBuyerLimit, bool listed, string calldata uri) external {
        Product storage p = products[id];
        if (p.merchant != msg.sender) revert Unauthorized();
        _validate(usdPrice6, inventory, perBuyerLimit, uri);
        p.usdPrice6 = usdPrice6;
        p.remaining = inventory;
        p.perBuyerLimit = perBuyerLimit;
        p.listed = listed;
        p.metadataURI = uri;
        emit ProductUpdated(id, msg.sender, usdPrice6, inventory, listed, uri);
    }
    function delistProduct(uint256 id) external {
        Product storage p = products[id];
        if (p.merchant != msg.sender && msg.sender != owner()) revert Unauthorized();
        p.listed = false;
        emit ProductUpdated(id, p.merchant, p.usdPrice6, p.remaining, false, p.metadataURI);
    }
    function _validate(uint256 price, uint256 inventory, uint256 limit, string calldata uri) internal pure {
        if (price == 0 || price > 1e15 || inventory > 1e9 || limit == 0 || limit > 1e9 || bytes(uri).length > 512)
            revert InvalidProduct();
    }
    function quoteProduct(uint256 id) public view returns (uint256 mudRequired, uint256 price8, uint256 updatedAt) {
        Product storage p = products[id];
        if (!p.listed || !merchants[p.merchant] || p.remaining == 0) revert InvalidProduct();
        (price8, updatedAt) = oracle.read();
        uint256 collateralAtoms = Math.mulDiv(p.usdPrice6, (10 ** token.collateralDecimals()) * 1e8,
            1e6 * price8, Math.Rounding.Ceil);
        mudRequired = Math.mulDiv(collateralAtoms, 1e18, token.getSpotPrice(), Math.Rounding.Ceil);
        if (mudRequired == 0) revert InvalidProduct();
    }
    function purchaseItem(uint256 productId, uint256 maxMudAmount, uint256 deadline) external nonReentrant whenNotPaused {
        _purchase(productId, maxMudAmount, deadline, bytes32(0));
    }
    function hashOrder(Order calldata order) public view returns (bytes32) {
        return _hashTypedDataV4(keccak256(abi.encode(ORDER_TYPEHASH, order.orderId, order.productId,
            order.buyer, order.maxMudAmount, order.deadline, order.nonce)));
    }
    /// @notice Buyer signs and submits. Signatures bind chain, deployment, nonce and constraints.
    function purchaseOrder(Order calldata order, bytes calldata signature) external nonReentrant whenNotPaused {
        if (order.buyer != msg.sender || order.orderId == bytes32(0) || usedOrders[order.orderId]
            || order.nonce != nonces[msg.sender] || ECDSA.recover(hashOrder(order), signature) != msg.sender)
            revert InvalidOrder();
        usedOrders[order.orderId] = true;
        nonces[msg.sender]++;
        _purchase(order.productId, order.maxMudAmount, order.deadline, order.orderId);
    }
    function _purchase(uint256 id, uint256 maxMudAmount, uint256 deadline, bytes32 orderId) internal {
        if (block.timestamp > deadline) revert InvalidOrder();
        Product storage p = products[id];
        if (purchased[id][msg.sender] >= p.perBuyerLimit) revert InvalidProduct();
        (uint256 payment,,) = quoteProduct(id);
        if (payment > maxMudAmount) revert InvalidOrder();
        uint256 burned = Math.mulDiv(payment, 500, 10000);
        p.remaining--;
        purchased[id][msg.sender]++;
        uint256 balance = token.balanceOf(address(this));
        IERC20(address(token)).safeTransferFrom(msg.sender, address(this), payment);
        if (token.balanceOf(address(this)) != balance + payment) revert InvalidOrder();
        uint256 merchantBalance = token.balanceOf(p.merchant);
        IERC20(address(token)).safeTransfer(p.merchant, payment - burned);
        if (token.balanceOf(p.merchant) != merchantBalance + payment - burned) revert InvalidOrder();
        token.burn(burned);
        emit ItemPurchased(id, msg.sender, p.merchant, payment, burned);
        emit OrderSettled(orderId, id, msg.sender, payment);
    }
    function pause() external {
        if (msg.sender != guardian && msg.sender != owner()) revert Unauthorized();
        _pause();
    }
    function unpause() external onlyOwner { _unpause(); }
    function renounceOwnership() public view override onlyOwner { revert Unauthorized(); }
}
