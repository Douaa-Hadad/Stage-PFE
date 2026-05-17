require("@nomicfoundation/hardhat-toolbox");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.20",
  networks: {
    hardhat: {
      chainId: 1337
    }
  },
  paths: {
    sources: "./blockchain/contracts",
    tests: "./blockchain/test",
    cache: "./cache",
    artifacts: "./artifacts"
  }
};
