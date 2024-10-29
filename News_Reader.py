import os
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import random
import time
from concurrent.futures import ThreadPoolExecutor

from Stocks import NSE_500_stocks

# Set environment variable to disable parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Initialize VADER sentiment analyzer
analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(news_text):
    if news_text.strip():
        try:
            sentiment = analyzer.polarity_scores(news_text)
            if sentiment['compound'] >= 0.05:
                return 'positive'
            elif sentiment['compound'] <= -0.05:
                return 'negative'
            else:
                return 'neutral'
        except Exception as e:
            print(f"Error during sentiment analysis: {e}")
            return None
    return None


# The rest of your functions remain unchanged...

async def fetch_page(url, driver):
    try:
        driver.get(url)
        time.sleep(random.uniform(1, 2))  # Shorter wait time
        html = driver.page_source
        return html
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def extract_news_links(soup):
    """Extract news links."""
    news_links = []
    for a in soup.find_all("a", href=True):
        if "article" in a['href']:  # Modify condition based on site structure
            news_links.append(a['href'])
    return news_links


async def process_news(url, stock_mentions, driver):
    html = await fetch_page(url, driver)
    if html:
        soup = BeautifulSoup(html, "lxml")
        news_links = extract_news_links(soup)

        # Limit nested page fetching to 10
        tasks = []
        for news_url in news_links[:30]:  # Take only the first 10 links
            tasks.append(fetch_and_analyze(news_url, stock_mentions, driver))

        await asyncio.gather(*tasks)  # Run all sentiment analysis tasks concurrently


async def fetch_and_analyze(news_url, stock_mentions, driver):
    """Fetch news article and analyze its sentiment."""
    driver.execute_script("window.open(arguments[0]);", news_url)  # Open in a new tab
    driver.switch_to.window(driver.window_handles[-1])  # Switch to the new tab
    time.sleep(random.uniform(1, 2))  # Short wait for loading

    news_html = driver.page_source
    news_soup = BeautifulSoup(news_html, "lxml")
    news_text = " ".join(p.text for p in news_soup.find_all("p"))

    if news_text and len(news_text) > 512:
        news_text = news_text[:512]

    # Perform sentiment analysis in a separate thread
    sentiment_label = await asyncio.get_event_loop().run_in_executor(ThreadPoolExecutor(), analyze_sentiment, news_text)

    # Check if sentiment analysis returned a label
    if sentiment_label:
        for stock in NSE_500_stocks:
            if stock in news_text:
                print(f"Found mention of {stock} in {news_url} with sentiment: {sentiment_label}")
                if sentiment_label == "positive":
                    stock_mentions[stock]["score"] += 1
                elif sentiment_label == "negative":
                    stock_mentions[stock]["score"] -= 1

    driver.close()  # Close the tab after processing
    driver.switch_to.window(driver.window_handles[0])  # Switch back to the original window


async def scrape_news(urls):
    stock_mentions = {stock: {"score": 0} for stock in NSE_500_stocks}

    # Set up the Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run headless
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--window-size=1920x1080")  # Set the window size
    chrome_options.add_argument("--disable-extensions")  # Disable extensions to improve performance
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        tasks = [process_news(url, stock_mentions, driver) for url in urls]
        await asyncio.gather(*tasks)
    finally:
        driver.quit()  # Close the browser after processing

    return stock_mentions


# Example URLs (replace with actual news URLs)
urls = [
    "https://pulse.zerodha.com/",
    "https://www.business-standard.com/markets",
    "https://www.moneycontrol.com/news/business/stocks/",
    "https://economictimes.indiatimes.com/markets/stocks?from=mdr"
    "https://www.livemint.com/market",
    "https://www.bqprime.com/markets",
    "https://www.tradingview.com/news/",
    "https://www.benzinga.com/",
]

if __name__ == "__main__":
    stock_mentions = asyncio.run(scrape_news(urls))

    # Print results
    top_positive = {stock: data["score"] for stock, data in stock_mentions.items() if data["score"] > 1}
    top_negative = {stock: data["score"] for stock, data in stock_mentions.items() if data["score"] < -1}

    print("\nTop Positive Stocks:")
    for stock, score in top_positive.items():
        print(f"{stock}: {score} score")

    print("\nTop Negative Stocks:")
    for stock, score in top_negative.items():
        print(f"{stock}: {score} score")
