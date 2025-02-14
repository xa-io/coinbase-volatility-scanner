"""
# Coinbase Advance Volatility Watcher

# This script monitors cryptocurrency pairs for significant price movements and sends notifications to Discord.
# It fetches and updates active USD trading pairs from Coinbase Advance, creating or updating the active_pairs_no_usd.txt file as needed.
# The script checks for price movements every `FETCH_INTERVAL` seconds by default and updates the list of active pairs every `UPDATE_INTERVAL_MINUTES` minutes.

# Setup:
- Install the required dependencies: `pip install requests python-dotenv`.
- Create a `.env` file in the same directory as this script with the following variables:
  - COINBASE_API_KEY=your_api_key
  - COINBASE_API_SECRET=your_api_secret
  - DISCORD_WEBHOOK_URL=your_discord_webhook_url
- The script will automatically create and update the `active_pairs_no_usd.txt` file based on active USD trading pairs.
- Adjust the configuration variables in the script to fit your needs, such as `FETCH_INTERVAL`, `HISTORY_RETENTION_MINUTES`, `HISTORICAL_INTERVAL_MINUTES`, `VOLATILE_TEXT`, `USE_DISCORD_WEBHOOK`, and `DEBUG` mode.
- Run the script in your preferred Python environment using `python range_puller.py`.
- Monitor the console for output or check your Discord channel for notifications.

# Script Overview:
1. **Environment Setup**: Loads API keys and webhook URL from the `.env` file.
2. **File Management**: Creates and updates the `active_pairs_no_usd.txt` file in the same directory as the script.
3. **Price Monitoring**: Checks price movements for significant changes and detects "wicked out of range" events.
4. **Notifications**: Sends notifications to the console (with timestamps) and to Discord (without timestamps).
5. **Historical Data**: Displays the percentage change over the last configured interval (e.g., `HISTORICAL_INTERVAL_MINUTES`) alongside the current price change, with corresponding emojis.
6. **Volatile Text**: Allows for adding configurable text to notifications when significant price movements are detected.
7. **Debug Mode**: Shows detailed data being pulled from `fetch_prices(pairs)` if `DEBUG` is set to `True`.
8. **Initial Alert Message**: Shows a one-time message "Scanner has been updated, please allow {HISTORICAL_INTERVAL_MINUTES} minutes for accurate longer term accuracy." right after the script starts.
9. **Post-Initialization Message**: Notifies users that the initialization period has passed, ensuring all subsequent data is accurate.
10. **Notification Cooldown**: Controls how frequently notifications can be sent for the same pair and applies a multiplier to the threshold during cooldown.

# Revision 1: Release (2024-08-16):
  - Created the initial version of the script to monitor cryptocurrency pairs for significant price movements.
  - Implemented environment setup using dotenv to load API keys and webhook URL.
  - Added functionality to fetch and update the active_pairs_no_usd.txt file every 60 minutes.
  - Integrated retry logic for API requests to handle connection errors gracefully.
  - Implemented "wicked out of range" detection to spot significant market movements.
  - Configured the script to print timestamps in console logs but exclude them from Discord notifications.
  - Ensured the active_pairs_no_usd.txt file is created and updated within the script directory.
  - Added historical data tracking to show the last 15-minute percentage change with emojis.
  - Added a configurable VOLATILE_TEXT for notifications.
  - Added a USE_DISCORD_WEBHOOK config to control whether Discord notifications are sent.
  - Enhanced DEBUG mode to show detailed data being pulled from fetch_prices(pairs).
  - Added a one-time initial message to notify users about the 15-minute accuracy wait.

# Revision 2: Update (2024-08-18):
- Added a post-initialization message to notify users that the initialization period has passed, ensuring all subsequent data is accurate.
- Improved notification formatting to ensure the correct placement of emojis based on price changes.
- Added logic to track and store the most recent pair prices in memory, ensuring notifications are only triggered if the price moves beyond the `NOTIFICATION_THRESHOLD`.

# Revision 3: Update (2024-08-21):
- Converted time-related settings from minutes to hours:
  - `HISTORY_RETENTION_MINUTES` and `HISTORICAL_INTERVAL_MINUTES` updated to 4 hours (240 minutes).
  - `UPDATE_INTERVAL_MINUTES` updated to 6 hours (360 minutes).
- Updated the initial alert and post-initialization messages to reflect the new hourly intervals.
- Updated notification formatting to display intervals as hours (e.g., `[4hr +5.94%]` instead of `[60m +5.94%]`).

# Revision 4: Update (2024-12-10):
- Updated for new Coinbase API endpoints:
  - Transitioned from the deprecated pro.coinbase.com endpoint to the new Coinbase Advanced Trade endpoint. 
  - Replaced the old products URL (https://api.pro.coinbase.com/products) with the new URL (https://api.exchange.coinbase.com/products).
  - Ensured compatibility with the updated format and fields returned by the new Coinbase Advanced Trade API.

# Revision 5: Update (2025-02-11):
- Introduced logic to skip failing pairs for a configurable period (`SKIP_FAILED_PAIRS_MINUTES`) whenever they hit `RETRY_ATTEMPTS` consecutive failures.
- The script now continues to fetch prices and send notifications for other pairs even if one pair fails multiple times.
- Implemented `FAIL_COUNT` and `NEXT_ALLOWED_FETCH` dictionaries to track failures and skip periods, ensuring that a single failing pair does not halt scanning for all pairs.
- Added a new setting `SKIP_FAILED_PAIRS_MINUTES` to control how long (in minutes) a failed pair is skipped after exhausting all `RETRY_ATTEMPTS`.

# Revision 6: Update (2025-02-13):
- **Reduced Data Retention**: 
  - Updated `update_price_history()` to store only the last **5 minutes** of data for short-term high/low detection, plus **one** data point from ~24 hours ago for historical comparison.
  - Significantly lowers memory usage and `price_history.json` size by removing thousands of older data points per pair.
- **Safe JSON Writing**:
  - Implemented a temporary file approach (`.tmp`) in `save_price_history()` to prevent corruption of `price_history.json` if the script is interrupted mid-write.
  - Renames (or replaces) the temp file only after a successful write, ensuring the old JSON remains intact if an error occurs.
- **Other Logic Unchanged**:
  - Preserves the existing skip logic for failing pairs, threshold notifications, and "wicked out of range" detection.
  - Continues to fetch pairs from `active_pairs_no_usd.txt` and send Discord alerts if `USE_DISCORD_WEBHOOK` is enabled.

# Future Considerations:
- Potentially adding database support if in-memory storage becomes insufficient.
- Exploring additional time intervals for price monitoring beyond the current `FETCH_INTERVAL` and `UPDATE_INTERVAL_MINUTES`.
- Enhancing the script with more detailed error logging and notifications for better diagnostics.
"""

import os
import re
import time
import json
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

#########################
# Configuration variables
#########################
DEBUG = False                           # Set to True for console-only output; set to False for Discord notifications
USE_DISCORD_WEBHOOK = True              # Set to False to disable sending notifications to Discord
FETCH_INTERVAL = 15                     # Time in seconds between each price fetch
RETRY_ATTEMPTS = 5                      # Number of retry attempts per API call
SKIP_FAILED_PAIRS_MINUTES = 5           # Time in minutes to skip a pair if it fails RETRY_ATTEMPTS times
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PAIRS_FILE = os.path.join(SCRIPT_DIR, "active_pairs_no_usd.txt")

# Notification settings
NOTIFICATION_THRESHOLD = 2
WICK_MULTIPLIER = 3
NOTIFICATION_COOLDOWN = 5
NOTIFICATION_COOLDOWN_MULTIPLIER = 2

# Data retention
HISTORY_RETENTION_MINUTES = 1440  # 24 hours
HISTORICAL_INTERVAL_MINUTES = 1440

# Update interval setting
UPDATE_INTERVAL_MINUTES = 30  # 30 minutes to rescan for active pairs

# Initial alert settings
SHOW_INITIAL_ALERT = True
INITIAL_ALERT_MESSAGE = f"Scanner has been updated, please allow {HISTORICAL_INTERVAL_MINUTES // 60} hours for accurate longer term accuracy."
POST_INITIALIZATION_MESSAGE = (
    f"Initialization period of {HISTORICAL_INTERVAL_MINUTES // 60} hours has passed. "
    "All data moving forward will be accurate."
)

VOLATILE_TEXT = ""

# Data storage dictionaries
PRICE_HISTORY = {}
LAST_NOTIFIED = {}
LAST_NOTIFICATION_TIME = {}
LAST_PRICES = {}

# Formatting settings
PAIR_LENGTH = 11
PERCENT_LENGTH = 7
PRICE_LENGTH = 10
HISTORICAL_LENGTH = 13

# Fail/skip logic
FAIL_COUNT = {}
NEXT_ALLOWED_FETCH = {}

load_dotenv()
API_KEY = os.getenv("COINBASE_API_KEY")
API_SECRET = os.getenv("COINBASE_API_SECRET")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

###################################
# JSON SAVE / LOAD PRICE_HISTORY
###################################
PRICE_HISTORY_FILE = os.path.join(SCRIPT_DIR, "price_history.json")

def save_price_history():
    """
    Save PRICE_HISTORY to a temporary file, then atomically rename it
    to avoid corrupting price_history.json if interrupted mid-write.
    """
    serializable_data = {}
    for pair, records in PRICE_HISTORY.items():
        # Convert (datetime, price) -> (timestamp, price)
        serializable_data[pair] = [(ts.timestamp(), price) for (ts, price) in records]

    temp_file = PRICE_HISTORY_FILE + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, indent=2)
        os.replace(temp_file, PRICE_HISTORY_FILE)
    except Exception as e:
        print(f"Error saving {temp_file}: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)

def load_price_history():
    """
    Load PRICE_HISTORY from JSON if it exists, otherwise start fresh.
    If the JSON is corrupted, we'll also start fresh.
    """
    global PRICE_HISTORY
    if not os.path.exists(PRICE_HISTORY_FILE):
        print(f"{PRICE_HISTORY_FILE} not found. Starting fresh with empty PRICE_HISTORY.")
        return
    
    try:
        with open(PRICE_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        loaded_history = {}
        for pair, records in data.items():
            loaded_history[pair] = [
                (datetime.fromtimestamp(ts, timezone.utc), price)
                for (ts, price) in records
            ]
        PRICE_HISTORY = loaded_history
        print(f"Loaded PRICE_HISTORY from {PRICE_HISTORY_FILE}.")
    except Exception as e:
        print(f"Failed to load {PRICE_HISTORY_FILE}. Starting fresh. Error: {e}")
        PRICE_HISTORY = {}

def load_pairs(file_path):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f.readlines()]

def update_active_pairs():
    """Fetch active USD pairs from Coinbase and update local pairs file if changed."""
    url = "https://api.exchange.coinbase.com/products"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Coinbase Exchange API: {e}")
        return
    
    products = response.json()
    # Filter out only USD pairs that are not disabled
    usd_pairs = [p for p in products if p.get('quote_currency') == 'USD' and not p.get('trading_disabled')]

    # Extract base currencies
    current_active_pairs_no_usd = sorted(p.get('base_currency') for p in usd_pairs if 'base_currency' in p)

    # Load previous pairs from file
    previous_active_pairs_no_usd = set()
    try:
        with open(PAIRS_FILE, "r") as file:
            previous_active_pairs_no_usd = set(file.read().splitlines())
    except FileNotFoundError:
        print(f"{PAIRS_FILE} not found, creating a new one.")

    if set(current_active_pairs_no_usd) != previous_active_pairs_no_usd:
        with open(PAIRS_FILE, "w") as file:
            for pair in current_active_pairs_no_usd:
                file.write(pair + "\n")
        print(f"{PAIRS_FILE} has been updated with traded pairs without the '-USD' suffix.")
    else:
        print(f"No changes in active pairs. {PAIRS_FILE} remains the same.")

def fetch_prices(pairs):
    """Fetch spot prices with retry logic and skip failing pairs."""
    prices = {}
    start_time = time.time()

    for pair in pairs:
        skip_until = NEXT_ALLOWED_FETCH.get(pair, 0)
        if time.time() < skip_until:
            prices[pair] = None
            continue

        success = False
        for attempt in range(RETRY_ATTEMPTS):
            try:
                # Use a timeout to prevent indefinite hangs
                response = requests.get(f"https://api.coinbase.com/v2/prices/{pair}-USD/spot", timeout=10)
                response.raise_for_status()
                data = response.json()
                prices[pair] = float(data['data']['amount'])
                FAIL_COUNT[pair] = 0
                success = True
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
                print(f"Error fetching price for {pair}: {e}")
                time.sleep(2)

        if not success:
            FAIL_COUNT[pair] = FAIL_COUNT.get(pair, 0) + 1
            prices[pair] = None
            if FAIL_COUNT[pair] >= RETRY_ATTEMPTS:
                NEXT_ALLOWED_FETCH[pair] = time.time() + SKIP_FAILED_PAIRS_MINUTES * 60
                print(f"Pair {pair} failed {FAIL_COUNT[pair]} times. Skipping for {SKIP_FAILED_PAIRS_MINUTES} minutes.")
        else:
            NEXT_ALLOWED_FETCH[pair] = 0

    end_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching prices took {end_time - start_time:.2f} seconds.")

    if DEBUG:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] DEBUG: Fetched prices: {prices}")

    return prices

def update_price_history(prices):
    """
    Append new prices for each pair, but store:
      - ALL data points from the last 5 minutes (for high/low detection)
      - The earliest data point from ~24 hours ago, if it exists
      This approach drastically reduces the total stored data.
    """
    current_time = datetime.now(timezone.utc)
    five_min_cutoff = current_time - timedelta(minutes=5)
    full_day_cutoff = current_time - timedelta(minutes=HISTORY_RETENTION_MINUTES)

    for pair, price in prices.items():
        if price is None:
            continue

        if pair not in PRICE_HISTORY:
            PRICE_HISTORY[pair] = []

        # Add the new data point
        PRICE_HISTORY[pair].append((current_time, price))

        # Filter out everything older than 24 hours
        data_24hr = [(ts, p) for (ts, p) in PRICE_HISTORY[pair] if ts >= full_day_cutoff]

        # Sort by timestamp
        data_24hr.sort(key=lambda x: x[0])

        # We'll keep:
        #   - All points newer than 5 minutes ago
        #   - If there's any points older than 5 min but within 24 hours, keep only the earliest one
        #     to use as the "historical" data point.
        # Everything else is discarded.
        final_list = [(ts, p) for (ts, p) in data_24hr if ts >= five_min_cutoff]

        # If there's at least one point < five_min_cutoff in data_24hr, keep the earliest
        older_points = [(ts, p) for (ts, p) in data_24hr if ts < five_min_cutoff]
        if older_points:
            # The earliest point in data_24hr is older than 5 min
            earliest_24hr_point = older_points[0]  # They are sorted
            # Insert it at the front, so it's the oldest in final_list
            final_list.insert(0, earliest_24hr_point)

        PRICE_HISTORY[pair] = final_list

def check_price_movements():
    """
    Check for significant price movements using the last 5 min data
    for max/min detection, plus the earliest 24-hour point for historical difference.
    """
    notifications = []
    current_time = datetime.now(timezone.utc)
    historical_interval = timedelta(minutes=HISTORICAL_INTERVAL_MINUTES)

    for pair, history in PRICE_HISTORY.items():
        if len(history) == 0:
            continue

        # The last 5 minutes data is everything except possibly the first item if that is from 24 hr
        # But we'll just gather by current_time - 5min:
        recent_cutoff = current_time - timedelta(minutes=5)
        recent_prices = [price for (ts, price) in history if ts >= recent_cutoff]

        if not recent_prices:
            continue

        initial_price = recent_prices[0]
        current_price = recent_prices[-1]
        high_price = max(recent_prices)
        low_price = min(recent_prices)
        percentage_change = ((current_price - initial_price) / initial_price) * 100 if initial_price != 0 else 0

        # For the 24-hour data, we want the earliest entry that is still in PRICE_HISTORY
        # Because we stored at most 1 data point older than 5 min, that is effectively the earliest in the last 24 hr
        # But let's keep consistent with the logic:
        historical_cutoff = current_time - historical_interval
        # We'll find any that are >= historical_cutoff
        historical_prices = [price for (ts, price) in history if ts >= historical_cutoff]
        if historical_prices:
            historical_initial_price = historical_prices[0]  # The earliest in that list
            historical_percentage_change = ((current_price - historical_initial_price) / historical_initial_price) * 100 if historical_initial_price != 0 else 0
        else:
            historical_percentage_change = 0

        # Cooldown logic
        last_notification_time = LAST_NOTIFICATION_TIME.get(pair, None)
        if last_notification_time:
            time_since_last = (current_time - last_notification_time).total_seconds() / 60
            if (time_since_last < NOTIFICATION_COOLDOWN and
                abs(percentage_change - LAST_NOTIFIED.get(pair, 0)) < NOTIFICATION_THRESHOLD * NOTIFICATION_COOLDOWN_MULTIPLIER):
                continue

        # Enough movement from last?
        last_price = LAST_PRICES.get(pair, None)
        if last_price is not None:
            movement_from_last = ((current_price - last_price) / last_price) * 100 if last_price != 0 else 0
            if abs(movement_from_last) < NOTIFICATION_THRESHOLD:
                continue

        # Update last known price
        LAST_PRICES[pair] = current_price

        # Check "wick" detection
        wicked = False
        if high_price > initial_price * (1 + WICK_MULTIPLIER * NOTIFICATION_THRESHOLD / 100):
            wicked = True
            notifications.append(format_notification(pair, percentage_change, current_price, historical_percentage_change, VOLATILE_TEXT))
        elif low_price < initial_price * (1 - WICK_MULTIPLIER * NOTIFICATION_THRESHOLD / 100):
            wicked = True
            notifications.append(format_notification(pair, percentage_change, current_price, historical_percentage_change, VOLATILE_TEXT))

        if abs(percentage_change) >= NOTIFICATION_THRESHOLD and not wicked:
            notifications.append(format_notification(pair, percentage_change, current_price, historical_percentage_change))
            LAST_NOTIFIED[pair] = percentage_change
            LAST_NOTIFICATION_TIME[pair] = current_time

    return notifications

def format_notification(pair, change, current_price, historical_change, extra_info=""):
    emoji = get_emoji(change)
    sign = "🔹" if change > 0 else "🔸"
    historical_emoji = get_emoji(historical_change)
    historical_sign = "🔹" if historical_change > 0 else "🔸"
    historical_info = f"[{HISTORICAL_INTERVAL_MINUTES // 1440}d {'+' if historical_change > 0 else ''}{historical_change:.2f}%]"

    pair_display = f"[{pair}]".center(PAIR_LENGTH)
    percent_display = f"{change:+.2f}%".ljust(PERCENT_LENGTH)
    price_display = f"${current_price:.5f}".center(PRICE_LENGTH)
    historical_display = f"{historical_info}".rjust(HISTORICAL_LENGTH)

    message_console = f"{sign}{emoji}\t{percent_display}\t{pair_display}\t{price_display}\t{historical_display}{historical_emoji}{historical_sign}"
    message_discord = f"{sign}{emoji}`{percent_display}{pair_display}{price_display}{historical_display}`{historical_emoji}{historical_sign}[{pair}](<https://www.coinbase.com/advanced-trade/spot/{pair}-USD>)"

    if extra_info:
        message_console += f" ({extra_info})"
        message_discord += f" ({extra_info})"

    return message_console, message_discord

def get_emoji(change):
    """Return an emoji representing how big the percentage change is."""
    val = abs(change)
    if val < 1:
        return "▪️"
    elif val < 2:
        return "◼"
    elif val < 3:
        return "🟩"
    elif val < 4:
        return "🟦"
    elif val < 5:
        return "🟪"
    elif val < 6:
        return "🟨"
    elif val < 7:
        return "🟧"
    elif val < 8:
        return "🟫"
    elif val < 9:
        return "🟥"
    else:
        return "💥"

def send_notifications(notifications):
    """Batch console + Discord notifications."""
    if notifications:
        for notification in notifications:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message_console, _ = notification
            print(f"[{timestamp}] {message_console}")
        if USE_DISCORD_WEBHOOK and not DEBUG:
            batched_message = "\n".join(n[1] for n in notifications)
            send_to_discord(batched_message)

def send_to_discord(message):
    data = {"content": message}
    requests.post(WEBHOOK_URL, json=data)

def main():
    global SHOW_INITIAL_ALERT
    last_update_time = time.time() - UPDATE_INTERVAL_MINUTES * 60
    initialization_time = time.time() + HISTORICAL_INTERVAL_MINUTES * 60
    initialization_posted = False

    # Load saved PRICE_HISTORY (if any) before main loop
    load_price_history()

    if SHOW_INITIAL_ALERT:
        print(INITIAL_ALERT_MESSAGE)
        if USE_DISCORD_WEBHOOK:
            send_to_discord(INITIAL_ALERT_MESSAGE)
        SHOW_INITIAL_ALERT = False

    while True:
        try:
            current_time = time.time()
            if current_time - last_update_time >= UPDATE_INTERVAL_MINUTES * 60:
                update_active_pairs()
                last_update_time = current_time

            pairs = load_pairs(PAIRS_FILE)
            prices = fetch_prices(pairs)
            update_price_history(prices)      # Only keep last 5 min + earliest 24 hr
            notifications = check_price_movements()
            send_notifications(notifications)

            # Safely save to avoid JSON corruption
            save_price_history()

            if not initialization_posted and current_time >= initialization_time:
                print(POST_INITIALIZATION_MESSAGE)
                if USE_DISCORD_WEBHOOK:
                    send_to_discord(POST_INITIALIZATION_MESSAGE)
                initialization_posted = True

            time.sleep(FETCH_INTERVAL)

        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] An error occurred: {e}")

if __name__ == "__main__":
    main()
