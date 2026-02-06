import csv
import datetime
import os
from serpapi import GoogleSearch

# ================= CONFIGURATION =================
API_KEY = "4aad71725d794cc9f548446d2ebb66e0d8c840af773b134dfb95eb44675e2783"
FILE_NAME = "daily_cheapest_flight_track.csv"

DEPARTURE = "BOM"
ARRIVAL = "DEL"

TIME_WINDOW = "6,9"     # 6 AM – 9 AM
DIRECT_ONLY = 1         # Non-stop only
# =================================================


def get_target_date():
    """
    If script runs after 8 AM, track tomorrow.
    Otherwise track today.
    """
    now = datetime.datetime.now()
    if now.hour >= 8:
        return (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")


def fetch_cheapest_fares():
    target_date = get_target_date()
    print(f"\nTracking cheapest fares for {target_date} (6–9 AM)\n")

    params = {
        "engine": "google_flights",
        "api_key": API_KEY,
        "departure_id": DEPARTURE,
        "arrival_id": ARRIVAL,
        "outbound_date": target_date,
        "currency": "INR",
        "outbound_times": TIME_WINDOW,
        "stops": DIRECT_ONLY,
        "type": "2",               # One-way
        "hl": "en",
        "deep_search": True
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    cheapest_by_airline = {}

    for section in ["best_flights", "other_flights"]:
        for itinerary in results.get(section, []):
            price = itinerary.get("price")
            if not price:
                continue

            extensions = itinerary.get("extensions", [])

            # Skip refundable / flex / premium fares
            if any(
                keyword in " ".join(extensions).lower()
                for keyword in ["refund", "change", "flex"]
            ):
                continue

            flight = itinerary["flights"][0]
            airline = flight.get("airline")

            departure_time = flight["departure_airport"]["time"]

            entry = {
                "query_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "flight_date": target_date,
                "airline": airline,
                "price": price,
                "departure_time": departure_time,
                "duration_minutes": itinerary.get("total_duration"),
                "fare_type": "Economy"
            }

            # Keep only the cheapest fare per airline
            if airline not in cheapest_by_airline or price < cheapest_by_airline[airline]["price"]:
                cheapest_by_airline[airline] = entry

    return list(cheapest_by_airline.values())


# ================= RUN & SAVE =================
data = fetch_cheapest_fares()

if not data:
    print("No economy fares found. Try widening the time window.")
    exit()

file_exists = os.path.isfile(FILE_NAME)

with open(FILE_NAME, mode="a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "query_time",
            "flight_date",
            "airline",
            "price",
            "departure_time",
            "duration_minutes",
            "fare_type"
        ]
    )

    if not file_exists:
        writer.writeheader()

    writer.writerows(data)

print("Saved cheapest fares:\n")
for row in data:
    print(f"{row['airline']}: ₹{row['price']} at {row['departure_time']}")

print("\nDone.")
