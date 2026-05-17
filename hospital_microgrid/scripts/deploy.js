const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with the account:", deployer.address);

  // 1. Deploy EnergyToken
  const EnergyToken = await hre.ethers.getContractFactory("EnergyToken");
  const energyToken = await EnergyToken.deploy();
  await energyToken.deployed();
  console.log("EnergyToken deployed to:", energyToken.address);

  // 2. Deploy PriorityGuard
  const PriorityGuard = await hre.ethers.getContractFactory("PriorityGuard");
  const priorityGuard = await PriorityGuard.deploy();
  await priorityGuard.deployed();
  console.log("PriorityGuard deployed to:", priorityGuard.address);

  // 3. Deploy EnergyMarket
  const EnergyMarket = await hre.ethers.getContractFactory("EnergyMarket");
  const energyMarket = await EnergyMarket.deploy(energyToken.address, priorityGuard.address);
  await energyMarket.deployed();
  console.log("EnergyMarket deployed to:", energyMarket.address);

  // Save addresses
  const deploymentsDir = path.join(__dirname, "..", "deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir);
  }

  const addresses = {
    EnergyToken: energyToken.address,
    PriorityGuard: priorityGuard.address,
    EnergyMarket: energyMarket.address,
    network: hre.network.name,
    deployedAt: new Date().toISOString()
  };

  fs.writeFileSync(
    path.join(deploymentsDir, "addresses.json"),
    JSON.stringify(addresses, null, 2)
  );

  // Register 10 hospital sections
  const sections = [
    { name: "Reanimation", priority: 1 },
    { name: "BlocOperatoire", priority: 1 },
    { name: "Urgences", priority: 1 },
    { name: "Neonatologie", priority: 1 },
    { name: "Dialyse", priority: 2 },
    { name: "Maternite", priority: 2 },
    { name: "Laboratoire", priority: 2 },
    { name: "Pharmacie", priority: 2 },
    { name: "Radiologie", priority: 3 },
    { name: "General", priority: 5 }
  ];

  const sectionAddresses = {};

  console.log("\nRegistering Hospital Sections:");
  for (const section of sections) {
    const randomWallet = hre.ethers.Wallet.createRandom();
    const address = randomWallet.address;
    
    const tx = await energyToken.registerSection(address, section.name, section.priority);
    await tx.wait();
    
    sectionAddresses[section.name] = {
      address: address,
      priority: section.priority
    };
    console.log(`- ${section.name} (P${section.priority}): ${address}`);
  }

  fs.writeFileSync(
    path.join(deploymentsDir, "sections.json"),
    JSON.stringify(sectionAddresses, null, 2)
  );

  console.log("\nDeployment and registration complete!");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
