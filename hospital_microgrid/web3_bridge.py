import json
import os
import time
from datetime import datetime
from web3 import Web3

class HospitalBridge:
    def __init__(self, rpc_url="http://127.0.0.1:8545"):
        # Connect to node
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise Exception(f"Failed to connect to Ethereum node at {rpc_url}")
        
        # Set oracle account (Hardhat account[0])
        self.oracle_account = self.w3.eth.accounts[0]
        self.w3.eth.default_account = self.oracle_account
        
        # Paths
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.artifacts_dir = os.path.join(self.base_dir, "artifacts", "blockchain", "contracts")
        self.deployments_dir = os.path.join(self.base_dir, "deployments")
        self.log_file = os.path.join(self.base_dir, "bridge_log.txt")
        
        # Load addresses
        with open(os.path.join(self.deployments_dir, "addresses.json"), "r") as f:
            self.addresses = json.load(f)
            
        with open(os.path.join(self.deployments_dir, "sections.json"), "r") as f:
            self.sections = json.load(f)
            
        # Load ABIs and initialize contracts
        self.energy_token = self._load_contract("EnergyToken")
        self.priority_guard = self._load_contract("PriorityGuard")
        self.energy_market = self._load_contract("EnergyMarket")
        
        print(f"Bridge initialized. Oracle: {self.oracle_account}")

    def _load_contract(self, name):
        artifact_path = os.path.join(self.artifacts_dir, f"{name}.sol", f"{name}.json")
        with open(artifact_path, "r") as f:
            artifact = json.load(f)
        
        address = self.addresses.get(name)
        if not address:
            raise Exception(f"Address for {name} not found in deployments.")
            
        return self.w3.eth.contract(address=address, abi=artifact["abi"])

    def _log_transaction(self, action, tx_hash):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] ACTION: {action} | TX_HASH: {tx_hash.hex()}\n"
        with open(self.log_file, "a") as f:
            f.write(log_entry)
        print(f"Transaction logged: {action} -> {tx_hash.hex()}")

    def submit_alert(self, alert_level, energy_balance, affected_section, min_battery=80, generator_status=None):
        """
        Calls PriorityGuard.submitAlert()
        alert_level: "NORMAL", "WARNING", "CRITICAL"
        """
        levels = {"NORMAL": 0, "WARNING": 1, "CRITICAL": 2}
        level_int = levels.get(alert_level.upper(), 0)
        
        metadata = f"GENERATOR_STATUS={generator_status}" if generator_status else ""
        print(f"Submitting {alert_level} alert for {affected_section} {metadata}...")
        try:
            tx_hash = self.priority_guard.functions.submitAlert(
                level_int,
                int(energy_balance),
                int(min_battery),
                affected_section
            ).transact()
            
            self._log_transaction(f"SUBMIT_ALERT({alert_level}, {affected_section}) {metadata}", tx_hash)
            return tx_hash
        except Exception as e:
            print(f"Error submitting alert: {e}")
            return None

    def log_generator_event(self, generator_id, event_type, fuel_level, output_kw):
        """
        Calls PriorityGuard.logGeneratorEvent()
        """
        try:
            tx_hash = self.priority_guard.functions.logGeneratorEvent(
                int(generator_id),
                event_type,
                int(fuel_level),
                int(output_kw)
            ).transact()
            self._log_transaction(f"LOG_GENERATOR_EVENT({generator_id}, {event_type}, fuel={fuel_level}, output={output_kw})", tx_hash)
            return tx_hash
        except Exception as e:
            print(f"Error logging generator event: {e}")
            return None

    def execute_trade(self, donor_name, receiver_name, amount_kwh, reason):
        """
        Calls EnergyMarket.executeTrade()
        """
        donor = self.sections.get(donor_name)
        receiver = self.sections.get(receiver_name)
        
        if not donor or not receiver:
            print(f"Error: Section names not found: {donor_name} or {receiver_name}")
            return None
            
        donor_addr = donor["address"]
        receiver_addr = receiver["address"]
        
        # Generate a dummy hash for the trade (as required by contract)
        precomputed_hash = self.w3.keccak(text=f"{donor_name}-{receiver_name}-{amount_kwh}-{time.time()}").hex()
        
        print(f"Executing trade: {donor_name} -> {receiver_name} ({amount_kwh} kWh)...")
        try:
            # First, ensure donor has enough tokens (1 kWh = 10 tokens)
            # In a real scenario, this would be pre-allocated. 
            # For this bridge, we'll assume the oracle/owner can mint if needed for simulation.
            needed_tokens = amount_kwh * 10
            current_balance = self.energy_token.functions.getSectionBalance(donor_addr).call()
            
            if current_balance < needed_tokens:
                print(f"Donor {donor_name} has insufficient balance ({current_balance} tokens). Minting {needed_tokens} tokens...")
                self.energy_token.functions.mint(donor_addr, needed_tokens).transact()

            tx_hash = self.energy_market.functions.executeTrade(
                donor_addr,
                receiver_addr,
                int(amount_kwh),
                reason,
                precomputed_hash
            ).transact()
            
            self._log_transaction(f"EXECUTE_TRADE({donor_name}->{receiver_name}, {amount_kwh}kWh)", tx_hash)
            return tx_hash
        except Exception as e:
            print(f"Error executing trade: {e}")
            return None

    def log_grid_event(self, event_type, event_id, capacity, status):
        """
        Calls EnergyMarket.logGridEvent()
        """
        print(f"Logging grid event: {event_type} (ID: {event_id})...")
        try:
            tx_hash = self.energy_market.functions.logGridEvent(
                event_type,
                int(event_id),
                int(capacity),
                status
            ).transact()
            
            self._log_transaction(f"LOG_GRID_EVENT({event_type}, {status})", tx_hash)
            return tx_hash
        except Exception as e:
            print(f"Error logging grid event: {e}")
            return None

if __name__ == "__main__":
    # Example usage
    bridge = HospitalBridge()
    bridge.submit_alert("WARNING", 500, "Radiologie")
