# Coinbase Advanced Volatility Watcher

This script monitors cryptocurrency pairs on Coinbase Advanced for significant price movements and sends notifications to a Discord channel. It regularly fetches the list of active USD trading pairs, tracks their price changes, and alerts you when notable movements occur.

This script is running 24/7 here: https://discord.gg/FprzuuWZ7t

## Examples:

`🔹🟦+4.33%   [VOXEL]   $0.14820  [60m +7.35%]🟧🔹`

`🔹🟪+3.28%    [NMR]   $16.37000  [60m +5.34%]🟩🔹`

`🔹◼+1.07%   [DRIFT]   $0.37950  [60m -0.91%]▪️🔸`

## Consider a donation after you buy your lambo.

BTC: `bc1qwjy0hl4z9c930kgy4nud2fp0nw8m6hzknvumgg`

ETH: `0x0941D41Cd0Ee81bd79Dbe34840bB5999C124D3F0`

SOL: `4cpdbmmp1hyTAstA3iUYdFbqeNBwjFmhQLfL5bMgf77z`

## Features

- **Real-Time Price Monitoring**: The script checks cryptocurrency prices at regular intervals and tracks historical price changes.
- **Discord Notifications**: Alerts are sent to a specified Discord channel for significant price movements, with customizable messages.
- **Automatic Pair Updates**: The list of active USD trading pairs is automatically updated every few hours.
- **Price Movement Detection**: Detects and highlights "wicked out of range" events to spot significant market movements.
- **Customizable Alerts**: Easily configure thresholds, intervals, and other settings to tailor the script to your needs.
- **Debug Mode**: Option to display detailed console output for troubleshooting or analysis.

## Installation

### Prerequisites

Ensure you have Python installed. If not, download and install it from [python.org](https://www.python.org/downloads/).

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### Step 2: Install Dependencies

Install the required Python packages using pip:

```bash
pip install requests python-dotenv
```

### Step 3: Set Up Environment Variables

Create a `.env` file in the same directory as the script and add the following lines:

```env
COINBASE_API_KEY=organizations/fake-organization-id/apiKeys/fake-api-key-id
COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----\nTHISISFAKEPRIVATEKEYDO-NOTUSEFAKEKEYINPROD\n-----END EC PRIVATE KEY-----\n
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

Replace `your_api_key`, `your_api_secret`, and `your_discord_webhook_url` with your actual Coinbase API key, secret, and Discord webhook URL.

### Step 4: Configure Script Settings

Open the script and adjust the configuration variables to fit your needs. Key settings include:

- `FETCH_INTERVAL`: Time in seconds between each price fetch.
- `HISTORY_RETENTION_MINUTES`: How long to retain price history.
- `NOTIFICATION_THRESHOLD`: Minimum percentage change required to trigger a notification.
- `DEBUG`: Set to `True` for console-only output; set to `False` for Discord notifications.

### Step 5: Run the Script

Execute the script in your preferred Python environment:

```bash
python coinbase-volatility-scanner.py
```

### Step 6: Monitor Output

The script will print logs to the console and send notifications to Discord based on the settings you configured.

## Script Overview

1. **Environment Setup**: Loads API keys and webhook URL from the `.env` file.
2. **File Management**: Creates and updates the `active_pairs_no_usd.txt` file in the script directory.
3. **Price Monitoring**: Checks price movements for significant changes and detects "wicked out of range" events.
4. **Notifications**: Sends notifications to the console (with timestamps) and to Discord (without timestamps).
5. **Historical Data**: Displays percentage change over the last configured interval with corresponding emojis.
6. **Volatile Text**: Allows adding configurable text to notifications when significant price movements are detected.
7. **Debug Mode**: Shows detailed data being pulled if `DEBUG` is set to `True`.
8. **Initial Alert Message**: Shows a one-time message after the script starts, explaining the initialization period.

## Revisions

### Revision 1: Release (2024-08-16)
- Created the initial version of the script to monitor cryptocurrency pairs for significant price movements.
- Added environment setup using dotenv to load API keys and webhook URL.
- Implemented automatic updates for the `active_pairs_no_usd.txt` file every 60 minutes.
- Integrated retry logic for API requests to handle connection errors.
- Added "wicked out of range" detection for significant market movements.
- Configured the script to print timestamps in console logs but exclude them from Discord notifications.
- Tracked historical data to show the last 15-minute percentage change with emojis.
- Added customizable `VOLATILE_TEXT` for notifications.
- Enabled `DEBUG` mode for detailed data output.

### Revision 2: Update (2024-08-18)
- Added a post-initialization message to notify users that the initialization period has passed.
- Improved notification formatting to ensure the correct placement of emojis based on price changes.
- Added logic to track and store the most recent pair prices in memory, ensuring notifications are only triggered if the price moves beyond the `NOTIFICATION_THRESHOLD`.

## Future Considerations

- **Database Support**: Potentially adding database support if in-memory storage becomes insufficient.
- **Additional Intervals**: Exploring additional time intervals for price monitoring.
- **Enhanced Logging**: Adding more detailed error logging and notifications for better diagnostics.
