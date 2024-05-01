# Project Alpaca-execution
Execution algorithm for seamless trading of US equities and cryptos over Alpacas API.
Inputs are toggleable to set asset traded, market side, order type,
as well as take profit and stop loss for multi legged orders. Execution flow also handles fee 
computations by computing slippage costs and trading fees for crypto set by user 30 day volume tiers.
## Requirements
- Python >= 3.7
- Alpaca API Key and Secret key
- For interaction with Trade_execution.py: install required libraries: `pip install alpaca-py`
- For interaction with HTTP_request_version.py, the above installation is not required
## Keys
The Alpaca API Keys used for trading are stored in a config file located in the same directory
as the scripts. It has the following contents:
`API_KEY = "insert_api_key_here"`
`SECRET_KEY = "insert_secret_key_here"`
