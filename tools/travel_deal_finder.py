#!/usr/bin/env python3
"""
Travel Deal Finder - Searches for business class award flights
and checks Amex/AA transfer compatibility
"""

import json
import re
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
import requests
from urllib.parse import quote

@dataclass
class AwardFlight:
    airline: str
    program: str
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str]
    points_required: int
    taxes_fees: float
    cabin: str
    transfer_from: List[str]  # Which programs can transfer to this
    transfer_bonus: Optional[float] = None
    availability: str = "unknown"

class TransferPartners:
    """Transfer partner mappings for credit card programs"""
    
    AMEX_PARTNERS = {
        "Aer Lingus AerClub": {"ratio": "1:1", "bonus": None},
        "Aeromexico Rewards": {"ratio": "1:1.6", "bonus": None},
        "Air Canada Aeroplan": {"ratio": "1:1", "bonus": None},
        "Air France-KLM Flying Blue": {"ratio": "1:1", "bonus": None},
        "ANA Mileage Club": {"ratio": "1:1", "bonus": None},
        "Avianca LifeMiles": {"ratio": "1:1", "bonus": None},
        "British Airways Executive Club": {"ratio": "1:1", "bonus": None},
        "Cathay Pacific Asia Miles": {"ratio": "1:1", "bonus": None},
        "Delta SkyMiles": {"ratio": "1:1", "bonus": None},
        "Emirates Skywards": {"ratio": "1:1", "bonus": None},
        "Etihad Guest": {"ratio": "1:1", "bonus": None},
        "Hawaiian Airlines HawaiianMiles": {"ratio": "1:1", "bonus": None},
        "Iberia Plus": {"ratio": "1:1", "bonus": None},
        "JetBlue TrueBlue": {"ratio": "1:0.8", "bonus": None},
        "Qantas Frequent Flyer": {"ratio": "1:1", "bonus": None},
        "Singapore Airlines KrisFlyer": {"ratio": "1:1", "bonus": None},
        "Virgin Atlantic Flying Club": {"ratio": "1:1", "bonus": None},
        "Hilton Honors": {"ratio": "1:2", "bonus": None},
        "Marriott Bonvoy": {"ratio": "1:1", "bonus": None},
    }
    
    # American Airlines doesn't transfer to other airlines, but can book partners
    AA_PARTNERS = {
        "oneworld": ["British Airways", "Iberia", "Qatar Airways", "Cathay Pacific", "Japan Airlines"],
        "other_partners": ["Alaska Airlines", "Etihad", "Hawaiian Airlines"]
    }
    
    CHASE_PARTNERS = {
        "Aer Lingus AerClub": {"ratio": "1:1"},
        "Air Canada Aeroplan": {"ratio": "1:1"},
        "Air France-KLM Flying Blue": {"ratio": "1:1"},
        "British Airways Executive Club": {"ratio": "1:1"},
        "Emirates Skywards": {"ratio": "1:1"},
        "Iberia Plus": {"ratio": "1:1"},
        "JetBlue TrueBlue": {"ratio": "1:1"},
        "Singapore Airlines KrisFlyer": {"ratio": "1:1"},
        "Southwest Rapid Rewards": {"ratio": "1:1"},
        "United MileagePlus": {"ratio": "1:1"},
        "Virgin Atlantic Flying Club": {"ratio": "1:1"},
        "IHG One Rewards": {"ratio": "1:1"},
        "Marriott Bonvoy": {"ratio": "1:1"},
        "World of Hyatt": {"ratio": "1:1"},
    }

class SweetSpots:
    """Known sweet spots for award redemptions to Europe"""
    
    NYC_TO_MADRID = {
        "Iberia Avios": {
            "off_peak_business": 34000,
            "peak_business": 50000,
            "peak_dates": ["June", "July", "August", "December"],
            "transfer_from": ["Amex", "Chase", "British Airways"],
            "notes": "Best value. Can transfer Amex→BA→Iberia or book via BA.com"
        },
        "British Airways Avios": {
            "off_peak_business": 50000,
            "peak_business": 60000,
            "transfer_from": ["Amex", "Chase"],
            "notes": "Higher than Iberia but easier to book"
        },
        "Air France-KLM Flying Blue": {
            "business_range": "45000-55000",
            "transfer_from": ["Amex", "Chase"],
            "notes": "Dynamic pricing, check regularly"
        },
        "American Airlines AAdvantage": {
            "off_peak_business": 57500,
            "peak_business": 70000,
            "transfer_from": ["AA only"],
            "notes": "Cannot transfer from Amex/Chase. Must use AA miles directly"
        },
        "Delta SkyMiles": {
            "business_range": "80000-120000",
            "transfer_from": ["Amex"],
            "notes": "Dynamic pricing, often poor value"
        },
        "United MileagePlus": {
            "business": 77000,
            "transfer_from": ["Chase only"],
            "notes": "If you have Chase UR points"
        },
        "Virgin Atlantic": {
            "business": 95000,
            "transfer_from": ["Amex", "Chase"],
            "notes": "Can book Delta One to Europe"
        }
    }

class TravelDealFinder:
    """Main class to find travel deals"""
    
    def __init__(self):
        self.transfer_partners = TransferPartners()
        self.sweet_spots = SweetSpots()
        
    def find_deals(self, origin: str, destination: str, 
                   departure_date: str, return_date: Optional[str] = None,
                   max_points: int = 70000, passengers: int = 2,
                   cabin: str = "business") -> List[Dict]:
        """
        Find award flight deals based on sweet spots and transfer partners
        """
        deals = []
        
        # Check NYC to Madrid specific deals
        if origin.upper() in ["NYC", "JFK", "EWR", "LGA"] and destination.upper() == "MADRID":
            deals.extend(self._check_nyc_madrid_routes(departure_date, return_date, max_points, passengers))
        
        # Add generic European business class sweet spots
        deals.extend(self._check_generic_europe_routes(origin, destination, departure_date, return_date, max_points, passengers))
        
        return sorted(deals, key=lambda x: x["total_points"])
    
    def _check_nyc_madrid_routes(self, departure_date: str, return_date: Optional[str], 
                                  max_points: int, passengers: int) -> List[Dict]:
        """Check known sweet spots for NYC-Madrid"""
        deals = []
        
        for program, details in self.sweet_spots.NYC_TO_MADRID.items():
            # Check if it's peak season (July-August)
            is_peak = self._is_peak_season(departure_date)
            
            if "off_peak_business" in details and "peak_business" in details:
                points = details["peak_business"] if is_peak else details["off_peak_business"]
            elif "business" in details:
                points = details["business"]
            else:
                # Skip dynamic pricing programs for now
                continue
            
            total_points = points * passengers
            
            if total_points <= max_points:
                deal = {
                    "program": program,
                    "points_per_person": points,
                    "total_points": total_points,
                    "passengers": passengers,
                    "is_peak": is_peak,
                    "transfer_from": details.get("transfer_from", []),
                    "notes": details.get("notes", ""),
                    "route": "NYC → Madrid",
                    "cabin": "Business Class",
                    "amex_transfer": "Amex" in details.get("transfer_from", []),
                    "aa_transfer": "AA" in details.get("transfer_from", []) or "American" in program,
                    "chase_transfer": "Chase" in details.get("transfer_from", [])
                }
                deals.append(deal)
        
        return deals
    
    def _check_generic_europe_routes(self, origin: str, destination: str,
                                      departure_date: str, return_date: Optional[str],
                                      max_points: int, passengers: int) -> List[Dict]:
        """Check generic sweet spots for Europe"""
        deals = []
        
        # Virgin Atlantic to Europe via Delta
        if max_points >= 95000 * passengers:
            deals.append({
                "program": "Virgin Atlantic (Delta One)",
                "points_per_person": 50000,
                "total_points": 50000 * passengers,
                "passengers": passengers,
                "transfer_from": ["Amex", "Chase"],
                "notes": "Can book Delta One to Europe. Sometimes lower off-peak",
                "route": f"{origin} → {destination}",
                "cabin": "Business Class",
                "amex_transfer": True,
                "aa_transfer": False,
                "chase_transfer": True,
                "is_peak": self._is_peak_season(departure_date)
            })
        
        # Aeroplan to Europe
        if max_points >= 60000 * passengers:
            deals.append({
                "program": "Air Canada Aeroplan",
                "points_per_person": 60000,
                "total_points": 60000 * passengers,
                "passengers": passengers,
                "transfer_from": ["Amex", "Chase"],
                "notes": "Good availability to Europe on Star Alliance partners",
                "route": f"{origin} → {destination}",
                "cabin": "Business Class",
                "amex_transfer": True,
                "aa_transfer": False,
                "chase_transfer": True,
                "is_peak": self._is_peak_season(departure_date)
            })
        
        return deals
    
    def _is_peak_season(self, date_str: str) -> bool:
        """Check if date falls in peak season"""
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            month = date.month
            # Peak: June (6), July (7), August (8), December (12)
            return month in [6, 7, 8, 12]
        except:
            return True  # Assume peak if can't parse
    
    def get_transfer_instructions(self, program: str, points_needed: int) -> Dict:
        """Get instructions on how to transfer points to a specific program"""
        
        instructions = {
            "Iberia Avios": {
                "amex_transfer": f"Transfer {points_needed} Amex MR → British Airways Avios (1:1), then combine to Iberia",
                "transfer_time": "Instant",
                "booking_site": "https://www.iberia.com",
                "alternative": "Book via BritishAirways.com (often easier)"
            },
            "British Airways Avios": {
                "amex_transfer": f"Transfer {points_needed} Amex MR → British Airways Avios (1:1)",
                "chase_transfer": f"Transfer {points_needed} Chase UR → British Airways Avios (1:1)",
                "transfer_time": "Instant",
                "booking_site": "https://www.britishairways.com"
            },
            "Air France-KLM Flying Blue": {
                "amex_transfer": f"Transfer {points_needed} Amex MR → Flying Blue (1:1)",
                "chase_transfer": f"Transfer {points_needed} Chase UR → Flying Blue (1:1)",
                "transfer_time": "Instant",
                "booking_site": "https://www.airfrance.com"
            },
            "American Airlines AAdvantage": {
                "amex_transfer": "❌ Cannot transfer Amex to AA",
                "notes": "Must use existing AA miles. Cannot transfer from credit cards",
                "booking_site": "https://www.aa.com"
            },
            "Delta SkyMiles": {
                "amex_transfer": f"Transfer {points_needed} Amex MR → Delta (1:1). Note: Usually poor value",
                "transfer_time": "Instant",
                "booking_site": "https://www.delta.com"
            }
        }
        
        return instructions.get(program, {"notes": "Check program website for transfer options"})
    
    def check_active_transfer_bonuses(self) -> List[Dict]:
        """
        Returns known transfer bonuses (would need web scraping or API for real-time)
        """
        # These change frequently - this is a template structure
        common_bonuses = [
            {
                "program": "British Airways / Iberia",
                "bonus": "30%",
                "from": "Amex",
                "expiry": "Check current offers",
                "effective_ratio": "1:1.3"
            },
            {
                "program": "Air France-KLM Flying Blue",
                "bonus": "25%",
                "from": "Amex",
                "expiry": "Check current offers",
                "effective_ratio": "1:1.25"
            }
        ]
        return common_bonuses
    
    def print_deal_report(self, deals: List[Dict], transfer_bonuses: List[Dict]):
        """Print a formatted deal report"""
        print("\n" + "="*70)
        print("🎯 TRAVEL DEAL FINDER REPORT")
        print("="*70)
        
        if not deals:
            print("\n❌ No deals found under the points threshold")
            return
        
        print(f"\n✅ Found {len(deals)} potential deals:\n")
        
        for i, deal in enumerate(deals, 1):
            print(f"{i}. {deal['program']}")
            print(f"   Route: {deal['route']}")
            print(f"   Points: {deal['points_per_person']:,} per person ({deal['total_points']:,} total)")
            print(f"   Peak Season: {'Yes' if deal['is_peak'] else 'No'}")
            print(f"   Transfer From: {', '.join(deal['transfer_from'])}")
            
            # Amex compatibility
            if deal['amex_transfer']:
                print(f"   ✓ Amex Transfer: YES")
            else:
                print(f"   ✗ Amex Transfer: NO")
            
            # AA compatibility
            if deal['aa_transfer']:
                print(f"   ✓ AA Miles: YES (use directly)")
            else:
                print(f"   ✗ AA Miles: NO (cannot transfer to this program)")
            
            print(f"   Notes: {deal['notes']}")
            print()
        
        # Show transfer bonuses
        if transfer_bonuses:
            print("\n" + "-"*70)
            print("💰 ACTIVE TRANSFER BONUSES (check for current offers):")
            print("-"*70)
            for bonus in transfer_bonuses:
                print(f"   {bonus['from']} → {bonus['program']}: +{bonus['bonus']} bonus")
                print(f"   Effective ratio: {bonus['effective_ratio']}")
            print()
        
        # Best deal recommendation
        if deals:
            best = deals[0]
            print("\n" + "="*70)
            print("🏆 RECOMMENDED DEAL")
            print("="*70)
            print(f"Program: {best['program']}")
            print(f"Points Needed: {best['total_points']:,} total")
            
            if best['amex_transfer']:
                instructions = self.get_transfer_instructions(best['program'], best['total_points'])
                print(f"\n📋 Transfer Instructions:")
                if 'amex_transfer' in instructions:
                    print(f"   {instructions['amex_transfer']}")
                if 'transfer_time' in instructions:
                    print(f"   Transfer Time: {instructions['transfer_time']}")
                if 'booking_site' in instructions:
                    print(f"   Book At: {instructions['booking_site']}")
                if 'alternative' in instructions:
                    print(f"   Tip: {instructions['alternative']}")


def main():
    """Main function to run the deal finder"""
    finder = TravelDealFinder()
    
    # Example search for Fas's trip
    print("Searching for deals: NYC → Madrid")
    print("Dates: July 23 - August 13, 2026")
    print("Passengers: 2")
    print("Max Points: 70,000 per person (140,000 total)\n")
    
    deals = finder.find_deals(
        origin="NYC",
        destination="Madrid",
        departure_date="2026-07-23",
        return_date="2026-08-13",
        max_points=140000,
        passengers=2,
        cabin="business"
    )
    
    bonuses = finder.check_active_transfer_bonuses()
    finder.print_deal_report(deals, bonuses)
    
    # Save results to file
    results = {
        "search_params": {
            "origin": "NYC",
            "destination": "Madrid",
            "departure": "2026-07-23",
            "return": "2026-08-13",
            "passengers": 2,
            "max_points": 140000
        },
        "deals_found": deals,
        "transfer_bonuses": bonuses
    }
    
    with open("travel_deals_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n💾 Results saved to: travel_deals_results.json")


if __name__ == "__main__":
    main()
