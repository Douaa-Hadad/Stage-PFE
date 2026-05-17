import time
import os
import sys

# Add parent directory (project root) to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3_bridge import HospitalBridge

def run_test():
    print("=== Starting Hospital Microgrid Bridge Test ===")
    
    try:
        bridge = HospitalBridge()
        
        # 0. Preparation: Register Oracle (since deploy.js didn't do it)
        # We use the owner (accounts[0]) to register itself as oracle
        print("Ensuring Oracle is registered...")
        current_oracle = bridge.priority_guard.functions.oracle().call()
        if current_oracle != bridge.oracle_account:
            print(f"Registering {bridge.oracle_account} as Oracle...")
            # accounts[0] is the owner, so it can call registerOracle
            tx_hash = bridge.priority_guard.functions.registerOracle(bridge.oracle_account).transact()
            bridge.w3.eth.wait_for_transaction_receipt(tx_hash)
            print("Oracle registered successfully.")
        else:
            print("Oracle already registered.")

        # 1. Simulate a CRITICAL alert
        # (alert level + energy balance + affected section)
        print("\n--- Test 1: Sending CRITICAL alert ---")
        bridge.submit_alert(
            alert_level="CRITICAL", 
            energy_balance=120, 
            affected_section="General"
        )
        
        # Give it a moment to process
        time.sleep(1)
        
        # 2. Simulate a trade from Pharmacie to Bloc Opératoire of 15 kWh
        # (donor section, receiver section, amount in kWh, and reason)
        print("\n--- Test 2: Executing energy trade ---")
        bridge.execute_trade(
            donor_name="Pharmacie",
            receiver_name="BlocOperatoire",
            amount_kwh=15,
            reason="High priority surgery demand"
        )
        
        # 3. Simulate a grid outage event being logged
        print("\n--- Test 3: Logging grid event ---")
        bridge.log_grid_event(
            event_type="OUTAGE",
            event_id=1001,
            capacity=0,
            status="CRITICAL_OFF"
        )
        
        print("\n=== Test Completed Successfully ===")
        print("Check 'bridge_log.txt' for transaction details.")

    except Exception as e:
        print(f"\n!!! Test Failed: {e}")

if __name__ == "__main__":
    run_test()
