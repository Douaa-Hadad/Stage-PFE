// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

import "./EnergyToken.sol";
import "./PriorityGuard.sol";

contract EnergyMarket {
    struct Trade {
        uint256 tradeId;
        uint256 timestamp;
        address donor;
        address receiver;
        uint8 donorPriority;
        uint8 receiverPriority;
        uint256 amountKwh;
        string reason;
        string blockchainHash;
        bool verified;
    }

    struct GridEvent {
        uint256 eventId;
        string eventType;
        uint256 capacity;
        string status;
        uint256 timestamp;
    }

    EnergyToken public tokenContract;
    PriorityGuard public guardContract;
    address public owner;
    
    uint256 public nextTradeId;
    mapping(uint256 => Trade) public trades;
    mapping(address => uint256[]) public sectionTrades;
    uint256 public totalKwhTraded;

    mapping(uint256 => GridEvent) public gridEvents;

    event TradeExecuted(uint256 indexed tradeId, address indexed donor, address indexed receiver, uint256 amountKwh, uint256 timestamp);
    event TradeVerified(uint256 indexed tradeId);
    event GridEventLogged(uint256 indexed eventId, string eventType, uint256 timestamp);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can perform this action");
        _;
    }

    constructor(address _tokenContract, address _guardContract) {
        owner = msg.sender;
        tokenContract = EnergyToken(_tokenContract);
        guardContract = PriorityGuard(_guardContract);
    }

    function executeTrade(
        address _donor, 
        address _receiver, 
        uint256 _amountKwh, 
        string memory _reason, 
        string memory _precomputedHash
    ) external {
        uint8 donorP = tokenContract.getSectionPriority(_donor);
        uint8 receiverP = tokenContract.getSectionPriority(_receiver);

        // Validates: donor priority > receiver priority (numeric value, e.g. 4 > 2)
        require(donorP > receiverP, "Donor must have lower priority than receiver");
        require(_amountKwh > 0 && _amountKwh <= 20, "Trade amount must be between 1 and 20 kWh");
        
        // EnergyToken.internalTransfer will revert if sections are not registered or balance insufficient
        // 1 kWh = 10 tokens (since 1 token = 0.1 kWh)
        uint256 tokenAmount = _amountKwh * 10;
        tokenContract.internalTransfer(_donor, _receiver, tokenAmount);

        uint256 tradeId = nextTradeId++;
        trades[tradeId] = Trade({
            tradeId: tradeId,
            timestamp: block.timestamp,
            donor: _donor,
            receiver: _receiver,
            donorPriority: donorP,
            receiverPriority: receiverP,
            amountKwh: _amountKwh,
            reason: _reason,
            blockchainHash: _precomputedHash,
            verified: false
        });

        sectionTrades[_donor].push(tradeId);
        sectionTrades[_receiver].push(tradeId);
        totalKwhTraded += _amountKwh;

        emit TradeExecuted(tradeId, _donor, _receiver, _amountKwh, block.timestamp);
    }

    function verifyTrade(uint256 _tradeId) external onlyOwner {
        require(_tradeId < nextTradeId, "Invalid trade ID");
        trades[_tradeId].verified = true;
        emit TradeVerified(_tradeId);
    }

    function logGridEvent(
        string memory _eventType, 
        uint256 _eventId, 
        uint256 _capacity, 
        string memory _status
    ) external onlyOwner {
        gridEvents[_eventId] = GridEvent({
            eventId: _eventId,
            eventType: _eventType,
            capacity: _capacity,
            status: _status,
            timestamp: block.timestamp
        });

        emit GridEventLogged(_eventId, _eventType, block.timestamp);
    }

    function getTradeHistory(address _section) external view returns (Trade[] memory) {
        uint256[] memory ids = sectionTrades[_section];
        Trade[] memory result = new Trade[](ids.length);
        for (uint256 i = 0; i < ids.length; i++) {
            result[i] = trades[ids[i]];
        }
        return result;
    }

    function getTotalTraded() external view returns (uint256) {
        return totalKwhTraded;
    }

    function getTradeCount() external view returns (uint256) {
        return nextTradeId;
    }
}
