# Travel Deal Finder

A Python tool to find award flight sweet spots and check transfer partner compatibility with Amex, Chase, and American Airlines points.

## Features

- **Sweet Spot Database**: Pre-loaded with known award sweet spots (NYC-Madrid, Europe routes)
- **Transfer Partner Check**: Identifies which credit card points can transfer to which airline programs
- **Peak/Off-Peak Detection**: Automatically detects peak season pricing
- **Points Calculator**: Calculates total points needed for multiple passengers
- **Transfer Bonus Tracking**: Template for tracking active transfer bonuses

## Usage

### Basic Search

```bash
python travel_deal_finder.py
```

This runs a default search for:
- Route: NYC → Madrid
- Dates: July 23 - August 13, 2026
- Passengers: 2
- Max Points: 140,000 total (70k per person)
- Cabin: Business Class

### Custom Search

Edit the `main()` function or import the class:

```python
from travel_deal_finder import TravelDealFinder

finder = TravelDealFinder()

deals = finder.find_deals(
    origin="NYC",
    destination="Paris",
    departure_date="2026-07-23",
    return_date="2026-08-13",
    max_points=120000,
    passengers=2,
    cabin="business"
)

finder.print_deal_report(deals, [])
```

## Transfer Partners Supported

### Amex Membership Rewards (1:1 unless noted)
- Aer Lingus AerClub
- Air Canada Aeroplan
- Air France-KLM Flying Blue
- British Airways Executive Club
- Delta SkyMiles
- Emirates Skywards
- Etihad Guest
- Hawaiian Airlines
- Iberia Plus
- Singapore Airlines KrisFlyer
- Virgin Atlantic Flying Club

### Chase Ultimate Rewards (1:1)
- Air Canada Aeroplan
- Air France-KLM Flying Blue
- British Airways Executive Club
- Iberia Plus
- Singapore Airlines KrisFlyer
- Southwest Rapid Rewards
- United MileagePlus
- Virgin Atlantic Flying Club
- World of Hyatt
- Marriott Bonvoy

### American Airlines AAdvantage
- ❌ Cannot transfer from Amex or Chase
- ✅ Must use AA miles directly
- Can book oneworld partners: British Airways, Iberia, Qatar, Cathay Pacific, JAL

## NYC to Madrid Sweet Spots

| Program | Off-Peak Business | Peak Business | Transfer From |
|---------|-------------------|---------------|---------------|
| Iberia Avios | 34,000 | 50,000 | Amex, Chase, BA |
| British Airways Avios | 50,000 | 60,000 | Amex, Chase |
| Air France Flying Blue | 45,000-55,000 | Dynamic | Amex, Chase |
| American Airlines | 57,500 | 70,000 | AA only |
| United MileagePlus | 60,000-77,000 | Dynamic | Chase only |

## Next Steps to Enhance

1. **Web Scraping**: Add scraping for Seats.aero, PointsYeah to check live availability
2. **Transfer Bonus API**: Integrate with PointsGuy or Doctor of Credit for current bonuses
3. **Award Alerts**: Set up monitoring for specific routes/dates
4. **More Routes**: Expand sweet spot database for Asia, South America, etc.

## Files

- `travel_deal_finder.py` - Main script
- `travel_deals_results.json` - Output file with search results
