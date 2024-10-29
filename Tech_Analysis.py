import pandas as pd
import pandas_ta as ta
import yfinance as yf

# Download historical stock data for demonstration
def get_stock_data(ticker, period="1y", interval="1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval)
        if df.empty:
            raise ValueError(f"No data returned for ticker '{ticker}'.")
        return df
    except Exception as e:
        print(f"Failed to get ticker '{ticker}' due to: {e}")
        return None

# Calculate indicators and generate buy/sell signals
def calculate_indicators(df):
    # MACD
    df['MACD'], df['Signal'], df['MACD_Hist'] = ta.macd(df['Close'], fast=12, slow=26, signal=9)

    # EMA
    df['EMA_9'] = ta.ema(df['Close'], length=9)
    df['EMA_21'] = ta.ema(df['Close'], length=21)

    # VWAP (Volume Weighted Average Price)
    df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])

    # RSI
    df['RSI'] = ta.rsi(df['Close'], length=14)

    return df

# Define strategies for buy and sell signals
def generate_signals(df):
    signals = []

    for i in range(1, len(df)):
        buy_signal = False
        sell_signal = False

        # MACD Strategy
        if df['MACD'].iloc[i] > df['Signal'].iloc[i] and df['MACD'].iloc[i - 1] <= df['Signal'].iloc[i - 1]:
            buy_signal = True
        elif df['MACD'].iloc[i] < df['Signal'].iloc[i] and df['MACD'].iloc[i - 1] >= df['Signal'].iloc[i - 1]:
            sell_signal = True

        # EMA Crossover Strategy
        if df['EMA_9'].iloc[i] > df['EMA_21'].iloc[i] and df['EMA_9'].iloc[i - 1] <= df['EMA_21'].iloc[i - 1]:
            buy_signal = True
        elif df['EMA_9'].iloc[i] < df['EMA_21'].iloc[i] and df['EMA_9'].iloc[i - 1] >= df['EMA_21'].iloc[i - 1]:
            sell_signal = True

        # VWAP Strategy
        if df['Close'].iloc[i] > df['VWAP'].iloc[i]:
            buy_signal = True
        elif df['Close'].iloc[i] < df['VWAP'].iloc[i]:
            sell_signal = True

        # RSI Strategy
        if df['RSI'].iloc[i] < 30:  # Oversold
            buy_signal = True
        elif df['RSI'].iloc[i] > 70:  # Overbought
            sell_signal = True

        # Append the combined signal for each row
        signals.append({
            "Date": df.index[i],
            "Buy Signal": buy_signal,
            "Sell Signal": sell_signal
        })

    return pd.DataFrame(signals)

# Main function to run the entire analysis
def analyze_stock(ticker):
    # Get stock data
    df = get_stock_data(ticker)
    if df is None:
        return None  # Return None if data retrieval fails

    # Calculate indicators
    df = calculate_indicators(df)
    # Generate signals
    signals = generate_signals(df)
    return signals

# Example usage
if __name__ == "__main__":
    ticker = "ZOMATO"  # Change to a valid ticker if necessary
    signals = analyze_stock(ticker)
    if signals is not None:
        print(signals)
    else:
        print("No signals generated due to data retrieval failure.")
