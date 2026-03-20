import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# ================================
# 1. FILE UPLOAD
# ================================
from google.colab import files
uploaded = files.upload()

file_name = list(uploaded.keys())[0]
df = pd.read_excel(file_name)

print("File loaded successfully!")

# ================================
# 2. CLEAN DATA
# ================================
df = df[df["price"] != "NO_DATA"]
df["price"] = pd.to_numeric(df["price"], errors="coerce")

df = df.dropna(subset=["price", "departure_time", "airline"])

df["departure_time"] = pd.to_datetime(
    df["departure_time"], errors="coerce"
).dt.strftime("%H:%M")

df = df.dropna(subset=["departure_time"])

df["flight_id"] = df["airline"].astype(str) + " - " + df["departure_time"]

# ================================
# 3. FLIGHT SUMMARY
# ================================
flight_summary = df.groupby("flight_id").agg(
    avg_price=("price", "mean"),
    min_price=("price", "min"),
    max_price=("price", "max")
).reset_index()

flight_summary["avg_price"] = flight_summary["avg_price"].astype(int)
flight_summary["min_price"] = flight_summary["min_price"].astype(int)
flight_summary["max_price"] = flight_summary["max_price"].astype(int)

flight_summary["airline"] = flight_summary["flight_id"].apply(lambda x: x.split(" - ")[0])

# ================================
# 4. ADMIN INPUT (SEATS FIRST)
# ================================
seats = {}

print("\n--- ADMIN: Enter Seats ---")
for i, row in flight_summary.iterrows():
    seats[row["flight_id"]] = int(input(f"Seats for {row['flight_id']}: "))

# ================================
# 5. DISPLAY FLIGHTS
# ================================
def show_flights():
    print("\nAvailable Flights:")
    for i, row in flight_summary.iterrows():
        print(f"{i}: {row['flight_id']}")

# ================================
# 6. WTP FUNCTION (7 QUESTIONS)
# ================================
def get_wtp(min_price, max_price):
    low = min_price
    high = max_price
    
    responses = []
    
    for _ in range(7):
        price = int((low + high) / 2)
        resp = input(f"Would you buy at ₹{price}? (yes/no): ").lower()
        
        if resp not in ["yes", "no"]:
            resp = "no"
        
        responses.append((price, resp))
        
        if resp == "yes":
            low = price
        else:
            high = price
    
    yes_prices = [p for p, r in responses if r == "yes"]
    return max(yes_prices) if yes_prices else 0

# ================================
# 7. PARTICIPANTS
# ================================
participants = []

n = int(input("\nEnter number of participants: "))

for i in range(n):
    print(f"\nParticipant {i+1}")
    show_flights()
    
    try:
        choice = int(input("Select flight index: "))
        selected = flight_summary.iloc[choice]
    except:
        print("Invalid choice, skipping")
        continue
    
    wtp = get_wtp(selected["min_price"], selected["max_price"])
    
    participants.append({
        "flight_id": selected["flight_id"],
        "wtp": wtp
    })

# ================================
# 8. REVENUE CURVES
# ================================
print("\n=== REVENUE CURVES ===")

flight_to_airline = dict(zip(flight_summary["flight_id"], flight_summary["airline"]))
airline_wtp = {}

for p in participants:
    airline = flight_to_airline[p["flight_id"]]
    airline_wtp.setdefault(airline, []).append(p["wtp"])

for airline, wtps in airline_wtp.items():
    if not wtps:
        continue
    
    price_points = sorted(set(wtps))
    revenues = []
    
    for price in price_points:
        demand = sum(1 for w in wtps if w >= price)
        revenues.append(price * demand)
    
    plt.figure()
    plt.plot(price_points, revenues, marker='o')
    plt.title(f"Revenue Curve - {airline}")
    plt.xlabel("Price")
    plt.ylabel("Revenue")
    plt.grid()
    plt.show()

# ================================
# 9. OPTIMIZATION
# ================================
results = {}

for flight in flight_summary["flight_id"]:
    wtps = [p["wtp"] for p in participants if p["flight_id"] == flight]
    
    avg_price = flight_summary.loc[
        flight_summary["flight_id"] == flight, "avg_price"
    ].values[0]

    if not wtps or max(wtps) == 0:
        best_price = int(0.8 * avg_price)
        best_sold = 0
        best_rev = 0
    else:
        possible_prices = sorted(set(wtps))
        best_price, best_rev, best_sold = 0, 0, 0
        
        for price in possible_prices:
            demand = sum(1 for w in wtps if w >= price)
            sold = min(demand, seats[flight])
            revenue = price * sold
            
            if revenue > best_rev:
                best_price, best_rev, best_sold = price, revenue, sold

        best_price = max(best_price, int(0.8 * avg_price))

    remaining = seats[flight] - best_sold
    load_factor = best_sold / seats[flight] if seats[flight] > 0 else 0

    if load_factor > 0.9:
        multiplier = 1.3
    elif load_factor > 0.7:
        multiplier = 1.15
    elif load_factor < 0.4:
        multiplier = 0.9
    else:
        multiplier = 1.0

    suggested_price = int(avg_price * multiplier)

    results[flight] = {
        "price": best_price,
        "revenue": best_rev,
        "sold": best_sold,
        "remaining_seats": remaining,
        "avg_price": avg_price,
        "suggested_price": suggested_price
    }

# ================================
# 10. DYNAMIC FLOOR
# ================================
def get_dynamic_floor(res):
    if res["remaining_seats"] < 20:
        return int(0.8 * res["suggested_price"])
    else:
        return int(0.6 * res["suggested_price"])

# ================================
# 11. TIME HELPER
# ================================
def time_to_minutes(t):
    return int(datetime.strptime(t, "%H:%M").hour) * 60 + int(datetime.strptime(t, "%H:%M").minute)

# ================================
# 12. MULTI-OPTION SUGGESTION (MAX 3)
# ================================
def suggest_alternative(wtp, chosen_flight):
    options = []

    chosen_time = chosen_flight.split(" - ")[1]
    chosen_minutes = time_to_minutes(chosen_time)

    for flight, res in results.items():
        if flight == chosen_flight:
            continue

        flight_time = flight.split(" - ")[1]
        flight_minutes = time_to_minutes(flight_time)

        time_diff = abs(flight_minutes - chosen_minutes)

        floor_price = get_dynamic_floor(res)
        base_price = max(res["price"], floor_price)

        discounted_price = int(base_price * 0.75)
        final_price = max(discounted_price, floor_price)

        if wtp < 0.8 * final_price:
            continue

        score = time_diff + 0.1 * final_price - 0.5 * res["remaining_seats"]

        options.append((flight, final_price, res["remaining_seats"], score))

    options = sorted(options, key=lambda x: x[3])

    return options[:3]

# ================================
# 13. PARTICIPANT BOOKINGS + INSIGHTS
# ================================
print("\n=== PARTICIPANT BOOKINGS & INSIGHTS ===")

for i, p in enumerate(participants):
    chosen = p["flight_id"]
    wtp = p["wtp"]

    res = results.get(chosen, None)
    if not res:
        continue

    avg_price = res["avg_price"]
    remaining = res["remaining_seats"]
    optimal_price = res["price"]
    suggested = res["suggested_price"]

    floor_price = get_dynamic_floor(res)
    effective_price = max(optimal_price, floor_price)

    print(f"\n👤 Participant {i+1}")
    print(f"Flight: {chosen}")
    print(f"WTP: ₹{wtp} | Price Offered: ₹{effective_price}")

    booked = False

    if remaining < 2 and optimal_price <= suggested:
        print("❌ Booking Blocked")
    elif remaining == 1:
        if wtp >= 1.5 * avg_price:
            print("✅ Booked (Premium Seat)")
            booked = True
        else:
            print("❌ Not Booked (Premium unmet)")
    elif wtp >= effective_price:
        print("✅ Booked")
        booked = True
    else:
        print("❌ Not Booked")

    # Insights
    gap = wtp - effective_price
    ratio = wtp / effective_price if effective_price > 0 else 0

    print("📊 Insights:")

    if gap > 0:
        print(f"✔ Surplus Value: ₹{gap}")
    else:
        print(f"✖ Shortfall: ₹{abs(gap)}")

    if ratio > 1.3:
        print("💰 Low price sensitivity")
    elif ratio > 1.0:
        print("⚖️ Moderate sensitivity")
    else:
        print("📉 High sensitivity")

    if remaining < 5:
        print("🪑 High demand flight")
    elif remaining > 15:
        print("🪑 Low demand flight")

    if not booked:
        alt = suggest_alternative(wtp, chosen)
        if alt:
            print("👉 Best Alternatives:")
            for a in alt:
                print(f"   {a[0]} at ₹{a[1]} (Seats: {a[2]})")
        else:
            print("❌ No alternatives")

# ================================
# 14. ADMIN INSIGHTS (ONLY SELECTED)
# ================================
print("\n=== ADMIN INSIGHTS ===")

selected_flights = set([p["flight_id"] for p in participants])

for flight in selected_flights:
    res = results.get(flight, None)
    if not res:
        continue

    optimal = res["price"]
    suggested = res["suggested_price"]
    remaining = res["remaining_seats"]
    sold = res["sold"]

    airline = flight.split(" - ")[0]

    capacity = sold + remaining if (sold + remaining) > 0 else 1
    load_factor = sold / capacity

    print(f"\n✈️ {flight}")
    print(f"Optimal: ₹{optimal} | Suggested: ₹{suggested}")
    print(f"Sold: {sold} | Remaining: {remaining}")

    if load_factor > 0.85:
        print("🔥 Strong Demand")
    elif load_factor > 0.6:
        print("⚖️ Balanced Demand")
    else:
        print("❄️ Weak Demand")

    if remaining < 3:
        print("🚨 Low seats → Redirect within same airline")

        alternatives = []
        for f2, r2 in results.items():
            if f2 != flight and f2.startswith(airline):
                if r2["remaining_seats"] > remaining:
                    alternatives.append((f2, r2["remaining_seats"], r2["price"]))

        alternatives = sorted(alternatives, key=lambda x: (-x[1], x[2]))

        if alternatives:
            best_alt = alternatives[0]
            print(f"👉 Redirect to: {best_alt[0]} (Seats: {best_alt[1]}, Price: ₹{best_alt[2]})")

    elif remaining > 10:
        print("🟡 Excess seats → Discount possible")

    if optimal > suggested:
        print("📈 Increase pricing")
    elif optimal < suggested:
        print("📉 Discount zone")
    else:
        print("⚖️ Maintain pricing")
