"""
Genereer een Markdown rapport met alle analyses voor Drie Gebroeders.
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

# Configuratie
TEAM_NAAM = "Drie Gebroeders"
DATA_DIR = Path("Data")
OUTPUT_DIR = Path("rapport_output")
OUTPUT_DIR.mkdir(exist_ok=True)

TEAM_COLOR = '#1f77b4'
OTHER_COLOR = '#cccccc'

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 150
plt.rcParams['font.size'] = 10

# =============================================================================
# DATA LADEN
# =============================================================================

def load_race_data(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def ship_to_dataframe(ship_data, race_name):
    df = pd.DataFrame({
        'timestamp': ship_data['stamp'],
        'lat': ship_data['lat'],
        'lon': ship_data['lon'],
        'speed': ship_data['speed'],
        'course': ship_data['course']
    })
    df['ship_name'] = ship_data['name']
    df['race'] = race_name
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    return df

def wind_to_dataframe(wind_data):
    df = pd.DataFrame({
        'timestamp': wind_data['stamp'],
        'lat': wind_data['lat'],
        'lon': wind_data['lon'],
        'wind_speed': wind_data['speed'],
        'wind_direction': wind_data['course']
    })
    df['station'] = wind_data['name']
    return df

def clean_race_data(df, starttime, endtime, speed_threshold=5, max_speed=200):
    df_clean = df[(df['timestamp'] >= starttime) & (df['timestamp'] <= endtime)].copy()
    df_clean = df_clean[df_clean['speed'] >= speed_threshold]
    df_clean = df_clean[df_clean['speed'] <= max_speed]
    return df_clean

def calculate_twa(course, wind_direction):
    diff = abs(course - wind_direction)
    if diff > 180:
        diff = 360 - diff
    return diff

print("📊 Data laden...")

race_files = sorted(DATA_DIR.glob("B-Match*.json"))
all_races = {}
all_wind = {}
race_info = []

for filepath in race_files:
    race_name = filepath.stem.replace('B-', '')
    data = load_race_data(filepath)

    starttime = data.get('starttime', 0)
    endtime = data.get('endtime', 0)

    race_info.append({
        'race': race_name,
        'start': datetime.fromtimestamp(starttime),
        'end': datetime.fromtimestamp(endtime),
        'duration_min': (endtime - starttime) / 60
    })

    ships_df = []
    for ship in data.get('shiptracks', []):
        df = ship_to_dataframe(ship, race_name)
        df_clean = clean_race_data(df, starttime, endtime)
        if len(df_clean) > 0:
            ships_df.append(df_clean)

    all_races[race_name] = pd.concat(ships_df, ignore_index=True) if ships_df else pd.DataFrame()

    wind_df = []
    for wind in data.get('windtracks', []):
        df = wind_to_dataframe(wind)
        df = df[(df['timestamp'] >= starttime) & (df['timestamp'] <= endtime)]
        if len(df) > 0:
            wind_df.append(df)

    all_wind[race_name] = pd.concat(wind_df, ignore_index=True) if wind_df else pd.DataFrame()

df_all = pd.concat(all_races.values(), ignore_index=True)
df_team = df_all[df_all['ship_name'] == TEAM_NAAM].copy()

print(f"✅ {len(race_files)} wedstrijden geladen")
print(f"✅ {len(df_team):,} datapunten voor {TEAM_NAAM}")

# =============================================================================
# ANALYSE 1: SNELHEID PER WEDSTRIJD
# =============================================================================

print("📈 Analyse 1: Snelheid per wedstrijd...")

speed_stats = df_all.groupby(['race', 'ship_name'])['speed'].agg(['mean', 'max', 'std']).reset_index()
speed_stats.columns = ['race', 'ship_name', 'avg_speed', 'max_speed', 'std_speed']

team_speeds = speed_stats[speed_stats['ship_name'] == TEAM_NAAM].set_index('race')
fleet_avg = speed_stats.groupby('race')['avg_speed'].mean()

fig, ax = plt.subplots(figsize=(12, 6))
races = sorted(df_all['race'].unique())
x = range(len(races))

fleet_values = [fleet_avg.get(r, 0) for r in races]
ax.bar([i - 0.2 for i in x], fleet_values, 0.4, label='Vloot gemiddelde', color=OTHER_COLOR)

team_values = [team_speeds.loc[r, 'avg_speed'] if r in team_speeds.index else 0 for r in races]
ax.bar([i + 0.2 for i in x], team_values, 0.4, label=TEAM_NAAM, color=TEAM_COLOR)

ax.set_xlabel('Wedstrijd')
ax.set_ylabel('Gemiddelde snelheid')
ax.set_title(f'Gemiddelde Snelheid per Wedstrijd: {TEAM_NAAM} vs Vloot')
ax.set_xticks(x)
ax.set_xticklabels([r.replace('Match', 'M') for r in races], rotation=45, ha='right')
ax.legend()
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '1_snelheid_per_wedstrijd.png', bbox_inches='tight')
plt.close()

# =============================================================================
# ANALYSE 2: TRUE WIND ANGLE
# =============================================================================

print("🌬️ Analyse 2: Windhoek berekenen...")

twa_data = []

for race_name in all_races.keys():
    race_df = all_races[race_name]
    wind_df = all_wind[race_name]

    if len(wind_df) == 0:
        continue

    team_race = race_df[race_df['ship_name'] == TEAM_NAAM].copy()

    avg_wind_dir = wind_df.groupby('timestamp')['wind_direction'].apply(
        lambda x: np.degrees(np.arctan2(np.mean(np.sin(np.radians(x))), np.mean(np.cos(np.radians(x))))) % 360
    )
    avg_wind_speed = wind_df.groupby('timestamp')['wind_speed'].mean()

    for _, row in team_race.iterrows():
        closest_ts = avg_wind_dir.index[np.abs(avg_wind_dir.index - row['timestamp']).argmin()]
        wind_dir = avg_wind_dir[closest_ts]
        wind_spd = avg_wind_speed.get(closest_ts, np.nan)

        twa = calculate_twa(row['course'], wind_dir)

        twa_data.append({
            'race': race_name,
            'timestamp': row['timestamp'],
            'speed': row['speed'],
            'course': row['course'],
            'wind_direction': wind_dir,
            'wind_speed': wind_spd,
            'twa': twa
        })

df_twa = pd.DataFrame(twa_data)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

ax1 = axes[0]
ax1.hist(df_twa['twa'], bins=36, range=(0, 180), color=TEAM_COLOR, edgecolor='white', alpha=0.7)
ax1.axvline(45, color='red', linestyle='--', label='Aan de wind (45°)')
ax1.axvline(90, color='orange', linestyle='--', label='Halve wind (90°)')
ax1.axvline(135, color='green', linestyle='--', label='Ruime wind (135°)')
ax1.set_xlabel('True Wind Angle (graden)')
ax1.set_ylabel('Frequentie')
ax1.set_title(f'Verdeling Windhoek - {TEAM_NAAM}')
ax1.legend()

ax2 = axes[1]
df_twa.boxplot(column='twa', by='race', ax=ax2)
ax2.set_xlabel('Wedstrijd')
ax2.set_ylabel('True Wind Angle (graden)')
ax2.set_title(f'Windhoek per Wedstrijd')
plt.suptitle('')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '2_windhoek_analyse.png', bbox_inches='tight')
plt.close()

# =============================================================================
# ANALYSE 3: POLAR DIAGRAM
# =============================================================================

print("🧭 Analyse 3: Polar diagram...")

df_twa['twa_bin'] = pd.cut(df_twa['twa'], bins=range(0, 190, 10), labels=range(5, 185, 10))
polar_data = df_twa.groupby('twa_bin', observed=True)['speed'].agg(['mean', 'std', 'count']).reset_index()
polar_data.columns = ['twa', 'avg_speed', 'std_speed', 'count']
polar_data['twa'] = polar_data['twa'].astype(float)
polar_data = polar_data[polar_data['count'] >= 10]

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

ax1 = axes[0]
ax1.fill_between(polar_data['twa'],
                  polar_data['avg_speed'] - polar_data['std_speed'],
                  polar_data['avg_speed'] + polar_data['std_speed'],
                  alpha=0.3, color=TEAM_COLOR)
ax1.plot(polar_data['twa'], polar_data['avg_speed'], 'o-', color=TEAM_COLOR, linewidth=2)
ax1.set_xlabel('True Wind Angle (graden)')
ax1.set_ylabel('Gemiddelde Snelheid')
ax1.set_title(f'Snelheid vs Windhoek - {TEAM_NAAM}')
ax1.grid(alpha=0.3)
ax1.set_xlim(0, 180)

ax2 = plt.subplot(122, projection='polar')
theta = np.radians(polar_data['twa'])
r = polar_data['avg_speed']
ax2.plot(theta, r, 'o-', color=TEAM_COLOR, linewidth=2, label='Stuurboord')
ax2.plot(-theta, r, 'o-', color=TEAM_COLOR, linewidth=2, alpha=0.5, label='Bakboord')
ax2.set_theta_zero_location('N')
ax2.set_theta_direction(-1)
ax2.set_thetamin(-180)
ax2.set_thetamax(180)
ax2.set_title(f'Polar Diagram - {TEAM_NAAM}', pad=20)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '3_polar_diagram.png', bbox_inches='tight')
plt.close()

# =============================================================================
# ANALYSE 4: RANKING
# =============================================================================

print("🏆 Analyse 4: Ranking...")

overall_speed = df_all.groupby('ship_name')['speed'].agg(['mean', 'max', 'std', 'count']).reset_index()
overall_speed.columns = ['ship_name', 'avg_speed', 'max_speed', 'std_speed', 'data_points']
overall_speed = overall_speed.sort_values('avg_speed', ascending=False)
overall_speed['rank'] = range(1, len(overall_speed) + 1)

team_rank = overall_speed[overall_speed['ship_name'] == TEAM_NAAM]['rank'].values[0]

fig, ax = plt.subplots(figsize=(12, 8))
colors = [TEAM_COLOR if name == TEAM_NAAM else OTHER_COLOR for name in overall_speed['ship_name']]
ax.barh(overall_speed['ship_name'], overall_speed['avg_speed'], color=colors)

team_speed = overall_speed[overall_speed['ship_name'] == TEAM_NAAM]['avg_speed'].values[0]
ax.axvline(team_speed, color='red', linestyle='--', alpha=0.5)

ax.set_xlabel('Gemiddelde Snelheid')
ax.set_ylabel('Schip')
ax.set_title(f'Snelheidsranking - {TEAM_NAAM} staat #{team_rank}')
ax.invert_yaxis()
ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '4_ranking.png', bbox_inches='tight')
plt.close()

# Ranking per wedstrijd
race_rankings = []
for race in df_all['race'].unique():
    race_speeds = df_all[df_all['race'] == race].groupby('ship_name')['speed'].mean().sort_values(ascending=False)
    for rank, (ship, speed) in enumerate(race_speeds.items(), 1):
        race_rankings.append({'race': race, 'ship_name': ship, 'avg_speed': speed, 'rank': rank})

df_rankings = pd.DataFrame(race_rankings)
team_rankings = df_rankings[df_rankings['ship_name'] == TEAM_NAAM].sort_values('race')

fig, ax = plt.subplots(figsize=(12, 5))
races = sorted(team_rankings['race'].unique())
ranks = [team_rankings[team_rankings['race'] == r]['rank'].values[0] for r in races]

ax.plot(races, ranks, 'o-', color=TEAM_COLOR, linewidth=2, markersize=10)
ax.axhline(y=np.mean(ranks), color='red', linestyle='--', alpha=0.5, label=f'Gemiddelde: {np.mean(ranks):.1f}')

ax.set_xlabel('Wedstrijd')
ax.set_ylabel('Ranking (lager is beter)')
ax.set_title(f'Ranking per Wedstrijd - {TEAM_NAAM}')
ax.invert_yaxis()
ax.set_ylim(16.5, 0.5)
ax.set_yticks(range(1, 17))
ax.legend()
ax.grid(alpha=0.3)

plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '5_ranking_per_wedstrijd.png', bbox_inches='tight')
plt.close()

# =============================================================================
# ANALYSE 5: VMG
# =============================================================================

print("🎯 Analyse 5: VMG analyse...")

df_twa['vmg_upwind'] = df_twa['speed'] * np.cos(np.radians(df_twa['twa']))
df_twa['vmg_downwind'] = df_twa['speed'] * np.cos(np.radians(180 - df_twa['twa']))
df_twa['sailing_mode'] = np.where(df_twa['twa'] < 90, 'Upwind', 'Downwind')

vmg_by_twa = df_twa.groupby('twa_bin', observed=True).agg({
    'vmg_upwind': 'mean',
    'vmg_downwind': 'mean',
    'speed': 'mean',
    'twa': 'count'
}).reset_index()
vmg_by_twa.columns = ['twa_bin', 'vmg_upwind', 'vmg_downwind', 'boat_speed', 'count']
vmg_by_twa['twa'] = vmg_by_twa['twa_bin'].astype(float)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

ax1 = axes[0]
upwind_data = vmg_by_twa[vmg_by_twa['twa'] < 90]
downwind_data = vmg_by_twa[vmg_by_twa['twa'] >= 90]

ax1.plot(upwind_data['twa'], upwind_data['vmg_upwind'], 'o-', color='blue', label='Upwind VMG', linewidth=2)
ax1.plot(downwind_data['twa'], downwind_data['vmg_downwind'], 'o-', color='red', label='Downwind VMG', linewidth=2)
ax1.axhline(0, color='gray', linestyle='-', alpha=0.3)
ax1.set_xlabel('True Wind Angle (graden)')
ax1.set_ylabel('VMG')
ax1.set_title(f'VMG vs Windhoek - {TEAM_NAAM}')
ax1.legend()
ax1.grid(alpha=0.3)

ax2 = axes[1]
upwind = df_twa[df_twa['sailing_mode'] == 'Upwind']['vmg_upwind']
downwind = df_twa[df_twa['sailing_mode'] == 'Downwind']['vmg_downwind']

ax2.hist(upwind, bins=30, alpha=0.7, label=f'Upwind VMG (gem: {upwind.mean():.1f})', color='blue')
ax2.hist(downwind, bins=30, alpha=0.7, label=f'Downwind VMG (gem: {downwind.mean():.1f})', color='red')
ax2.set_xlabel('VMG')
ax2.set_ylabel('Frequentie')
ax2.set_title(f'VMG Distributie - {TEAM_NAAM}')
ax2.legend()

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '6_vmg_analyse.png', bbox_inches='tight')
plt.close()

# =============================================================================
# MARKDOWN RAPPORT GENEREREN
# =============================================================================

print("📝 Markdown rapport genereren...")

# Bereken statistieken
best_upwind_idx = upwind_data['vmg_upwind'].idxmax() if len(upwind_data) > 0 else None
best_downwind_idx = downwind_data['vmg_downwind'].idxmax() if len(downwind_data) > 0 else None

upwind_pct = (df_twa['twa'] < 90).mean() * 100
downwind_pct = (df_twa['twa'] >= 90).mean() * 100

speed_table = ""
for race in races:
    team_avg = team_speeds.loc[race, 'avg_speed'] if race in team_speeds.index else 0
    fleet = fleet_avg.get(race, 0)
    diff = team_avg - fleet
    diff_pct = (diff / fleet * 100) if fleet > 0 else 0
    speed_table += f"| {race} | {team_avg:.1f} | {fleet:.1f} | {diff:+.1f} ({diff_pct:+.1f}%) |\n"

ranking_table = ""
for race, rank in zip(races, ranks):
    total_ships = len(df_rankings[df_rankings['race'] == race])
    ranking_table += f"| {race} | #{rank} van {total_ships} |\n"

markdown = f"""# IFKS 2025 Analyse Rapport
## {TEAM_NAAM}

*Gegenereerd op {datetime.now().strftime('%d-%m-%Y %H:%M')}*

---

## Samenvatting

| Statistiek | Waarde |
|------------|--------|
| Wedstrijden gevaren | {len(all_races)} |
| Totaal datapunten | {len(df_team):,} |
| Gemiddelde snelheid | {df_team['speed'].mean():.1f} |
| Maximum snelheid | {df_team['speed'].max():.0f} |
| Overall ranking | #{team_rank} van {len(overall_speed)} |
| Gemiddelde TWA | {df_twa['twa'].mean():.1f}° |
| Upwind tijd | {upwind_pct:.1f}% |
| Downwind tijd | {downwind_pct:.1f}% |

---

## 1. Snelheid per Wedstrijd

Vergelijking van de gemiddelde snelheid van {TEAM_NAAM} met het vlootgemiddelde.

![Snelheid per wedstrijd](rapport_output/1_snelheid_per_wedstrijd.png)

| Wedstrijd | {TEAM_NAAM} | Vloot | Verschil |
|-----------|-------------|-------|----------|
{speed_table}

---

## 2. Windhoek Analyse (True Wind Angle)

De True Wind Angle (TWA) geeft aan onder welke hoek er ten opzichte van de wind wordt gevaren:
- **0-60°**: Aan de wind (kruisen)
- **60-120°**: Halve wind
- **120-180°**: Ruime wind / voor de wind

![Windhoek analyse](rapport_output/2_windhoek_analyse.png)

**Verdeling:**
- Aan de wind (0-60°): {((df_twa['twa'] >= 0) & (df_twa['twa'] < 60)).mean() * 100:.1f}%
- Halve wind (60-120°): {((df_twa['twa'] >= 60) & (df_twa['twa'] < 120)).mean() * 100:.1f}%
- Ruime wind (120-180°): {((df_twa['twa'] >= 120) & (df_twa['twa'] <= 180)).mean() * 100:.1f}%

---

## 3. Polar Diagram

Het polar diagram toont de gemiddelde snelheid bij verschillende windhoeken.

![Polar diagram](rapport_output/3_polar_diagram.png)

**Optimale hoeken:**
- Hoogste snelheid: {polar_data['avg_speed'].max():.1f} bij {polar_data.loc[polar_data['avg_speed'].idxmax(), 'twa']:.0f}°

---

## 4. Ranking

### Overall Ranking (op basis van gemiddelde snelheid)

![Ranking](rapport_output/4_ranking.png)

**{TEAM_NAAM} staat #{team_rank} van {len(overall_speed)} schepen.**

### Ranking per Wedstrijd

![Ranking per wedstrijd](rapport_output/5_ranking_per_wedstrijd.png)

| Wedstrijd | Positie |
|-----------|---------|
{ranking_table}

**Gemiddelde ranking: {np.mean(ranks):.1f}**

---

## 5. VMG Analyse (Velocity Made Good)

VMG meet de effectieve snelheid richting de wind:
- **Upwind VMG**: Hoe snel je tegen de wind in komt
- **Downwind VMG**: Hoe snel je met de wind mee komt

![VMG analyse](rapport_output/6_vmg_analyse.png)

**Optimale VMG hoeken:**
- Beste upwind hoek: {vmg_by_twa.loc[best_upwind_idx, 'twa']:.0f}° (VMG: {vmg_by_twa.loc[best_upwind_idx, 'vmg_upwind']:.1f})
- Beste downwind hoek: {vmg_by_twa.loc[best_downwind_idx, 'twa']:.0f}° (VMG: {vmg_by_twa.loc[best_downwind_idx, 'vmg_downwind']:.1f})

---

## Wedstrijdoverzicht

| Wedstrijd | Datum | Locatie | Duur (min) |
|-----------|-------|---------|------------|
"""

for info in race_info:
    locatie = info['race'].split('-')[-1] if '-' in info['race'] else info['race']
    markdown += f"| {info['race']} | {info['start'].strftime('%d-%m-%Y')} | {locatie} | {info['duration_min']:.0f} |\n"

markdown += """
---

*Dit rapport is automatisch gegenereerd op basis van GPS-tracking data van de IFKS 2025.*
"""

with open('rapport_drie_gebroeders.md', 'w') as f:
    f.write(markdown)

print("\n" + "="*60)
print("✅ RAPPORT GEREED!")
print("="*60)
print(f"\n📄 Markdown rapport: rapport_drie_gebroeders.md")
print(f"📁 Afbeeldingen: {OUTPUT_DIR}/")
print("\nOm naar PDF te converteren:")
print("  1. Open rapport_drie_gebroeders.md in VS Code")
print("  2. Gebruik 'Markdown PDF' extensie, of")
print("  3. Print naar PDF vanuit je browser")
