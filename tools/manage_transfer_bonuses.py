#!/usr/bin/env python3
import json
from datetime import datetime
from typing import List, Dict, Optional
import os
import re
import sys

REPO_PATH = os.path.expanduser('~/memory/transfer_bonus_repository.json')

def get_current_date() -> datetime:
    return datetime.now()

def load_repository() -> List[Dict]:
    if os.path.exists(REPO_PATH):
        try:
            with open(REPO_PATH, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_repository(bonuses: List[Dict]):
    with open(REPO_PATH, 'w') as f:
        json.dump(bonuses, f, indent=2)

def is_expired(bonus: Dict, current_date: datetime) -> bool:
    expiry_str = bonus.get('expiry')
    if not expiry_str:
        return False
    try:
        # Handles MM/DD/YY, assuming current century
        expiry_date = datetime.strptime(expiry_str, '%m/%d/%y')
        return expiry_date < current_date
    except ValueError:
        try:
            # Handles MM/DD/YYYY
            expiry_date = datetime.strptime(expiry_str, '%m/%d/%Y')
            return expiry_date < current_date
        except ValueError:
            # If parsing fails, assume not expired for safety
            return False

def parse_frequent_miler_bonuses(content: str) -> List[Dict]:
    """
    Parses transfer bonuses from Frequent Miler's "Current point transfer bonuses" page.
    """
    bonuses = []
    # Corrected regex to find the plain text section header
    current_section_match = re.search(r'Current and Upcoming Transfer Bonuses\n\n\tTransfer FromTransfer Bonus DetailsStart DateEnd Date\n\n(.+?)(?=\n\nSee Also|\n\nExpired Transfer Bonuses|\Z)', content, re.DOTALL)
    
    if current_section_match:
        section_content = current_section_match.group(1).strip()
        lines = section_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # This pattern reliably captures the details string and the two dates at the end
            main_content_pattern = re.compile(r'^(.*?)(?:\s|\t)*(\d{2}/\d{2}/\d{2,4})(?:\s|\t)*(\d{2}/\d{2}/\d{2,4})$')
            main_content_match = main_content_pattern.match(line)

            if main_content_match:
                full_bonus_string = main_content_match.group(1).strip()
                start_date_str = main_content_match.group(2).strip()
                end_date_str = main_content_match.group(3).strip()
                source_url = "Frequent Miler"

                transfer_from = "Unknown"
                bonus_percent = None
                target_program = "Unknown"

                # This regex splits the string into three parts:
                # 1. The 'from' program (e.g., "Capital One Miles")
                # 2. The bonus percentage (e.g., "30")
                # 3. The rest of the details (e.g., "transfer bonus from...")
                initial_split_match = re.match(r'^(.*?)\s*(\d+)%\s*(.*)', full_bonus_string, re.IGNORECASE)

                if initial_split_match:
                    transfer_from = initial_split_match.group(1).strip()
                    bonus_percent = int(initial_split_match.group(2))
                    details_text = initial_split_match.group(3).strip()

                    # Now, parse the details_text for the 'to' program
                    to_match = re.search(r'to\s+(.*)', details_text, re.IGNORECASE)
                    if to_match:
                        target_program = to_match.group(1).strip()
                        
                        # Sometimes the 'from' is also repeated in the details, let's check.
                        from_in_details_match = re.search(r'from\s+(.*?)\s+to', details_text, re.IGNORECASE)
                        if from_in_details_match:
                            # This is likely the more accurate 'from', so we overwrite.
                            transfer_from = from_in_details_match.group(1).strip()

                if bonus_percent is not None:
                    effective_ratio = 1 + (bonus_percent / 100.0)
                    bonuses.append({
                        'from': transfer_from,
                        'program': target_program,
                        'bonus': f'{bonus_percent}%',
                        'expiry': end_date_str,
                        'effective_ratio': effective_ratio,
                        'source_url': source_url
                    })
    return bonuses

def update_bonuses_repository(new_bonuses: List[Dict]):
    current_date = get_current_date()
    # Start with a clean slate to avoid merging old bad data
    existing_bonuses = [] # load_repository()
    
    all_bonuses = existing_bonuses + new_bonuses
    unique_bonuses = []
    seen = set()
    for bonus in all_bonuses:
        # Use a tuple of the main identifiers to check for uniqueness
        key = (bonus.get('program'), bonus.get('from'), bonus.get('bonus'), bonus.get('expiry'))
        if key not in seen:
            unique_bonuses.append(bonus)
            seen.add(key)
            
    active_bonuses = [b for b in unique_bonuses if not is_expired(b, current_date)]
    save_repository(active_bonuses)
    return active_bonuses

def main():
    if len(sys.argv) > 1:
        content_file = sys.argv[1]
        if os.path.exists(content_file):
            with open(content_file, 'r') as f:
                raw_content = f.read()
            
            new_bonuses = parse_frequent_miler_bonuses(raw_content)
            active_offers = update_bonuses_repository(new_bonuses)
            
            print("\n--- Active Transfer Bonuses Repository ---\n")
            if active_offers:
                for offer in active_offers:
                    print(f"From: {offer.get('from')}, To: {offer.get('program')}, Bonus: {offer.get('bonus')}, Expiry: {offer.get('expiry')}, Ratio: {offer.get('effective_ratio', 0):.2f}")
            else:
                print("No active transfer bonuses found in repository.")
        else:
            print(f"Error: Content file not found at {content_file}", file=sys.stderr)
    else:
        # If no file is provided, just clean up the existing repository for expired bonuses
        current_date = get_current_date()
        active_offers = load_repository()
        active_offers = [b for b in active_offers if not is_expired(b, current_date)]
        save_repository(active_offers)
        print("\n--- Cleaned Existing Repository ---\n")
        if active_offers:
            for offer in active_offers:
                print(f"From: {offer.get('from')}, To: {offer.get('program')}, Bonus: {offer.get('bonus')}, Expiry: {offer.get('expiry')}, Ratio: {offer.get('effective_ratio', 0):.2f}")
        else:
            print("No active transfer bonuses found in repository.")

if __name__ == "__main__":
    main()
