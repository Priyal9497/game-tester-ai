#!/usr/bin/env bash
set -o errexit

echo "=== Installing system dependencies ==="
apt-get update -qq
apt-get install -y wget gnupg unzip curl

echo "=== Installing Google Chrome ==="
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
apt-get update -qq
apt-get install -y google-chrome-stable

echo "=== Chrome version ==="
google-chrome --version

echo "=== Installing ChromeDriver ==="
CHROME_MAJOR=$(google-chrome --version | grep -oP '\d+' | head -1)
echo "Chrome major version: $CHROME_MAJOR"

# Download ChromeDriver for Chrome 115+
CHROMEDRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/$(curl -s https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE)/linux64/chromedriver-linux64.zip"
wget -q "$CHROMEDRIVER_URL" -O chromedriver.zip
unzip -q chromedriver.zip
mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
chmod +x /usr/local/bin/chromedriver

echo "=== ChromeDriver version ==="
chromedriver --version

echo "=== Installing Python packages ==="
pip install -r requirements.txt

echo "=== Build Complete! ==="