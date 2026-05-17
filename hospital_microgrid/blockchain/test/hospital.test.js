const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Hospital Microgrid System", function () {
  let EnergyToken, energyToken;
  let PriorityGuard, priorityGuard;
  let EnergyMarket, energyMarket;
  let owner, oracle, section1, section2, unregistered;

  beforeEach(async function () {
    [owner, oracle, section1, section2, unregistered] = await ethers.getSigners();

    EnergyToken = await ethers.getContractFactory("EnergyToken");
    energyToken = await EnergyToken.deploy();
    await energyToken.deployed();

    PriorityGuard = await ethers.getContractFactory("PriorityGuard");
    priorityGuard = await PriorityGuard.deploy();
    await priorityGuard.deployed();

    EnergyMarket = await ethers.getContractFactory("EnergyMarket");
    energyMarket = await EnergyMarket.deploy(energyToken.address, priorityGuard.address);
    await energyMarket.deployed();
  });

  describe("EnergyToken", function () {
    it("should register a section correctly", async function () {
      await energyToken.registerSection(section1.address, "ICU", 1);
      const priority = await energyToken.getSectionPriority(section1.address);
      expect(priority).to.equal(1);
    });

    it("should mint tokens to a section", async function () {
      await energyToken.registerSection(section1.address, "ICU", 1);
      await energyToken.mint(section1.address, 100);
      const balance = await energyToken.getSectionBalance(section1.address);
      expect(balance).to.equal(100);
    });

    it("should transfer tokens between sections", async function () {
      await energyToken.registerSection(section1.address, "Donor", 4);
      await energyToken.registerSection(section2.address, "Receiver", 1);
      await energyToken.mint(section1.address, 100);
      
      await energyToken.connect(section1).transfer(section2.address, 40);
      
      expect(await energyToken.getSectionBalance(section1.address)).to.equal(60);
      expect(await energyToken.getSectionBalance(section2.address)).to.equal(40);
    });

    it("should reject transfer from unregistered section", async function () {
      await energyToken.registerSection(section2.address, "Receiver", 1);
      await expect(
        energyToken.connect(unregistered).transfer(section2.address, 10)
      ).to.be.revertedWith("Address not registered as a section");
    });

    it("should reject mint from non-owner", async function () {
      await energyToken.registerSection(section1.address, "ICU", 1);
      await expect(
        energyToken.connect(section1).mint(section1.address, 100)
      ).to.be.revertedWith("Only owner can perform this action");
    });
  });

  describe("PriorityGuard", function () {
    beforeEach(async function () {
      await priorityGuard.registerOracle(oracle.address);
    });

    it("should set oracle address correctly", async function () {
      expect(await priorityGuard.oracle()).to.equal(oracle.address);
    });

    it("should accept alert from oracle", async function () {
      await priorityGuard.connect(oracle).submitAlert(0, 500, 80, "General");
      const lastAlert = await priorityGuard.getLastAlert();
      expect(lastAlert.level).to.equal(0); // NORMAL
    });

    it("should reject alert from non-oracle", async function () {
      await expect(
        priorityGuard.connect(section1).submitAlert(0, 500, 80, "General")
      ).to.be.revertedWith("Only oracle can submit alerts");
    });

    it("should activate protocol on CRITICAL alert", async function () {
      await priorityGuard.connect(oracle).submitAlert(2, 100, 20, "Reanimation");
      expect(await priorityGuard.protocolActive()).to.be.true;
    });

    it("should cut power to P4 and P5 during protocol", async function () {
      await priorityGuard.connect(oracle).submitAlert(2, 100, 20, "Reanimation");
      expect(await priorityGuard.isSectionPowered(1)).to.be.true;
      expect(await priorityGuard.isSectionPowered(3)).to.be.true;
      expect(await priorityGuard.isSectionPowered(4)).to.be.false;
      expect(await priorityGuard.isSectionPowered(5)).to.be.false;
    });

    it("should restore protocol on NORMAL alert after CRITICAL", async function () {
      await priorityGuard.connect(oracle).submitAlert(2, 100, 20, "Reanimation");
      expect(await priorityGuard.protocolActive()).to.be.true;
      
      await priorityGuard.connect(oracle).submitAlert(0, 500, 80, "Grid Restored");
      expect(await priorityGuard.protocolActive()).to.be.false;
    });

    it("should store alert history correctly", async function () {
      await priorityGuard.connect(oracle).submitAlert(0, 500, 80, "A1");
      await priorityGuard.connect(oracle).submitAlert(1, 400, 60, "A2");
      
      const history = await priorityGuard.getAlertHistory(2);
      expect(history.length).to.equal(2);
      expect(history[0].affectedSection).to.equal("A2");
      expect(history[1].affectedSection).to.equal("A1");
    });
  });

  describe("EnergyMarket", function () {
    beforeEach(async function () {
      await energyToken.registerSection(section1.address, "Donor", 4);
      await energyToken.registerSection(section2.address, "Receiver", 2);
      await energyToken.mint(section1.address, 500);
    });

    it("should execute a valid trade between sections", async function () {
      // 10 kWh = 100 tokens
      await energyMarket.executeTrade(section1.address, section2.address, 10, "Outage support", "hash123");
      
      expect(await energyToken.getSectionBalance(section1.address)).to.equal(400);
      expect(await energyToken.getSectionBalance(section2.address)).to.equal(100);
      
      const trade = await energyMarket.trades(0);
      expect(trade.amountKwh).to.equal(10);
      expect(trade.verified).to.be.false;
    });

    it("should reject trade where donor priority <= receiver priority", async function () {
      // Donor P4, Receiver P2. 4 > 2 is valid.
      // Now try Donor P2 to Receiver P4. 2 > 4 is invalid.
      await expect(
        energyMarket.executeTrade(section2.address, section1.address, 10, "Invalid", "hash")
      ).to.be.revertedWith("Donor must have lower priority than receiver");
    });

    it("should reject trade amount above 20 kWh", async function () {
      await expect(
        energyMarket.executeTrade(section1.address, section2.address, 25, "Too much", "hash")
      ).to.be.revertedWith("Trade amount must be between 1 and 20 kWh");
    });

    it("should log a grid event correctly", async function () {
      await energyMarket.logGridEvent("BLACKOUT", 101, 5000, "ONGOING");
      const event = await energyMarket.gridEvents(101);
      expect(event.eventType).to.equal("BLACKOUT");
    });

    it("should return correct trade history for a section", async function () {
      await energyMarket.executeTrade(section1.address, section2.address, 5, "T1", "h1");
      await energyMarket.executeTrade(section1.address, section2.address, 5, "T2", "h2");
      
      const history = await energyMarket.getTradeHistory(section1.address);
      expect(history.length).to.equal(2);
    });

    it("should return correct total traded amount", async function () {
      await energyMarket.executeTrade(section1.address, section2.address, 5, "T1", "h1");
      await energyMarket.executeTrade(section1.address, section2.address, 10, "T2", "h2");
      
      expect(await energyMarket.getTotalTraded()).to.equal(15);
    });
  });
});
