# Project Alpaca-functions
Project creates functions for seamless trading of US equities and cryptos over Alpacas API.
Functions are toggleable based on user input to set asset traded, market side, order type,
as well as take profit and stop loss for multi legged orders. Functions also handle fee 
computations for filled orders.
## Requirements
- Python >= 3.7
- Alpaca API Key and Secret key
- To install required libraries: `pip install alpaca-py`
## Keys
The Alpaca API Keys used for trading are stored in a config file located in the same directory
as the scripts. It has the following contents:
`API_KEY = "insert_api_key_here"`
`SECRET_KEY = "insert_secret_key_here"`
