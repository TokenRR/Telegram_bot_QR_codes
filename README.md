# Telegram bot for create and scan QR codes
## Cloning a repository

To download this code from GitHub, open a terminal and run the following commands:
```sh
git clone https://github.com/TokenRR/Telegram_bot_QR_codes.git
cd Telegram_bot_QR_codes
```

## Installing dependencies

Create a virtual environment and install dependencies:
```sh
python -m venv venv
source venv/bin/activate  # For Windows, use venv\Scripts\activate
pip install -r requirements.txt
```

## Setting up the configuration
Open the `config.py` file and change the bot token to your own:
```python
TOKEN='paste-your-token'
```

## Start program
To start the program, execute the following command:
```sh
python main.py
```