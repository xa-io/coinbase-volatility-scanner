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

# Future Considerations:
- Potentially adding database support if in-memory storage becomes insufficient.
- Exploring additional time intervals for price monitoring beyond the current `FETCH_INTERVAL` and `UPDATE_INTERVAL_MINUTES`.
- Enhancing the script with more detailed error logging and notifications for better diagnostics.
"""

import os
import time
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("COINBASE_API_KEY")
API_SECRET = os.getenv("COINBASE_API_SECRET")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Configuration variables

# General settings
DEBUG = False  # Set to True for console-only output; set to False for Discord notifications
USE_DISCORD_WEBHOOK = True  # Set to False to disable sending notifications to Discord
FETCH_INTERVAL = 15  # Time in seconds between each price fetch
RETRY_ATTEMPTS = 5  # Number of retry attempts for API calls if a connection fails
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))  # Directory where the script is located
PAIRS_FILE = os.path.join(SCRIPT_DIR, "active_pairs_no_usd.txt")  # Ensure the file is created in the script's directory

# Notification settings
NOTIFICATION_THRESHOLD = 1  # Minimum percentage change required to trigger a notification
WICK_MULTIPLIER = 3  # Multiplier for detecting "wicked out of range" events
NOTIFICATION_COOLDOWN = 5  # Time in minutes before another notification can be sent for the same pair
NOTIFICATION_COOLDOWN_MULTIPLIER = 2  # Multiplier for applying to NOTIFICATION_THRESHOLD during cooldown

# Historical data settings
HISTORY_RETENTION_MINUTES = 60  # Time in minutes to retain price history for each pair
HISTORICAL_INTERVAL_MINUTES = 60  # Time in minutes to calculate historical percentage change

# Update interval setting
UPDATE_INTERVAL_MINUTES = 300  # Time in minutes to check and update the active pairs

# Initial alert settings
SHOW_INITIAL_ALERT = True  # Set to False to skip the initial alert message when the script starts
INITIAL_ALERT_MESSAGE = f"Scanner has been updated, please allow {HISTORICAL_INTERVAL_MINUTES} minutes for accurate longer term accuracy."  # Custom initial message
POST_INITIALIZATION_MESSAGE = f"Initialization period of {HISTORICAL_INTERVAL_MINUTES} minutes has passed. All data moving forward will be accurate."  # Custom message after initialization period

# Volatility text
VOLATILE_TEXT = ""  # Text to use in volatile notifications, set to empty string for now

# Data storage dictionaries
PRICE_HISTORY = {}  # Dictionary to store price history for each pair
LAST_NOTIFIED = {}  # Dictionary to store the last percentage change notified for each pair
LAST_NOTIFICATION_TIME = {}  # Dictionary to store the last notification time for each pair
LAST_PRICES = {}  # Dictionary to store the most recent prices for each pair

# Formatting settings
PAIR_LENGTH = 11  # Total characters for pair names, including brackets
PERCENT_LENGTH = 7  # Total characters for percentage changes
PRICE_LENGTH = 10  # Total characters for price, including the dollar sign
HISTORICAL_LENGTH = 13  # Total characters for historical data

# Function to load currency pairs from the file
def load_pairs(file_path):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f.readlines()]

# Function to fetch USD pairs and create/update active_pairs_no_usd.txt
def update_active_pairs():
    url = "https://api.pro.coinbase.com/products"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Coinbase Pro API: {e}")
        return
    
    products = response.json()
    # Filter out only USD pairs
    usd_pairs = [product for product in products if product['quote_currency'] == 'USD' and not product['trading_disabled']]
    
    # Remove '-USD' from each traded pair and sort them alphabetically
    current_active_pairs_no_usd = sorted(pair['base_currency'] for pair in usd_pairs)
    
    # Load previous pairs from file
    previous_active_pairs_no_usd = set()
    try:
        with open(PAIRS_FILE, "r") as file:
            previous_active_pairs_no_usd = set(file.read().splitlines())
    except FileNotFoundError:
        print(f"{PAIRS_FILE} not found, creating a new one.")
    
    # Check if the file needs to be updated
    if set(current_active_pairs_no_usd) != previous_active_pairs_no_usd:
        with open(PAIRS_FILE, "w") as file:
            for pair in current_active_pairs_no_usd:
                file.write(pair + "\n")
        print(f"{PAIRS_FILE} has been updated with traded pairs without the '-USD' suffix.")
    else:
        print(f"No changes in active pairs. {PAIRS_FILE} remains the same.")

# Function to fetch current spot prices from Coinbase API with retry logic
def fetch_prices(pairs):
    prices = {}
    for pair in pairs:
        for attempt in range(RETRY_ATTEMPTS):
            try:
                response = requests.get(f"https://api.coinbase.com/v2/prices/{pair}-USD/spot")
                response.raise_for_status()
                data = response.json()
                prices[pair] = float(data['data']['amount'])
                break  # Exit loop if successful
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
                print(f"Error fetching price for {pair}: {e}")
                if attempt < RETRY_ATTEMPTS - 1:
                    print(f"Retrying... ({attempt + 1}/{RETRY_ATTEMPTS})")
                    time.sleep(2)  # Wait before retrying
                else:
                    print(f"Failed to fetch price for {pair} after {RETRY_ATTEMPTS} attempts.")
                    prices[pair] = None

    if DEBUG:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] DEBUG: Fetched prices: {prices}")  # Print all prices in one large data pull with a timestamp

    return prices

# Function to update the price history and track highs and lows for each pair
def update_price_history(prices):
    current_time = datetime.now(timezone.utc)
    retention_period = timedelta(minutes=HISTORY_RETENTION_MINUTES)
    for pair, price in prices.items():
        if price is None:
            continue  # Skip pairs that failed to fetch
        if pair not in PRICE_HISTORY:
            PRICE_HISTORY[pair] = []
        PRICE_HISTORY[pair].append((current_time, price))
        # Remove data older than the configured HISTORY_RETENTION_MINUTES
        PRICE_HISTORY[pair] = [
            (timestamp, p) for timestamp, p in PRICE_HISTORY[pair]
            if timestamp > current_time - retention_period
        ]

# Function to check for significant price movements and "wicked out of range" events
def check_price_movements():
    notifications = []
    current_time = datetime.now(timezone.utc)
    historical_interval = timedelta(minutes=HISTORICAL_INTERVAL_MINUTES)
    
    for pair, history in PRICE_HISTORY.items():
        if len(history) > 0:
            initial_time = current_time - timedelta(minutes=5)
            recent_prices = [price for timestamp, price in history if timestamp >= initial_time]
            if len(recent_prices) > 0:
                initial_price = recent_prices[0]
                current_price = recent_prices[-1]
                high_price = max(recent_prices)
                low_price = min(recent_prices)
                percentage_change = ((current_price - initial_price) / initial_price) * 100

                # Calculate the historical percentage change over the configured interval
                historical_prices = [price for timestamp, price in history if timestamp >= current_time - historical_interval]
                if historical_prices:
                    historical_initial_price = historical_prices[0]
                    historical_percentage_change = ((current_price - historical_initial_price) / historical_initial_price) * 100
                else:
                    historical_percentage_change = 0

                # Check if the pair has been notified recently and apply cooldown logic
                last_notification_time = LAST_NOTIFICATION_TIME.get(pair, None)
                if last_notification_time:
                    time_since_last_notification = (current_time - last_notification_time).total_seconds() / 60  # convert to minutes
                    if time_since_last_notification < NOTIFICATION_COOLDOWN and abs(percentage_change - LAST_NOTIFIED.get(pair, 0)) < NOTIFICATION_THRESHOLD * NOTIFICATION_COOLDOWN_MULTIPLIER:
                        continue  # Skip if within cooldown and the percentage change is not significant

                # Check if the price has significantly moved since last notification
                last_price = LAST_PRICES.get(pair, None)
                if last_price:
                    movement_from_last = ((current_price - last_price) / last_price) * 100
                    if abs(movement_from_last) < NOTIFICATION_THRESHOLD:
                        continue  # Skip if movement from the last notification is not significant

                # Update the last prices dictionary with the current price
                LAST_PRICES[pair] = current_price

                # Detect significant highs or lows (wicked out of range events)
                wicked = False
                if high_price > initial_price * (1 + WICK_MULTIPLIER * NOTIFICATION_THRESHOLD / 100):
                    wicked = True
                    notifications.append(format_notification(pair, percentage_change, current_price, historical_percentage_change, VOLATILE_TEXT))
                elif low_price < initial_price * (1 - WICK_MULTIPLIER * NOTIFICATION_THRESHOLD / 100):
                    wicked = True
                    notifications.append(format_notification(pair, percentage_change, current_price, historical_percentage_change, VOLATILE_TEXT))

                if abs(percentage_change) >= NOTIFICATION_THRESHOLD and not wicked:
                    notifications.append(format_notification(pair, percentage_change, current_price, historical_percentage_change))
                    LAST_NOTIFIED[pair] = percentage_change  # Update last notified percentage change
                    LAST_NOTIFICATION_TIME[pair] = current_time  # Update last notification time
    return notifications

# Function to format the notification messages
def format_notification(pair, change, current_price, historical_change, extra_info=""):
    emoji = get_emoji(change)
    sign = "🔹" if change > 0 else "🔸"
    historical_emoji = get_emoji(historical_change)
    historical_sign = "🔹" if historical_change > 0 else "🔸"
    historical_info = f"[{HISTORICAL_INTERVAL_MINUTES}m {'+' if historical_change > 0 else ''}{historical_change:.2f}%]"

    # Pad the pair name to the desired length
    pair_display = f"[{pair}]".center(PAIR_LENGTH)
    
    # Pad the percentage change to the desired length
    percent_display = f"{change:+.2f}%".ljust(PERCENT_LENGTH)
    
    # Determine the price display and pad it to the desired length
    price_display = f"${current_price:.5f}".center(PRICE_LENGTH)
    
    # Pad the historical info to the desired length
    historical_display = f"{historical_info}".rjust(HISTORICAL_LENGTH)
    
    # Create the message string for console 
    message_console = f"{sign}{emoji}\t{percent_display}\t{pair_display}\t{price_display}\t{historical_display}{historical_emoji}{historical_sign}"
    
    # Create the message string for Discord with backticks around the main content
    message_discord = f"{sign}{emoji}`{percent_display}{pair_display}{price_display}{historical_display}`{historical_emoji}{historical_sign}[{pair}](<https://www.coinbase.com/advanced-trade/spot/{pair}-USD>)"
    
    # Add extra info like "wicked out of range" if applicable
    if extra_info:
        message_console += f" ({extra_info})"
        message_discord += f" ({extra_info})"
        
    return message_console, message_discord

# Function to determine which emoji to use based on the percentage change
def get_emoji(change):
    if abs(change) < 1:
        return "▪️"
    elif abs(change) < 2:
        return "◼"
    elif abs(change) < 3:
        return "🟫"
    elif abs(change) < 4:
        return "🟪"
    elif abs(change) < 5:
        return "🟦"
    elif abs(change) < 6:
        return "🟩"
    elif abs(change) < 7:
        return "🟨"
    elif abs(change) < 8:
        return "🟧"
    elif abs(change) < 9:
        return "🟥"
    else:
        return "💥"

# Function to send notifications either to the console or Discord
def send_notifications(notifications):
    if notifications:
        for notification in notifications:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message_console, message_discord = notification
            print(f"[{timestamp}] {message_console}")  # Console output with timestamp
        if USE_DISCORD_WEBHOOK and not DEBUG:
            batched_message = "\n".join([msg[1] for msg in notifications])
            send_to_discord(batched_message)  # Discord notification without timestamp

# Function to send the message to a Discord channel via webhook
def send_to_discord(message):
    data = {"content": message}
    requests.post(WEBHOOK_URL, json=data)

# Main loop of the script
def main():
    global SHOW_INITIAL_ALERT
    last_update_time = time.time() - UPDATE_INTERVAL_MINUTES * 60  # Convert minutes to seconds for time calculations
    initialization_time = time.time() + HISTORICAL_INTERVAL_MINUTES * 60  # End time for the initialization period
    initialization_posted = False  # To track if the post-initialization message has been posted

    # Show the initial alert message only once when the script starts
    if SHOW_INITIAL_ALERT:
        print(INITIAL_ALERT_MESSAGE)
        if USE_DISCORD_WEBHOOK:
            send_to_discord(INITIAL_ALERT_MESSAGE)
        SHOW_INITIAL_ALERT = False

    while True:
        current_time = time.time()
        if current_time - last_update_time >= UPDATE_INTERVAL_MINUTES * 60:
            update_active_pairs()  # Update active pairs every configured interval
            last_update_time = current_time

        pairs = load_pairs(PAIRS_FILE)
        prices = fetch_prices(pairs)
        update_price_history(prices)
        notifications = check_price_movements()
        send_notifications(notifications)

        # Post the initialization complete message once the period has passed
        if not initialization_posted and current_time >= initialization_time:
            print(POST_INITIALIZATION_MESSAGE)
            if USE_DISCORD_WEBHOOK:
                send_to_discord(POST_INITIALIZATION_MESSAGE)
            initialization_posted = True

        time.sleep(FETCH_INTERVAL)

# Entry point of the script
if __name__ == "__main__":
    main()
