import numpy as np
import matplotlib.pyplot as plt
from itertools import product
import random

# user input functions
def parse_event_laps(event_name):
    while True:
        s = input(f"Enter laps for {event_name} events separated by commas (or leave blank for none): ").strip()
        if s == "":
            return []
        try:
            laps = [int(x.strip()) for x in s.split(",") if x.strip() != ""]
            if any(lap < 1 or lap > LAPS for lap in laps):
                print(f"Please enter laps between 1 and {LAPS}.")
                continue
            return laps
        except ValueError:
            print("Invalid input. Please enter integers separated by commas.")

while True:
    try:
        LAPS = int(input("Enter total number of laps (e.g. 70): "))
        if LAPS <= 0:
            print("Please enter a positive integer for laps.")
            continue
        break
    except ValueError:
        print("Invalid input. Please enter an integer.")

while True:
    try:
        PIT_STOP_TIME = float(input("Enter pit stop time in seconds (e.g. 20.0): "))
        if PIT_STOP_TIME <= 0:
            print("Please enter a positive number for pit stop time.")
            continue
        break
    except ValueError:
        print("Invalid input. Please enter a number.")

while True:
    CURRENT_WEATHER = input("Enter current weather (Dry, Intermediate, Wet): ").strip().capitalize()
    if CURRENT_WEATHER not in ['Dry', 'Intermediate', 'Wet']:
        print("Invalid weather. Please enter 'Dry', 'Intermediate', or 'Wet'.")
    else:
        break

while True:
    try:
        SOFT_BASE_TIME = float(input("Enter base lap time on Soft tyres in seconds (e.g. 85.0): "))
        if SOFT_BASE_TIME <= 0:
            print("Please enter a positive number for base lap time.")
            continue
        break
    except ValueError:
        print("Invalid input. Please enter a number.")

while True:
    try:
        TRACK_DEGRADATION_MULTIPLIER = float(input("Enter track tyre degradation multiplier (e.g. 1.0 for normal, >1.0 for high degradation): "))
        if TRACK_DEGRADATION_MULTIPLIER <= 0:
            print("Please enter a positive number for degradation multiplier.")
            continue
        break
    except ValueError:
        print("Invalid input. Please enter a number.")

# safety events input
print("\nNow enter the laps for safety events (if any):")
vsc_laps = parse_event_laps("VSC")
sc_laps = parse_event_laps("SC")
red_laps = parse_event_laps("Red")

# combine safety events into dict, SC overwrites VSC, Red overwrites both
SAFETY_EVENTS = {}
for lap in vsc_laps:
    SAFETY_EVENTS[lap] = 'VSC'
for lap in sc_laps:
    SAFETY_EVENTS[lap] = 'SC'
for lap in red_laps:
    SAFETY_EVENTS[lap] = 'Red'

TYRE_TYPES = ['Soft', 'Medium', 'Hard', 'Inter', 'Wet']

# soft tyre baseline
SOFT_DEGRADATION = 0.11 #s/lap
SOFT_LIFE = 15 # laps
SOFT_WARMUP = 2 # laps

TYRE_BASE_TIME_PCT = {
    'Soft': 1.00,
    'Medium': 1.0125,
    'Hard': 1.025,  
    'Inter': 1.06,
    'Wet': 1.09
}
TYRE_DEGRADATION_PCT = {
    'Soft': 1.00,
    'Medium': 0.70,  
    'Hard': 0.28,    
    'Inter': 0.64,
    'Wet': 0.82
}
TYRE_LIFE_PCT = {
    'Soft': 1.00,
    'Medium': 2.00,
    'Hard': 3.00,
    'Inter': 1.33,
    'Wet': 1.33
}
TYRE_WARMUP_PCT = {
    'Soft': 1.00,
    'Medium': 1.2,
    'Hard': 1.3,
    'Inter': 1.0,
    'Wet': 1.0
}
TYRE_SET_LIMITS = {
    'Soft': 2,
    'Medium': 2,
    'Hard': 2,
    'Inter': 3,
    'Wet': 3
}

# absolute values
TYRE_BASE_TIME = {tyre: SOFT_BASE_TIME * TYRE_BASE_TIME_PCT[tyre] for tyre in TYRE_TYPES}

# apply track degradation multiplier here:
TYRE_DEGRADATION = {tyre: SOFT_DEGRADATION * TYRE_DEGRADATION_PCT[tyre] * TRACK_DEGRADATION_MULTIPLIER for tyre in TYRE_TYPES}

TYRE_LIFE = {tyre: int(SOFT_LIFE * TYRE_LIFE_PCT[tyre]) for tyre in TYRE_TYPES}
TYRE_WARMUP = {tyre: int(SOFT_WARMUP * TYRE_WARMUP_PCT[tyre]) for tyre in TYRE_TYPES}

# simulate functions
def is_valid_dry_strategy(strategy):
    if CURRENT_WEATHER != 'Dry':
        return True
    tyres_used = set(tyre for tyre, _ in strategy if tyre in ['Soft', 'Medium', 'Hard'])
    return len(tyres_used) >= 2

def tyre_set_usage_okay(strategy):
    usage = {}
    for tyre, _ in strategy:
        usage[tyre] = usage.get(tyre, 0) + 1
    for tyre, count in usage.items():
        if count > TYRE_SET_LIMITS.get(tyre, 0):
            return False
    return True

def simulate_stint(tyre, laps, fuel_start_lap):
    degradation = TYRE_DEGRADATION[tyre]
    base_time = TYRE_BASE_TIME[tyre]
    warmup_laps = TYRE_WARMUP[tyre]
    life = TYRE_LIFE[tyre]
    times = []

    falloff_severity = {
        'Soft': 4.0,
        'Medium': 2.2,
        'Hard': 1.0,
        'Inter': 2.5,
        'Wet': 2.8
    }

    falloff_start_pct = {
        'Soft': 0.70,
        'Medium': 0.80,
        'Hard': 0.90,
        'Inter': 0.80,
        'Wet': 0.80
    }

    falloff_point = int(falloff_start_pct[tyre] * life)

    for i in range(laps):
        lap_num = fuel_start_lap + i
        fuel_effect = 0.03 * (LAPS - lap_num)

        if i < falloff_point:
            tyre_wear_penalty = degradation * i
            puncture_chance = 0.002
        elif i < life:
            tyre_wear_penalty = (
                degradation * falloff_point +
                (i - falloff_point) * degradation * falloff_severity[tyre]
            )
            puncture_chance = 0.005 + 0.001 * (i - falloff_point) * falloff_severity[tyre]
        else:
            tyre_wear_penalty = (
                degradation * falloff_point +
                (life - falloff_point) * degradation * falloff_severity[tyre] +
                (i - life) * degradation * (falloff_severity[tyre] + 2.0)
            )
            puncture_chance = 0.01 + 0.002 * (i - life) * falloff_severity[tyre]

        # penalty for unrealistically long soft stints
        if tyre == 'Soft' and laps > TYRE_LIFE['Soft'] + 3:
            tyre_wear_penalty += 0.5 * (laps - TYRE_LIFE['Soft'] - 3)

        warmup_penalty = 1.0 if i < warmup_laps else 0.0
        randomness = np.random.normal(0, 0.2)
        puncture_penalty = 5.0 if random.random() < puncture_chance else 0.0

        weather_penalty = 0.0
        if CURRENT_WEATHER == 'Intermediate':
            if tyre in ['Soft', 'Medium', 'Hard']:
                weather_penalty += 10.0
            elif tyre == 'Wet':
                weather_penalty += 3.0
        elif CURRENT_WEATHER == 'Wet':
            if tyre in ['Soft', 'Medium', 'Hard']:
                weather_penalty += 20.0

        safety_adjustment = 0.0
        if lap_num in SAFETY_EVENTS:
            if SAFETY_EVENTS[lap_num] == 'VSC':
                safety_adjustment = 2.0
            elif SAFETY_EVENTS[lap_num] == 'SC':
                safety_adjustment = 5.0
            elif SAFETY_EVENTS[lap_num] == 'Red':
                safety_adjustment = 0.0

        stationary_start_penalty = 3.0 if lap_num == 0 else 0.0

        lap_time = max(
            base_time + tyre_wear_penalty + fuel_effect + warmup_penalty +
            randomness + puncture_penalty + weather_penalty +
            safety_adjustment + stationary_start_penalty, LAPS
        )

        times.append(lap_time)

    return times


def simulate_race(strategy):
    lap_times = []
    current_lap = 0
    pit_laps = []

    for i, (tyre, stint_length) in enumerate(strategy):
        stint_times = simulate_stint(tyre, stint_length, current_lap)
        lap_times += stint_times
        current_lap += stint_length

        if i < len(strategy) - 1 and current_lap < LAPS:
            lap_times[-1] += PIT_STOP_TIME
            pit_laps.append(current_lap)

    return lap_times[:LAPS], pit_laps

def generate_strategies():
    all_results = []

    # allow only tyres appropriate for the current weather
    if CURRENT_WEATHER == 'Dry':
        valid_tyres = ['Soft', 'Medium', 'Hard']
    elif CURRENT_WEATHER == 'Intermediate':
        valid_tyres = ['Inter']
    elif CURRENT_WEATHER == 'Wet':
        valid_tyres = ['Wet']
    else:
        valid_tyres = TYRE_TYPES  # fallback

    # two-stop strategy loop
    min_first_stint = TYRE_LIFE[valid_tyres[-1]] - 5
    max_first_stint = TYRE_LIFE[valid_tyres[-1]] + 5

    for c1 in valid_tyres:
        for c2 in valid_tyres:
            for split in range(min_first_stint, max_first_stint + 1):
                if split >= LAPS:
                    continue

                second_stint_laps = LAPS - split
                if second_stint_laps <= 0 or second_stint_laps > TYRE_LIFE[c2]:
                    continue

                stints = [(c1, split), (c2, second_stint_laps)]
                if not is_valid_dry_strategy(stints) or not tyre_set_usage_okay(stints):
                    continue

                time, _ = simulate_race(stints)
                all_results.append((sum(time), stints))

    # three-stop strategy loop
    for compounds in product(valid_tyres, repeat=3):
        for split1 in range(10, LAPS - 20):
            for split2 in range(split1 + 5, LAPS - 5):
                lengths = [split1, split2 - split1, LAPS - split2]
                if any(l <= 0 for l in lengths):
                    continue
                strategy = list(zip(compounds, lengths))
                if not is_valid_dry_strategy(strategy) or not tyre_set_usage_okay(strategy):
                    continue
                time, _ = simulate_race(strategy)
                all_results.append((sum(time), strategy))

    all_results.sort(key=lambda x: x[0])
    
    # one-stop strategy loop
    for c1 in valid_tyres:
        for c2 in valid_tyres:
            for split in range(1, LAPS):  # split point is where the stop happens
                first_stint = split
                second_stint = LAPS - split
                strategy = [(c1, first_stint), (c2, second_stint)]

            if not is_valid_dry_strategy(strategy) or not tyre_set_usage_okay(strategy):
                continue

            time, _ = simulate_race(strategy)
            all_results.append((sum(time), strategy))


    print("\nTop 10 Strategies:")
    for i, (t, s) in enumerate(all_results[:10], 1):
        print(f"{i}: Time = {t:.2f}s, Strategy = {s}")

    return all_results[:5]


# run simulation
print("\nSimulating best strategies...\n")
results = generate_strategies()
best_time, best_strategy = results[0]
lap_times, pit_laps = simulate_race(best_strategy)

print(f"\nBest Strategy: {best_strategy}")
print(f"Total Race Time: {best_time:.2f}s")

# plot
plt.figure(figsize=(12, 6))
plt.plot(range(1, len(lap_times) + 1), lap_times, label='Lap Time', color='blue')
plt.axhline(y=np.mean(lap_times), color='gray', linestyle='--', label='Average Pace')

for idx, pit in enumerate(pit_laps):
    plt.axvline(x=pit, color='red', linestyle='--', label='Pit Stop' if idx == 0 else "")

plt.title('Race Simulation - Optimal Strategy')
plt.xlabel('Lap')
plt.ylabel('Lap Time (s)')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
