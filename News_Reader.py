import os
import asyncio
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from concurrent.futures import ThreadPoolExecutor
from Stocks import NSE_100_stocks

# Set environment variable to disable parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Initialize VADER sentiment analyzer
analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(news_text):
    if news_text.strip():
        sentiment = analyzer.polarity_scores(news_text)
        if sentiment['compound'] >= 0.05:
            return 'positive'
        elif sentiment['compound'] <= -0.05:
            return 'negative'
        else:
            return 'neutral'
    return None


async def fetch_page(url, driver):
    try:
        driver.get(url)
        await asyncio.sleep(random.uniform(2, 3))  # Wait for page to load
        return driver.page_source
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def extract_news_links(soup):
    news_links = []
    for a in soup.find_all("a", href=True):
        if "article" in a['href'] or "news" in a['href']:
            news_links.append(a['href'])
    return list(set(news_links))  # Remove duplicates


async def process_news(url, stock_mentions, driver):
    html = await fetch_page(url, driver)
    if html:
        soup = BeautifulSoup(html, "lxml")
        news_links = extract_news_links(soup)

        tasks = [fetch_and_analyze(news_url, stock_mentions, driver) for news_url in news_links[:30]]
        await asyncio.gather(*tasks)


async def fetch_and_analyze(news_url, stock_mentions, driver):
    try:
        driver.execute_script("window.open(arguments[0]);", news_url)
        driver.switch_to.window(driver.window_handles[-1])
        await asyncio.sleep(random.uniform(2, 3))

        news_html = driver.page_source
        news_soup = BeautifulSoup(news_html, "lxml")

        # Improved headline extraction
        headline = news_soup.find('h1')
        if headline is None:
            headline = news_soup.find('title')  # Fallback to <title> tag
        headline_text = headline.text.strip() if headline else "No headline found"
        print(f"Processing headline: {headline_text}")

        # Extract article content
        paragraphs = news_soup.find_all("p")
        news_text = " ".join(p.text for p in paragraphs if p.text).strip()

        # Check if news text is too short
        if len(news_text) < 50:  # Skip if too short
            print(f"Skipping analysis for {news_url}: content too short.")
            return

        if news_text and len(news_text) > 512:
            news_text = news_text[:512]

        print(f"Analyzing text: {news_text}")

        # Perform sentiment analysis in a thread pool
        sentiment_label = await asyncio.get_event_loop().run_in_executor(ThreadPoolExecutor(), analyze_sentiment, news_text)

        if sentiment_label:
            for stock in NSE_100_stocks:
                if stock in news_text:
                    if sentiment_label == "positive":
                        stock_mentions[stock]["score"] += 1
                        stock_mentions[stock]["headlines"].append(headline_text)
                    elif sentiment_label == "negative":
                        stock_mentions[stock]["score"] -= 1
                        stock_mentions[stock]["headlines"].append(headline_text)
        else:
            print(f"No sentiment detected for {news_url}.")

    except Exception as e:
        print(f"Error processing {news_url}: {e}")
    finally:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

async def scrape_news(urls):
    stock_mentions = {stock: {"score": 0, "headlines": []} for stock in NSE_100_stocks}

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-extensions")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        await asyncio.gather(*(process_news(url, stock_mentions, driver) for url in urls))
        print_results(stock_mentions)
    finally:
        driver.quit()


def print_results(stock_mentions):
    top_positive = {stock: data for stock, data in stock_mentions.items() if data["score"] > 0}
    top_negative = {stock: data for stock, data in stock_mentions.items() if data["score"] < 0}

    print("\nTop Positive Stocks:")
    if top_positive:
        for stock, data in top_positive.items():
            print(f"{stock}: {data['score']} score, Headlines: {data['headlines']}")
    else:
        print("No positive stocks found.")

    print("\nTop Negative Stocks:")
    if top_negative:
        for stock, data in top_negative.items():
            print(f"{stock}: {data['score']} score, Headlines: {data['headlines']}")
    else:
        print("No negative stocks found.")


# Example URLs (replace with actual news URLs)
urls = [
    "https://economictimes.indiatimes.com/markets/stocks?from=mdr",
    "https://www.livemint.com/market",
    "https://www.ndtvprofit.com/markets?src=topnav"
    "https://pulse.zerodha.com/"
]

if __name__ == "__main__":
    asyncio.run(scrape_news(urls))
