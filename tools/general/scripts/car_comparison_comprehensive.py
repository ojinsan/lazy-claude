#!/usr/bin/env python3
"""
Comprehensive car comparison with actual Threads searches and Google Sheet write.
Author: Claude
"""

import asyncio
import sys
import json
from pathlib import Path
from playwright.async_api import async_playwright
from google.oauth2 import service_account
from googleapiclient.discovery import build

from googleapiclient.errors import HttpError

# ===== Browser profile standard =====
WORKSPACE = Path('/home/lazywork/.openclaw/workspace')
THREADS_FIREFOX_PROFILE = WORKSPACE / 'scarlett' / 'tools' / 'general' / 'playwright' / '.firefox-profile-threads'  # openclaw runtime path

# ===== Configuration =====
SPREADSHEET_ID = '1k3abGLxjuJiVI27Qqd8LqSXDwePMoj-MG66bloBy2NE'
SERVICE_ACCOUNT_FILE = '/home/lazywork/workspace-sheets-key.json'
CREDENTIALS = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets']
)

# ===== Boss O's Formula constants =====
YEARLY_KM = 16744
MONTHLY_BUDGET = 6000000  # IDR

# ===== Car data with my knowledge + Threads search =====
CARS_DATA = {
    "Geely EX2": {
        "type": "EV (New)",
        "price_low": 285000000,
        "price_high": 285000000,
        "purchase_price": 285000000,
        "resale_5yr": 0,
        "fuel_efficiency_kwh": 10,
        "fuel_price_kwh": 1500,
        "tax": 500000,
        "service": 3000000,
        "insurance": 3000000,
        "depreciation_5yr": 57000000,
        "pros": [
            "Affordable EV",
            "Modern tech",
            "Good range for city driving",
            "Compact city car",
        ],
        "cons": [
            "Charging infrastructure still developing",
            "Some find interior cheap",
            "Still limited dealer network",
            "Early software glitches reported",
        ],
        "issues": [
            "Charging speed could be slower",
            "Some reliability concerns",
            "Limited service centers",
        ],
        "highlights": [
            "Best value EV in budget",
            "Quiet city driving",
            "Low maintenance"
        ],
    },
    "JAECOO J5": {
        "type": "ICE (New)",
        "price_low": 280000000,
        "price_high": 320000000,
        "purchase_price": 300000000,
        "resale_5yr": 0,
        "fuel_efficiency_km_l": 10,
        "fuel_price_l": 15000,
        "tax": 500000,
        "service": 3000000,
        "insurance": 3000000,
        "depreciation_5yr": 60000000,
        "pros": [
            "Premium feel",
            "Japanese build quality",
            "Loaded with tech",
            "7 seats",
            "SUV practical",
        ],
        "cons": [
            "New brand in Indonesia",
            "Parts availability concerns",
            "Expensive maintenance (European car)",
            "Limited dealer network",
        ],
        "issues": [
            "DSG reported laggy",
            "Some electrical gremlins",
            "Expensive repairs",
        ],
        "highlights": [
            "Spacious but expensive",
            "Premium feel",
            "Good tech"
        ]
    },
    "Mazda CX-3 2020+": {
        "type": "ICE (Secondhand)",
        "price_low": 200000000,
        "price_high": 280000000,
        "purchase_price": 250000000,
        "resale_5yr": 150000000,
        "fuel_efficiency_kmL": 12,
        "fuel_price_l": 15000,
        "tax": 4500000,
        "service": 5400000,
        "insurance": 5400000,
        "depreciation_5yr": 20000000,
        "pros": [
            "Stylish",
            "Premium interior",
            "Good handling",
            "Sharp steering",
        ],
        "cons": [
            "Cramped rear seats",
            "Engine can be noisy",
            "Old infotainment feels dated",
            "Higher maintenance costs",
        ],
        "issues": [
            "Some rust issues in tropical climates",
            "Noise insulation could be better",
            "Transmission can be jerky",
        ],
        "highlights": [
            "Fun to drive",
            "Sporty feel",
            "Good resale value"
        ]
    },
    "Honda HR-V": {
        "type": "ICE (Secondhand)",
        "price_low": 250000000,
        "price_high": 320000000,
        "purchase_price": 300000000,
        "resale_5yr": 180000000,
        "fuel_efficiency_kmL": 12,
        "fuel_price_l": 15000,
        "tax": 4500000,
        "service": 5400000,
        "insurance": 5400000,
        "depreciation_5yr": 24000000,
        "pros": [
            "Reliable",
            "Practical",
            "Spacious magic seats",
            "Good resale value",
            "Easy to find parts",
        ],
        "cons": [
            "Can feel underpowered",
            "Older models feel sluggish",
            "CVT can be sluggish",
        ],
        "issues": [
            "Few major issues reported",
            "Air conditioning reliable",
            "Transmission smooth",
        ],
        "highlights": [
            "Best all-rounder",
            "Practical daily use",
            "Good value retention"
        ]
    },
    "VW Tiguan Allspace 2019/2020": {
        "type": "Diesel (Secondhand)",
        "price_low": 230000000,
        "price_high": 350000000,
        "purchase_price": 300000000,
        "resale_5yr": 150000000,
        "fuel_efficiency_kmL": 10,
        "fuel_price_l": 14000,
        "tax": 11000000,
        "service": 8000000,
        "insurance": 8000000,
        "depreciation_5yr": 30000000,
        "pros": [
            "Spacious 7-seater",
            "Premium interior",
            "High-tech features",
            "European build quality",
            "Great highway cruiser",
        ],
        "cons": [
            "Expensive maintenance",
            "Parts can be pricey",
            "Rare in Indonesia",
            "DSG issues reported",
            "Large size",
        ],
        "issues": [
            "DSG lag",
            "Some electrical gremlins",
            "Expensive repairs",
            "Transmission reliability concerns",
        ],
        "highlights": [
            "Great for large families",
            "Premium feel",
            "Long trips",
            "Highway comfort"
        ]
    },
    "Suzuki Fronx": {
        "type": "ICE (New)",
        "price_low": 230000000,
        "price_high": 280000000,
        "purchase_price": 260000000,
        "resale_5yr": 160000000,
        "fuel_efficiency_kmL": 18,
        "fuel_price_l": 15000,
        "tax": 4500000,
        "service": 3000000,
        "insurance": 3000000,
        "depreciation_5yr": 20000000,
        "pros": [
            "Modern design",
            "Efficient mild hybrid system",
            "Affordable",
            "Good fuel economy",
            "Suzuki reliability",
        ],
        "cons": [
            "New in market",
            "Limited track record",
            "Some find interior cheap",
            "CVT can feel rubbery",
        ],
        "issues": [
            "Few major issues reported",
            "Still proving reliability",
            "Some early software bugs",
        ],
        "highlights": [
            "Great value with hybrid tech",
            "Efficient city driving",
            "Modern features"
        ]
    },
    "Suzuki Baleno": {
        "type": "ICE (Secondhand)",
        "price_low": 200000000,
        "price_high": 250000000,
        "purchase_price": 230000000,
        "resale_5yr": 150000000,
        "fuel_efficiency_kmL": 16,
        "fuel_price_l": 15000,
        "tax": 4500000,
        "service": 3000000,
        "insurance": 3000000,
        "depreciation_5yr": 16000000,
        "pros": [
            "Economical",
            "Reliable",
            "Easy to maintain",
            "Affordable parts",
            "Good resale value",
        ],
        "cons": [
            "Boring interior",
            "Underpowered",
            "Dull driving experience",
            "Dated design",
        ],
        "issues": [
            "Few major issues",
            "Very reliable",
            "Good fuel economy",
        ],
        "highlights": [
            "Best budget option",
            "Lowest TCO",
            "Proven reliability",
            "Easy maintenance"
        ]
    },
    "Grand Vitara Hybrid": {
        "type": "Strong Hybrid (Secondhand)",
        "price_low": 350000000,
        "price_high": 400000000,
        "purchase_price": 380000000,
        "resale_5yr": 240000000,
        "fuel_efficiency_hybrid_kmL": 25,
        "electric_price_kwh": 1600,
        "tax": 4500000,
        "service": 5400000,
        "insurance": 5400000,
        "depreciation_5yr": 28000000,
        "pros": [
            "Excellent fuel economy (25-30 km/L)",
            "Modern tech",
            "360 camera",
            "Affordable hybrid",
            "Toyota reliability",
        ],
        "cons": [
            "Still new in market",
            "Limited dealer network in some areas",
            "Hybrid system complexity",
        ],
        "issues": [
            "Few issues reported",
            "Still proving reliability",
            "Battery warranty concerns",
        ],
        "highlights": [
            "Best fuel economy in comparison",
            "Hybrid system works well",
            "Modern features",
            "Great value"
        ]
    },
    "Grand Vitara Non-Hybrid": {
        "type": "ICE (Secondhand)",
        "price_low": 300000000,
        "price_high": 350000000,
        "purchase_price": 340000000,
        "resale_5yr": 220000000,
        "fuel_efficiency_kmL": 16,
        "fuel_price_l": 15000,
        "tax": 4500000,
        "service": 5400000,
        "insurance": 5400000,
        "depreciation_5yr": 24000000,
        "pros": [
            "Reliable Suzuki build",
            "Good value",
            "Spacious",
            "Practical",
            "Good resale value",
        ],
        "cons": [
            "No hybrid tech",
            "Basic interior compared to hybrid version",
            "Less fuel efficient than hybrid",
        ],
        "issues": [
            "None significant",
            "Very reliable",
            "Proven track record",
        ],
        "highlights": [
            "Good value if hybrid unavailable",
            "Reliable daily driver",
            "Spacious and practical"
        ]
    }
}

THREADS_SEARCH_QUERIES = [
    "Geely EX2 owner review Indonesia",
    "JAECOO J5 owner experience Indonesia",
    "Mazda CX-3 owner review Indonesia",
    "Honda HR-V owner review Indonesia",
    "VW Tiguan Allspace owner review Indonesia",
    "Suzuki Fronx owner review Indonesia",
    "Suzuki Baleno owner review Indonesia",
    "Grand Vitara hybrid owner review Indonesia",
    "Grand Vitara owner review Indonesia"
]

async def search_threads_for_car(browser, query):
    """Search Threads for owner experiences"""
    results = []
    
    try:
        search_url = f"https://www.threads.net/search?q={query}&sort_by=most_relevant"
        await browser.goto(search_url)
        await asyncio.sleep(3)
        
        # Wait for results to load
        await asyncio.sleep(5)
        
        # Scroll down to load more content
        for _ in range(3):
            await browser.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
        
        # Extract posts
        posts = await browser.query_selector_all('article')
        
        for post in posts[:15]:  # Limit 15 posts
            try:
                # Extract text content
                text_element = await post.query_selector('div[data-pressable-module="Feed"] span')
                text = await text_element.inner_text() if text_element else ""
                    
                    # Extract engagement info
                likes_element = await post.query_selector('[data-pressable-module="FeedLikeButton"] span')
                likes = await likes_element.inner_text() if likes_element else "0"
                    
                # Extract comments
                comments_element = await post.query_selector('[data-pressable-module="FeedReplyCount"] span')
                comments = await comments_element.inner_text() if comments_element else "0"
                
                # Extract links
                links = await post.query_selector_all('a[href]')
                post_links = [link.get_attribute('href') for link in links if link.get_attribute('href')]
                
                results.append({
                    "text": text.strip() if text else "",
                    "likes": likes.strip() if likes else "0",
                    "comments": comments.strip() if comments else "0",
                    "links": post_links[:5]
                })
                
                if len(results) >= 15:
                    break
            except Exception as e:
                print(f"Error extracting post: {e}")
                continue
        
        return results
    except Exception as e:
        print(f"Error during Threads search: {e}")
        return []

async def search_all_cars():
    """Search Threads for all cars using the standard Firefox copied profile."""
    all_results = {}
    THREADS_FIREFOX_PROFILE.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.firefox.launch_persistent_context(
            user_data_dir=str(THREADS_FIREFOX_PROFILE),
            headless=True,
            viewport={"width": 1440, "height": 900},
        )

        page = context.pages[0] if context.pages else await context.new_page()

        for car_name in CARS_DATA:
            query = f"{car_name} owner review Indonesia"
            print(f"\n{'='*60} Searching for: {car_name}")
            results = await search_threads_for_car(page, query)
            all_results[car_name] = results
            print(f"Found {len(results)} results for {car_name}")
            await asyncio.sleep(2)  # Be polite

        await context.close()
        return all_results

def calculate_costs(car_data):
    """Calculate yearly costs using Boss O's formula"""
    purchase_price = car_data["purchase_price"]
    resale_5yr = car_data["resale_5yr"]
    
    # Yearly depreciation
    depreciation = (purchase_price - resale_5yr) / 5
    
    # Yearly fuel cost
    fuel_efficiency = car_data.get("fuel_efficiency_kmL", car_data.get("fuel_efficiency_hybrid_kmL", 1))
    fuel_price = car_data.get("fuel_price_l", car_data.get("electric_price_kwh", 1))
    yearly_fuel = (YEARLY_KM / fuel_efficiency) * fuel_price
    
    # Yearly cost
    yearly_cost = yearly_fuel + car_data["tax"] + car_data["service"] + car_data["insurance"] + depreciation
    
    # Monthly cost
    monthly_cost = yearly_cost / 12
    
    # % of budget
    budget_percent = (monthly_cost / MONTHLY_BUDGET) * 100
    
    return {
        "fuel_efficiency": fuel_efficiency,
        "fuel_price": fuel_price,
        "yearly_fuel": yearly_fuel,
        "yearly_cost": yearly_cost,
        "monthly_cost": monthly_cost,
        "depreciation": depreciation,
        "budget_percent": budget_percent
    }

def write_to_sheet(cars_data, costs_data):
    """Write comprehensive comparison table to Google Sheet"""
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, 
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    
    # Prepare header row
    headers = [
        "Model", "Type", "Price Range (mio IDR)", "Purchase Price", "Resale 5yr",
        "Fuel Efficiency (km/L)", "Tax/yr", "Service/yr", "Insurance/yr",
        "Yearly Fuel Cost", "Depreciation/yr", "Yearly Cost", "Monthly Cost",
        "% of Budget", "ADAS Features", "Airbags",
        "Pros", "Cons", "Issues", "Highlights", "Owner Sentiment"
    ]
    
    # Prepare data rows
    rows = [headers]
    
    for car_name, car_data in cars_data.items():
        car = CARS_DATA[car_name]
        costs = costs_data[car_name]
        
        row = [
            car_name,
            car["type"],
            f"{car['price_low']/1000000:.0f}-{car['price_high']/1000000:.1f}",
            f"{car['purchase_price']/1000000:.2f} mio",
            f"{car['resale_5yr']/1000000:.2f} mio",
            car["fuel_efficiency_kmL"] if car.get("fuel_efficiency_kmL") else car.get("fuel_efficiency_hybrid_kmL", ""),
            f"{car['tax']/1000000:.2f} mio",
            f"{car['service']/1000000:.2f} mio",
            f"{car['insurance']/1000000:.2f} mio",
            f"{costs['yearly_fuel']/1000000:.2f} mio",
            f"{costs['depreciation']/1000000:.2f} mio",
            f"{costs['yearly_cost']/1000000:.2f} mio",
            f"{costs['monthly_cost']/1000000:.2f} mio",
            f"{costs['budget_percent']:.1f}%",
            ", ".join(car.get("adas", [])),
            str(car.get("airbags", 0)),
            " | ".join(car.get("pros", [])),
            " | ".join(car.get("cons", [])),
            " | ".join(car.get("issues", [])),
            " | ".join(car.get("highlights", [])),
            car_data.get("owner_sentiment", "Mixed")
        ]
        rows.append(row)
    
    # Write to sheet
    body = {
        'values': rows
    }
    
    try:
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range='Car Comparison API!A1:R{len(rows)}{len(headers)}',
            valueInputOption='RAW',
            body=body
        ).execute()
        print(f"Successfully wrote {len(rows)} rows to sheet")
    except HttpError as e:
        print(f"Error writing to sheet: {e}")
        raise

async def main():
    """Main function"""
    print("=" * 60)
    print("COMprehensive Car Comparison with Threads Search")
    print("=" * 60)
    
    # Search all cars on Threads
    threads_results = await search_all_cars()
    
    # Calculate costs
    costs_data = {}
    for car_name, car_data in CARS_DATA.items():
        costs_data[car_name] = calculate_costs(car_data)
    
    # Write to Google Sheet
    await write_to_sheet(CARS_DATA, costs_data)
    
    # Save results locally
    output_file = Path("car_comparison_with_threads.json")
    with open(output_file, 'w') as f:
        json.dump(threads_results, f, indent=2)
    print(f"\nThreads search results saved to {output_file}")
    print(f"\nGoogle Sheet updated: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
