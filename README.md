# Coinbase Advanced Volatility Watcher

This script monitors cryptocurrency pairs on **Coinbase Advanced** for significant price movements and sends notifications to a Discord channel. It regularly fetches the list of active USD trading pairs, tracks their price changes, and alerts you when notable movements occur.

This script is running 24/7 here: [https://discord.gg/FprzuuWZ7t](https://discord.gg/FprzuuWZ7t)

## Examples

`🔹🟩+2.01%    [BTC]   $107427.57000  [1d +2.03%]🟩🔹BTC`

`🔹🟩+2.14%    [DOGE]   $0.25978  [1d -12.77%]💥🔸DOGE`

`🔸🟫-7.06%    [ETH]   $2465.35500 [1d -21.27%]💥🔸ETH`

`🔹🟫+7.35%   [TOSHI]   $0.00100  [1d +38.37%]💥🔹TOSHI`

## Features

- **Real-Time Price Monitoring**: The script checks cryptocurrency prices at regular intervals and tracks historical price changes.
- **Discord Notifications**: Alerts are sent to a specified Discord channel for significant price movements, with customizable messages.
- **Automatic Pair Updates**: The list of active USD trading pairs is automatically updated every few hours.
- **Price Movement Detection**: Detects and highlights "wicked out of range" events to spot large market swings.
- **Customizable Alerts**: Easily configure thresholds, intervals, and other settings to match your needs.
- **Lightweight Historical Data Storage**: Instead of storing thousands of data points per pair, the script keeps detailed data only for the last 5 minutes (for high/low detection) plus one data point from ~24 hours ago (for historical comparison), greatly reducing memory usage.
- **Safe JSON Writing**: Implements a temporary file approach when writing the `price_history.json` file to avoid corruption if the script is interrupted.
- **Debug Mode**: Optionally print detailed output for troubleshooting by setting `DEBUG = True`.
- **Initial and Post-Initialization Alerts**: Displays one-time messages on startup and after the initialization period so you know when data becomes fully reliable.

## Installation

### Prerequisites

Ensure you have Python installed (tested with **Python 3.12**). If not, download and install it from [python.org](https://www.python.org/downloads/).

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
- `SKIP_FAILED_PAIRS_MINUTES`: The number of minutes to skip a pair after it fails consecutive attempts.
- Other settings (like `UPDATE_INTERVAL_MINUTES`, `VOLATILE_TEXT`, etc.) can be adjusted as needed.

### Step 5: Run the Script

Execute the script in your preferred Python environment:

```bash
python coinbase-volatility-scanner.py
```

### Step 6: Monitor Output

The script will print logs to the console and send notifications to Discord based on the settings you configured.

# Script Overview:

1. **Environment Setup**  
   Loads API keys (`COINBASE_API_KEY`, `COINBASE_API_SECRET`) and the Discord webhook URL (`DISCORD_WEBHOOK_URL`) from a `.env` file. This file should be located in the same directory as the script.

2. **File Management**  
   - Automatically creates and updates an `active_pairs_no_usd.txt` file containing all active USD trading pairs (minus the `-USD` suffix).  
   - Stores short‐term plus minimal 24‐hour price history data in a JSON file (`price_history.json`), ensuring script restarts do not lose important historical information.

3. **Price Monitoring**  
   - Fetches prices for each active pair at configurable intervals (`FETCH_INTERVAL`).  
   - Uses retry logic (`RETRY_ATTEMPTS`) and temporary skip windows (`SKIP_FAILED_PAIRS_MINUTES`) to handle pairs that repeatedly fail to fetch data.  
   - Tracks short‐term price movement using the last 5 minutes of data, plus a single data point from ~24 hours ago for historical comparison.

4. **Notifications**  
   - Sends formatted alerts to both the console (with timestamps) and to a Discord channel (without timestamps) if configured via `USE_DISCORD_WEBHOOK`.  
   - Each alert includes the pair symbol, short‐term percentage change, current price, and a 24‐hour comparison percentage with corresponding emojis.  

5. **Historical Data**  
   - Maintains a rolling 24‐hour window of historical data (`HISTORY_RETENTION_MINUTES`).  
   - Retains all price points within the last 5 minutes for detecting local highs/lows and a single “anchor” point from ~24 hours ago for percent‐change calculation.  
   - Saves and loads data from a JSON file to preserve history across script restarts.

6. **Volatile Text**  
   - Allows you to specify an optional text string (`VOLATILE_TEXT`) to append to alerts, useful for highlighting significant or “wicked” price changes.

7. **Debug Mode**  
   - If `DEBUG = True`, the script prints additional information to the console, including fetched price dictionaries and extended logs of retry attempts.

8. **Initial Alert Message**  
   - On script start, displays a single alert message (e.g. “Scanner has been updated…") both in the console and on Discord, indicating how long until full historical accuracy is established.

9. **Post-Initialization Message**  
   - Once the configured `HISTORICAL_INTERVAL_MINUTES` (often 24 hours) has elapsed, sends a final message acknowledging the script has built a complete rolling history, so further alerts reflect accurate longer-term data.

10. **Notification Cooldown**  
    - Ensures that each pair only triggers a new alert after a minimum cooldown period (`NOTIFICATION_COOLDOWN` in minutes).  
    - Applies an additional threshold multiplier (`NOTIFICATION_COOLDOWN_MULTIPLIER`) to avoid back‐to‐back alerts for small fluctuations after an initial large move.

11. **Block List for Ignored Coins**  
    - Introduces a `BLOCK_LIST` (comma‐separated string) to skip sending alerts for specific coins (e.g. `"IOTX"`).  
    - The script continues fetching prices for these pairs, but does not generate notifications when they meet normal alert conditions.

12. **Fail‐Skip Logic**  
    - Tracks pairs that repeatedly fail to fetch prices (`RETRY_ATTEMPTS`) and temporarily excludes them from requests for `SKIP_FAILED_PAIRS_MINUTES`.  
    - Prevents an endlessly failing pair from blocking or slowing overall scanning.

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

### Revision 3: Update (2024-08-21):
- Converted time-related settings from minutes to hours:
  - `HISTORY_RETENTION_MINUTES` and `HISTORICAL_INTERVAL_MINUTES` updated to 4 hours (240 minutes).
  - `UPDATE_INTERVAL_MINUTES` updated to 6 hours (360 minutes).
- Updated the initial alert and post-initialization messages to reflect the new hourly intervals.
- Updated notification formatting to display intervals as hours (e.g., `[4hr +5.94%]` instead of `[60m +5.94%]`).

### Revision 4: Update (2024-12-10):
- Updated notification on longer timeframes to 1 day (e.g., `[1d +5.94%]` instead of `[4hr +5.94%]`).
- Updated for new Coinbase API endpoints:
  - Transitioned from the deprecated pro.coinbase.com endpoint to the new Coinbase Advanced Trade endpoint. 
  - Replaced the old products URL (https://api.pro.coinbase.com/products) with the new URL (https://api.exchange.coinbase.com/products).
  - Ensured compatibility with the updated format and fields returned by the new Coinbase Advanced Trade API.

### Revision 5: Update (2025-02-11)
- Introduced logic to skip pairs that repeatedly fail to fetch:
  - Added `FAIL_COUNT` and `NEXT_ALLOWED_FETCH` dictionaries to track consecutive failures and enforce a skip window (`SKIP_FAILED_PAIRS_MINUTES`).
  - The script continues scanning other pairs even if one pair fails repeatedly.

### Revision 6: Update (2025-02-13)
- **Reduced Data Retention**:
  - Updated `update_price_history()` to store only detailed data for the last **5 minutes** (for short-term high/low detection) plus **one** data point from approximately **24 hours** ago for historical comparison.
  - This change significantly reduces memory usage and the size of `price_history.json` compared to storing every data point.
- **Safe JSON Writing**:
  - Modified `save_price_history()` to write the price history to a temporary file (with a `.tmp` extension) and then atomically replace the main JSON file using `os.replace()`.
  - This prevents file corruption if the script is interrupted during a write.
- **Overall Stability**:
  - The script now continues scanning and sending alerts even if individual pairs fail repeatedly, thanks to the enhanced skip logic.
  - Retains all core features including real-time monitoring, Discord notifications, and historical data analysis.

### Revision 7: Update (2025-02-26)
- **Block List for Ignored Coins**:  
  - Added a `BLOCK_LIST` configuration option for specifying coins (e.g., `IOTX`) that should be excluded from generating alerts.  
  - The script still fetches and stores price data for these coins, but no notifications will be sent if one of these coins meets the usual movement thresholds.
- **Preserved Core Functionality**:  
  - All existing logic for short-term versus historical data, retry logic, cooldown checks, and JSON data persistence remains unchanged.
- **Example Usage**:  
  - To ignore `IOTX` and `ABC123` in future alerts, set `BLOCK_LIST = "IOTX, ABC123"` in the configuration.  
  - The script will continue tracking prices for those coins, but no alerts will be sent.

## Recommendations On Use

- **Weekly Reboot**: It is recommended to reboot the script once a week. This helps prevent potential memory overload and ensures the script continues to run smoothly without unexpected stops.
- **Monitor Resource Usage**: Keep an eye on your system’s resource usage and adjust `FETCH_INTERVAL` or other settings if necessary to optimize performance.
  
By following these recommendations, you can maintain the stability of the script and ensure that its historical price tracking remains accurate even after restarts.

## Consider a donation after you buy your lambo.

BTC: `bc1qwjy0hl4z9c930kgy4nud2fp0nw8m6hzknvumgg`

ETH: `0x0941D41Cd0Ee81bd79Dbe34840bB5999C124D3F0`

SOL: `4cpdbmmp1hyTAstA3iUYdFbqeNBwjFmhQLfL5bMgf77z`
