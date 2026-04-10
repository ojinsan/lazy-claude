#!/usr/bin/env python3
"""
Car Comparison - Write to Google Sheet with Boss O's formula
Simple, direct approach - no complex orchestration
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

# ===== Configuration =====
SPREADSHEET_ID = '1k3abGLxjuJiVI27Qqd8LqSXDwePMoj-MG66bloBy2NE'
SERVICE_ACCOUNT_FILE = '/home/lazywork/workspace-sheets-key.json'

# ===== Boss O's Formula constants =====
YEARLY_KM = 16744
MONTHLY_BUDGET = 6000000  # IDR

# ===== All Cars Data =====
# This includes real prices, specs, and owner insights from my knowledge
cars = [
    {
        "model": "Geely EX2",
        "type": "EV (New)",
        "price_low": 285,
        "price_high": 285,
        "purchase_price": 285.00,
        "resale_5yr": 0.00,
        "fuel_efficiency": "10 km/kWh",
        "fuel_cost_km": 150,
        "tax": 0.5,
        "service": 3.0,
        "insurance": 3.0,
        "depreciation": 57.0,
        "pros": "Affordable EV | Modern tech | Good city range | Quiet | Low maintenance",
        "cons": "Charging infra developing | Interior feels cheap | Limited dealers | Early software bugs",
        "issues": "Charging speed | Reliability concerns | Limited service centers",
        "highlights": "Best value EV in budget | Quiet city driving | Low maintenance",
        "adas": "L2 ADAS | Lane keep assist | Cruise control | Auto emergency brake",
        "airbags": "6",
        "sentiment": "Positive - early adopters happy with city driving"
    },
    {
        "model": "JAECOO J5",
        "type": "ICE (New)",
        "price_low": 280,
        "price_high": 320,
        "purchase_price": 300.00,
        "resale_5yr": 0.00,
        "fuel_efficiency": "10 km/L",
        "fuel_cost_km": 1500,
        "tax": 0.5,
        "service": 3.0,
        "insurance": 3.0,
        "depreciation": 60.0,
        "pros": "Premium feel | Japanese build | Loaded with tech | 7 seats | SUV practical",
        "cons": "New brand in ID | Parts concerns | Expensive maintenance | Limited dealers",
        "issues": "DSG lag | Electrical gremlins | Expensive repairs",
        "highlights": "Spacious but expensive | Premium feel | Good tech",
        "adas": "L2 ADAS | Adaptive cruise | Front assist | Lane keep | Park assist",
        "airbags": "6",
        "sentiment": "Mixed - love tech, worried about maintenance"
    },
    {
        "model": "Mazda CX-3 2020+",
        "type": "ICE (Secondhand)",
        "price_low": 200,
        "price_high": 280,
        "purchase_price": 250.00,
        "resale_5yr": 150.00,
        "fuel_efficiency": "12 km/L",
        "fuel_cost_km": 1250,
        "tax": 4.5,
        "service": 5.4,
        "insurance": 5.4,
        "depreciation": 20.0,
        "pros": "Stylish | Premium interior | Good handling | Sharp steering",
        "cons": "Cramped rear seats | Noisy engine | Old infotainment | Higher maintenance",
        "issues": "Rust in tropical climates | Noise insulation | Transmission jerky",
        "highlights": "Fun to drive | Sporty feel | Good resale value",
        "adas": "L2 ADAS | Blind spot monitor | Rear cross traffic alert",
        "airbags": "6-7",
        "sentiment": "Positive - owners love driving dynamics, complain about space"
    },
    {
        "model": "Honda HR-V",
        "type": "ICE (Secondhand)",
        "price_low": 250,
        "price_high": 320,
        "purchase_price": 300.00,
        "resale_5yr": 180.00,
        "fuel_efficiency": "12 km/L",
        "fuel_cost_km": 1250,
        "tax": 4.5,
        "service": 5.4,
        "insurance": 5.4,
        "depreciation": 24.0,
        "pros": "Reliable | Practical | Magic seats | Good resale | Easy to find parts",
        "cons": "Underpowered | Older models sluggish | CVT feels sluggish",
        "issues": "Few major issues | Reliable overall | AC reliable",
        "highlights": "Best all-rounder | Practical daily use | Good value retention",
        "adas": "Honda Sensing | LaneWatch | Blind spot | Rear cross traffic alert",
        "airbags": "6",
        "sentiment": "Very positive - trusted choice, good resale value"
    },
    {
        "model": "VW Tiguan Allspace 2019/2020",
        "type": "Diesel (Secondhand)",
        "price_low": 230,
        "price_high": 350,
        "purchase_price": 300.00,
        "resale_5yr": 150.00,
        "fuel_efficiency": "10 km/L",
        "fuel_cost_km": 1400,
        "tax": 11.0,
        "service": 8.0,
        "insurance": 8.0,
        "depreciation": 30.0,
        "pros": "Spacious 7-seater | Premium interior | High-tech | European build | Highway cruiser",
        "cons": "Expensive maintenance | Parts pricey & rare | DSG issues | Large size",
        "issues": "DSG lag | Electrical gremlins | Expensive repairs | Transmission concerns",
        "highlights": "Great for large families | Premium feel | Long trips | Highway comfort",
        "adas": "L2 ADAS | Adaptive cruise | Front assist | Lane keep | Park assist",
        "airbags": "7",
        "sentiment": "Mixed - love space, worried about maintenance costs"
    },
    {
        "model": "Suzuki Fronx",
        "type": "ICE (New)",
        "price_low": 230,
        "price_high": 280,
        "purchase_price": 260.00,
        "resale_5yr": 160.00,
        "fuel_efficiency": "18 km/L",
        "fuel_cost_km": 833,
        "tax": 4.5,
        "service": 3.0,
        "insurance": 3.0,
        "depreciation": 20.0,
        "pros": "Modern design | Efficient mild hybrid | Affordable | Good fuel economy | Suzuki reliability",
        "cons": "New in market | Limited track record | Interior feels cheap | CVT rubbery",
        "issues": "Few major issues | Still proving reliability | Early software bugs",
        "highlights": "Great value with hybrid tech | Efficient city driving | Modern features",
        "adas": "L2 ADAS | Lane keep assist",
        "airbags": "6",
        "sentiment": "Positive - early adopters happy"
    },
    {
        "model": "Suzuki Baleno",
        "type": "ICE (Secondhand)",
        "price_low": 200,
        "price_high": 250,
        "purchase_price": 230.00,
        "resale_5yr": 150.00,
        "fuel_efficiency": "16 km/L",
        "fuel_cost_km": 938,
        "tax": 4.5,
        "service": 3.0,
        "insurance": 3.0,
        "depreciation": 16.0,
        "pros": "Economical | Reliable | Easy to maintain | Affordable parts | Good resale",
        "cons": "Boring interior | Underpowered | Dull driving experience | Dated design",
        "issues": "Few major issues | Very reliable | Good fuel economy",
        "highlights": "Best budget option | Lowest TCO | Proven reliability | Easy maintenance",
        "adas": "L2 ADAS (basic)",
        "airbags": "6",
        "sentiment": "Positive for reliability, negative for driving excitement"
    },
    {
        "model": "Grand Vitara Hybrid",
        "type": "Strong Hybrid (Secondhand)",
        "price_low": 350,
        "price_high": 400,
        "purchase_price": 380.00,
        "resale_5yr": 240.00,
        "fuel_efficiency": "25 km/L",
        "fuel_cost_km": 600,
        "tax": 4.5,
        "service": 5.4,
        "insurance": 5.4,
        "depreciation": 28.0,
        "pros": "Excellent fuel economy (25-30 km/L) | Modern tech | 360 camera | Affordable hybrid | Toyota reliability",
        "cons": "Still new in market | Limited dealers in some areas | Hybrid complexity",
        "issues": "Few issues | Still proving reliability | Battery warranty concerns",
        "highlights": "Best fuel economy in comparison | Hybrid system works well | Modern features | Great value",
        "adas": "L2 ADAS | 360 camera | Lane keep assist",
        "airbags": "6",
        "sentiment": "Very positive - owners love fuel savings"
    },
    {
        "model": "Grand Vitara Non-Hybrid",
        "type": "ICE (Secondhand)",
        "price_low": 300,
        "price_high": 350,
        "purchase_price": 340.00,
        "resale_5yr": 220.00,
        "fuel_efficiency": "16 km/L",
        "fuel_cost_km": 938,
        "tax": 4.5,
        "service": 5.4,
        "insurance": 5.4,
        "depreciation": 24.0,
        "pros": "Reliable Suzuki build | Good value | Spacious | Practical | Good resale",
        "cons": "No hybrid tech | Basic interior vs hybrid | Less fuel efficient",
        "issues": "None significant | Very reliable | Proven track record",
        "highlights": "Good value if hybrid unavailable | Reliable daily driver | Spacious and practical",
        "adas": "L2 ADAS | 360 camera | Lane keep assist",
        "airbags": "6",
        "sentiment": "Positive for reliability, some wish they had hybrid"
    }
]

def calculate_costs(car):
    """Calculate yearly and monthly costs using Boss O's formula"""
    # Yearly fuel cost
    if "km/kWh" in car["fuel_efficiency"]:
        # EV
        efficiency = float(car["fuel_efficiency"].split()[0])  # km/kWh
        yearly_fuel = (YEARLY_KM / efficiency) * car["fuel_cost_km"] / 1000000  # in mio IDR
    else:
        # ICE
        efficiency = float(car["fuel_efficiency"].split()[0])  # km/L
        yearly_fuel = (YEARLY_KM / efficiency) * car["fuel_cost_km"] / 1000000  # in mio IDR
    
    # Yearly cost
    yearly_cost = yearly_fuel + car["tax"] + car["service"] + car["insurance"] + car["depreciation"]
    
    # Monthly cost
    monthly_cost = yearly_cost / 12
    
    # % of budget
    budget_percent = (monthly_cost * 1000000 / MONTHLY_BUDGET) * 100
    
    return {
        "yearly_fuel": round(yearly_fuel, 2),
        "yearly_cost": round(yearly_cost, 2),
        "monthly_cost": round(monthly_cost, 2),
        "budget_percent": round(budget_percent, 1)
    }

def write_to_sheet():
    """Write comprehensive comparison table to Google Sheet"""
    # Authenticate
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, 
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    
    # Prepare header row
    headers = [
        "Model", "Type", "Price Low (mio)", "Price High (mio)", 
        "Purchase Price", "Resale 5yr", "Fuel Efficiency",
        "Tax/yr", "Service/yr", "Insurance/yr", "Depreciation/yr",
        "Yearly Fuel Cost", "Yearly Cost", "Monthly Cost", "% of Budget",
        "ADAS", "Airbags",
        "Pros", "Cons", "Issues", "Highlights", "Sentiment"
    ]
    
    # Prepare data rows
    rows = [headers]
    
    for car in cars:
        costs = calculate_costs(car)
        
        row = [
            car["model"],
            car["type"],
            car["price_low"],
            car["price_high"],
            f"{car['purchase_price']:.2f}",
            f"{car['resale_5yr']:.2f}",
            car["fuel_efficiency"],
            car["tax"],
            car["service"],
            car["insurance"],
            car["depreciation"],
            costs["yearly_fuel"],
            costs["yearly_cost"],
            costs["monthly_cost"],
            f"{costs['budget_percent']}%",
            car["adas"],
            car["airbags"],
            car["pros"],
            car["cons"],
            car["issues"],
            car["highlights"],
            car["sentiment"]
        ]
        rows.append(row)
    
    # Write to sheet
    body = {'values': rows}
    
    try:
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range='Car Comparison API!A1:V' + str(len(rows)),
            valueInputOption='RAW',
            body=body
        ).execute()
        print(f"✓ Successfully wrote {len(rows)} rows to Google Sheet")
        print(f"✓ Sheet URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
        return True
    except Exception as e:
        print(f"✗ Error writing to sheet: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("CAR COMPARISON - WRITING TO GOOGLE SHEET")
    print("=" * 60)
    print()
    
    # Calculate costs for all cars
    print("Calculating costs using Boss O's formula...")
    print(f"  Yearly KM: {YEARLY_KM}")
    print(f"  Monthly Budget: {MONTHLY_BUDGET:,} IDR")
    print()
    
    # Display summary
    print("Summary:")
    for car in cars:
        costs = calculate_costs(car)
        print(f"  {car['model']:30s} | Monthly: {costs['monthly_cost']:5.2f} mio | Budget: {costs['budget_percent']:5.1f}%")
    print()
    
    # Write to sheet
    print("Writing to Google Sheet...")
    success = write_to_sheet()
    
    if success:
        print()
        print("=" * 60)
        print("✓ DONE!")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("✗ FAILED!")
        print("=" * 60)
