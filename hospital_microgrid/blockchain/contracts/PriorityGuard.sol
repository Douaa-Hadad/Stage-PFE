// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

contract PriorityGuard {
    enum AlertLevel { NORMAL, WARNING, CRITICAL }

    struct Alert {
        uint256 timestamp;
        AlertLevel level;
        uint256 energyBalance;
        uint256 minBatteryPct;
        string affectedSection;
        string actionTaken;
    }

    struct GeneratorEvent {
        uint8 generatorId;
        string eventType;
        uint256 timestamp;
        uint256 fuelLevel;
        uint256 outputKw;
    }

    address public owner;
    address public oracle;
    bool public protocolActive;
    
    Alert[100] public alerts;
    uint256 public alertCount;
    uint256 public head;

    GeneratorEvent[50] public generatorEvents;
    uint256 public generatorEventCount;
    uint256 public generatorEventHead;

    event AlertReceived(AlertLevel level, uint256 timestamp);
    event ProtocolActivated(uint256 timestamp, string reason);
    event ProtocolRestored(uint256 timestamp);
    event GeneratorEventLogged(uint8 generatorId, string eventType, uint256 timestamp);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can perform this action");
        _;
    }

    modifier onlyOracle() {
        require(msg.sender == oracle, "Only oracle can submit alerts");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function registerOracle(address _oracle) external onlyOwner {
        oracle = _oracle;
    }

    function submitAlert(
        AlertLevel _level, 
        uint256 _energyBalance, 
        uint256 _minBatteryPct, 
        string memory _affectedSection
    ) external onlyOracle {
        string memory action = "NONE";
        
        if (_level == AlertLevel.CRITICAL && !protocolActive) {
            triggerProtocol();
            action = "PROTOCOL_ACTIVATED";
        } else if (_level == AlertLevel.NORMAL && protocolActive) {
            restoreProtocol();
            action = "PROTOCOL_RESTORED";
        }

        Alert memory newAlert = Alert({
            timestamp: block.timestamp,
            level: _level,
            energyBalance: _energyBalance,
            minBatteryPct: _minBatteryPct,
            affectedSection: _affectedSection,
            actionTaken: action
        });

        alerts[head] = newAlert;
        head = (head + 1) % 100;
        alertCount++;

        emit AlertReceived(_level, block.timestamp);
    }

    function logGeneratorEvent(
        uint8 generatorId,
        string memory eventType,
        uint256 fuelLevel,
        uint256 outputKw
    ) external onlyOracle {
        GeneratorEvent memory entry = GeneratorEvent({
            generatorId: generatorId,
            eventType: eventType,
            timestamp: block.timestamp,
            fuelLevel: fuelLevel,
            outputKw: outputKw
        });

        generatorEvents[generatorEventHead] = entry;
        generatorEventHead = (generatorEventHead + 1) % 50;
        generatorEventCount++;

        emit GeneratorEventLogged(generatorId, eventType, block.timestamp);
    }

    function getGeneratorStatus(uint8 generatorId) external view returns (GeneratorEvent memory) {
        require(generatorEventCount > 0, "No generator events recorded");
        uint256 checked = 0;
        uint256 index = generatorEventHead;

        while (checked < generatorEventCount && checked < 50) {
            index = (index + 50 - 1) % 50;
            GeneratorEvent memory candidate = generatorEvents[index];
            if (candidate.generatorId == generatorId) {
                return candidate;
            }
            checked++;
        }

        revert("Generator status not found");
    }

    function triggerProtocol() internal {
        protocolActive = true;
        emit ProtocolActivated(block.timestamp, "Critical alert received - cutting P4 and P5");
    }

    function restoreProtocol() internal {
        protocolActive = false;
        emit ProtocolRestored(block.timestamp);
    }

    function getLastAlert() external view returns (Alert memory) {
        require(alertCount > 0, "No alerts recorded");
        uint256 lastIndex = (head == 0) ? 99 : head - 1;
        return alerts[lastIndex];
    }

    function getAlertHistory(uint256 _count) external view returns (Alert[] memory) {
        uint256 limit = _count > alertCount ? alertCount : _count;
        if (limit > 100) limit = 100;

        Alert[] memory result = new Alert[](limit);
        for (uint256 i = 0; i < limit; i++) {
            uint256 index = (head + 100 - 1 - i) % 100;
            result[i] = alerts[index];
        }
        return result;
    }

    function isSectionPowered(uint8 _priority) external view returns (bool) {
        if (!protocolActive) return true;
        // During protocol: P1,P2,P3 = true, P4,P5 = false
        return _priority <= 3;
    }
}
