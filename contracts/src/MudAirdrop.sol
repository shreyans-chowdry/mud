// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {MerkleProof} from "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";
import {SafeERC20, IERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
contract MudAirdrop is Ownable2Step, ReentrancyGuard {
    using SafeERC20 for IERC20;
    IERC20 public immutable token;
    uint256 public immutable allocation;
    uint256 public immutable expiry;
    bytes32 public merkleRoot;
    uint256[40] private claimedBitmap;
    uint256 public claimedCount;
    uint256 public claimedAmount;
    event RootUpdated(bytes32 indexed root);
    event Claimed(uint256 indexed index, address indexed account, uint256 amount);
    event Recovered(address indexed recipient, uint256 amount);
    error InvalidClaim();
    constructor(address owner_, address token_, bytes32 root_, uint256 allocation_, uint256 expiry_)
        Ownable(owner_)
    {
        if (token_.code.length == 0 || root_ == bytes32(0) || allocation_ == 0 || expiry_ <= block.timestamp)
            revert InvalidClaim();
        token = IERC20(token_);
        merkleRoot = root_;
        allocation = allocation_;
        expiry = expiry_;
    }
    function isClaimed(uint256 index) public view returns (bool) {
        if (index >= 10000) revert InvalidClaim();
        return claimedBitmap[index >> 8] & (uint256(1) << (index & 255)) != 0;
    }
    function setRoot(bytes32 root) external onlyOwner {
        if (claimedCount != 0 || root == bytes32(0) || block.timestamp >= expiry) revert InvalidClaim();
        merkleRoot = root;
        emit RootUpdated(root);
    }
    function leaf(uint256 index, address account, uint256 amount) public pure returns (bytes32) {
        return keccak256(bytes.concat(keccak256(abi.encode(index, account, amount))));
    }
    function claim(uint256 index, address account, uint256 amount, bytes32[] calldata proof) external nonReentrant {
        if (block.timestamp >= expiry || account == address(0) || amount == 0 || index >= 10000 || isClaimed(index)
            || amount > allocation - claimedAmount || token.balanceOf(address(this)) < allocation - claimedAmount
            || !MerkleProof.verifyCalldata(proof, merkleRoot, leaf(index, account, amount))) revert InvalidClaim();
        claimedBitmap[index >> 8] |= uint256(1) << (index & 255);
        claimedCount++;
        claimedAmount += amount;
        token.safeTransfer(account, amount);
        emit Claimed(index, account, amount);
    }
    function recover(address to) external onlyOwner nonReentrant {
        if (block.timestamp < expiry || to == address(0)) revert InvalidClaim();
        uint256 amount = token.balanceOf(address(this));
        token.safeTransfer(to, amount);
        emit Recovered(to, amount);
    }
    function renounceOwnership() public view override onlyOwner { revert InvalidClaim(); }
}
