@echo off
echo ==================================================
echo   SMART HOSPITAL MICROGRID - ONE-CLICK LAUNCH
echo ==================================================

echo [1/4] Starting Hardhat Local Blockchain Node...
start "Hardhat Node" cmd /k "npx hardhat node"

echo Waiting for node to initialize (3s)...
timeout /t 3 /nobreak > nul

echo [2/4] Deploying Smart Contracts to Localhost...
call npx hardhat run scripts/deploy.js --network localhost

echo Waiting for deployment to settle (2s)...
timeout /t 2 /nobreak > nul

echo [3/4] Launching Streamlit Dashboard...
start "Microgrid Dashboard" cmd /k "python -m streamlit run dashboard/app.py"

echo [4/4] Opening browser...
timeout /t 2 /nobreak > nul
start http://localhost:8501

echo ==================================================
echo   System is live! Check the new windows for logs.
echo ==================================================
pause
