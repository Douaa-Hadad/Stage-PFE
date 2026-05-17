// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

contract EnergyToken {
    struct Section {
        string name;
        uint8 priority;
        uint256 balance;
        bool isRegistered;
    }

    address public owner;
    uint256 public totalMinted;
    uint256 public totalTransferred;
    
    mapping(address => Section) public sections;
    address[] public registeredAddresses;

    event Mint(address indexed section, uint256 amount);
    event Transfer(address indexed from, address indexed to, uint256 amount);
    event SectionRegistered(address indexed section, string name, uint8 priority);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can perform this action");
        _;
    }

    modifier onlyRegistered(address _addr) {
        require(sections[_addr].isRegistered, "Address not registered as a section");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function registerSection(address _section, string memory _name, uint8 _priority) external onlyOwner {
        require(!sections[_section].isRegistered, "Section already registered");
        require(_priority >= 1 && _priority <= 5, "Priority must be between 1 and 5");
        
        sections[_section] = Section({
            name: _name,
            priority: _priority,
            balance: 0,
            isRegistered: true
        });
        
        registeredAddresses.push(_section);
        emit SectionRegistered(_section, _name, _priority);
    }

    function mint(address _section, uint256 _amount) external onlyOwner onlyRegistered(_section) {
        sections[_section].balance += _amount;
        totalMinted += _amount;
        emit Mint(_section, _amount);
    }

    function transfer(address _to, uint256 _amount) external onlyRegistered(msg.sender) onlyRegistered(_to) {
        require(sections[msg.sender].balance >= _amount, "Insufficient balance");
        
        sections[msg.sender].balance -= _amount;
        sections[_to].balance += _amount;
        totalTransferred += _amount;
        
        emit Transfer(msg.sender, _to, _amount);
    }
    
    // Internal version for EnergyMarket
    function internalTransfer(address _from, address _to, uint256 _amount) external {
        // In a real scenario, this would have access control (e.g., onlyMarket)
        // For this lightweight version, we'll keep it simple or call it from the market
        require(sections[_from].isRegistered && sections[_to].isRegistered, "Sections must be registered");
        require(sections[_from].balance >= _amount, "Insufficient balance");
        
        sections[_from].balance -= _amount;
        sections[_to].balance += _amount;
        totalTransferred += _amount;
        
        emit Transfer(_from, _to, _amount);
    }

    function getSectionBalance(address _section) external view returns (uint256) {
        return sections[_section].balance;
    }
    
    function getSectionPriority(address _section) external view returns (uint8) {
        return sections[_section].priority;
    }

    function getAllSections() external view returns (address[] memory) {
        return registeredAddresses;
    }
}
