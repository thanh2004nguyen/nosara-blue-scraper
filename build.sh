#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

echo "Build completed successfully!"
