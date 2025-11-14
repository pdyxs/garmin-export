from garminconnect import Garmin
from datetime import date, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os
import json

# Configuration from environment variables
GARMIN_USERNAME = os.environ.get('GARMIN_USERNAME')
GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD')
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
SHEET_NAME = os.environ.get('SHEET_NAME', 'Sheet1')  # Default to 'Sheet1' if not specified
GOOGLE_SHEETS_CREDENTIALS = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
USER_AGE = int(os.environ.get('USER_AGE', '38'))
USER_MAX_HR = os.environ.get('USER_MAX_HR')

# Convert USER_MAX_HR to int if provided, otherwise None
if USER_MAX_HR:
  USER_MAX_HR = int(USER_MAX_HR)

# Number of days to fetch and update (last 7 days)
DAYS_TO_FETCH = 7

# Calculate max heart rate
if USER_MAX_HR is None:
  MAX_HR = 220 - USER_AGE
else:
  MAX_HR = USER_MAX_HR

# Define heart rate zones
ZONES = {
  'zone_1_rest': (0, int(MAX_HR * 0.60)),
  'zone_2_easy': (int(MAX_HR * 0.60), int(MAX_HR * 0.70)),
  'zone_3_aerobic': (int(MAX_HR * 0.70), int(MAX_HR * 0.80)),
  'zone_4_threshold': (int(MAX_HR * 0.80), int(MAX_HR * 0.90)),
  'zone_5_max': (int(MAX_HR * 0.90), 300)
}

print(f"Using Max HR: {MAX_HR} bpm")
print(f"Heart Rate Zones:")
for zone_name, (lower, upper) in ZONES.items():
  print(f"  {zone_name}: {lower}-{upper} bpm")
print()

# Connect to Garmin API
print("Connecting to Garmin Connect...")
try:
  api = Garmin(GARMIN_USERNAME, GARMIN_PASSWORD)
  api.login()
  print("Successfully connected to Garmin Connect")
except Exception as e:
  print(f"Error connecting to Garmin: {e}")
  exit(1)

# Connect to Google Sheets
print("Connecting to Google Sheets...")
try:
  # Parse credentials from environment variable
  creds_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)

  # Set up credentials with proper scopes
  scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
  ]

  credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
  gc = gspread.authorize(credentials)

  # Open the spreadsheet
  spreadsheet = gc.open_by_key(SPREADSHEET_ID)
  worksheet = spreadsheet.worksheet(SHEET_NAME)

  print(f"Successfully connected to spreadsheet: {spreadsheet.title}")
  print(f"Using sheet: {SHEET_NAME}")
except Exception as e:
  print(f"Error connecting to Google Sheets: {e}")
  exit(1)

# Define column order (must match spreadsheet headers)
FIELDNAMES = ['date',
              'sleep_score', 'sleep_duration_hours',
              'hrv_last_night_avg', 'hrv_last_night_5min_high', 'hrv_weekly_avg', 'hrv_status',
              'resting_heart_rate', 'max_heart_rate', 'min_heart_rate',
              'zone_1_minutes', 'zone_2_minutes', 'zone_3_minutes', 'zone_4_minutes', 'zone_5_minutes',
              'avg_stress_level', 'max_stress_level',
              'body_battery_charged', 'body_battery_drained', 'body_battery_highest', 'body_battery_lowest',
              'vigorous_intensity_minutes', 'moderate_intensity_minutes']

# Fetch data for the last 7 days
print(f"\nFetching data for the past {DAYS_TO_FETCH} days...")
data_rows = []

for day_offset in range(DAYS_TO_FETCH):
  current_date = date.today() - timedelta(days=day_offset)
  date_str = current_date.isoformat()

  print(f"Fetching data for {date_str}...")

  row = {
    'date': date_str,
    'sleep_score': None,
    'sleep_duration_hours': None,
    'hrv_last_night_avg': None,
    'hrv_last_night_5min_high': None,
    'hrv_weekly_avg': None,
    'hrv_status': None,
    'resting_heart_rate': None,
    'max_heart_rate': None,
    'min_heart_rate': None,
    'zone_1_minutes': 0,
    'zone_2_minutes': 0,
    'zone_3_minutes': 0,
    'zone_4_minutes': 0,
    'zone_5_minutes': 0,
    'avg_stress_level': None,
    'max_stress_level': None,
    'body_battery_charged': None,
    'body_battery_drained': None,
    'body_battery_highest': None,
    'body_battery_lowest': None,
    'vigorous_intensity_minutes': None,
    'moderate_intensity_minutes': None
  }

  # Fetch HRV data
  try:
    hrv = api.get_hrv_data(date_str)
    if hrv and 'hrvSummary' in hrv:
      row['hrv_last_night_avg'] = hrv['hrvSummary'].get('lastNightAvg')
      row['hrv_last_night_5min_high'] = hrv['hrvSummary'].get('lastNight5MinHigh')
      row['hrv_weekly_avg'] = hrv['hrvSummary'].get('weeklyAvg')
      row['hrv_status'] = hrv['hrvSummary'].get('status')
  except Exception as e:
    print(f"  Error fetching HRV data: {e}")

  # Fetch sleep data
  try:
    sleep = api.get_sleep_data(date_str)
    if sleep and 'dailySleepDTO' in sleep:
      daily_sleep = sleep['dailySleepDTO']
      row['sleep_score'] = daily_sleep.get('sleepScores', {}).get('overall', {}).get('value')

      sleep_time_seconds = daily_sleep.get('sleepTimeSeconds')
      if sleep_time_seconds:
        row['sleep_duration_hours'] = round(sleep_time_seconds / 3600, 2)
  except Exception as e:
    print(f"  Error fetching sleep data: {e}")

  # Fetch heart rate data
  try:
    heart_rate = api.get_heart_rates(date_str)
    if heart_rate:
      row['resting_heart_rate'] = heart_rate.get('restingHeartRate')
      row['max_heart_rate'] = heart_rate.get('maxHeartRate')
      row['min_heart_rate'] = heart_rate.get('minHeartRate')

      # Calculate time in each heart rate zone
      hr_values = heart_rate.get('heartRateValues')
      if hr_values:
        timestamps = []
        zone_counts = {
          'zone_1_rest': 0,
          'zone_2_easy': 0,
          'zone_3_aerobic': 0,
          'zone_4_threshold': 0,
          'zone_5_max': 0
        }

        for item in hr_values:
          hr_value = None
          timestamp = None

          if isinstance(item, list) and len(item) >= 2:
            timestamp = item[0]
            hr_value = item[1]
          elif isinstance(item, dict):
            timestamp = item.get('timestamp')
            hr_value = item.get('value') or item.get('heartRate')
          elif isinstance(item, (int, float)):
            hr_value = item

          if timestamp:
            timestamps.append(timestamp)

          if hr_value and isinstance(hr_value, (int, float)) and hr_value > 0:
            for zone_name, (lower, upper) in ZONES.items():
              if lower <= hr_value < upper:
                zone_counts[zone_name] += 1
                break

        # Calculate average sampling interval
        if len(timestamps) >= 2:
          intervals = []
          for i in range(1, min(10, len(timestamps))):
            interval = (timestamps[i] - timestamps[i-1]) / 1000
            if interval > 0:
              intervals.append(interval)

          if intervals:
            avg_interval_seconds = sum(intervals) / len(intervals)
            samples_per_minute = 60 / avg_interval_seconds
          else:
            samples_per_minute = 12
        else:
          samples_per_minute = 12

        row['zone_1_minutes'] = round(zone_counts['zone_1_rest'] / samples_per_minute, 1)
        row['zone_2_minutes'] = round(zone_counts['zone_2_easy'] / samples_per_minute, 1)
        row['zone_3_minutes'] = round(zone_counts['zone_3_aerobic'] / samples_per_minute, 1)
        row['zone_4_minutes'] = round(zone_counts['zone_4_threshold'] / samples_per_minute, 1)
        row['zone_5_minutes'] = round(zone_counts['zone_5_max'] / samples_per_minute, 1)

  except Exception as e:
    print(f"  Error fetching heart rate data: {e}")

  # Fetch intensity minutes
  try:
    stats = api.get_stats(date_str)
    if stats:
      row['vigorous_intensity_minutes'] = stats.get('vigorousIntensityMinutes')
      row['moderate_intensity_minutes'] = stats.get('moderateIntensityMinutes')
  except Exception as e:
    print(f"  Error fetching intensity minutes: {e}")

  # Fetch stress data
  try:
    stress = api.get_stress_data(date_str)
    if stress:
      row['avg_stress_level'] = stress.get('avgStressLevel')
      row['max_stress_level'] = stress.get('maxStressLevel')
  except Exception as e:
    print(f"  Error fetching stress data: {e}")

  # Fetch body battery data
  try:
    body_battery = api.get_body_battery(date_str)
    if body_battery and len(body_battery) > 0:
      bb_data = body_battery[0]
      row['body_battery_charged'] = bb_data.get('charged')
      row['body_battery_drained'] = bb_data.get('drained')

      bb_values = bb_data.get('bodyBatteryValuesArray', [])
      if bb_values:
        values = []
        for item in bb_values:
          if isinstance(item, list) and len(item) >= 2:
            values.append(item[1])
          elif isinstance(item, dict):
            val = item.get('value') or item.get('bodyBatteryValue')
            if val is not None:
              values.append(val)

        if values:
          row['body_battery_highest'] = max(values)
          row['body_battery_lowest'] = min(values)
  except Exception as e:
    print(f"  Error fetching body battery data: {e}")

  data_rows.append(row)

# Update Google Sheets with upsert logic
print("\nUpdating Google Sheets...")

try:
  # Get all existing data from the sheet
  all_values = worksheet.get_all_values()

  if not all_values:
    print("ERROR: Spreadsheet is empty. Please ensure headers are set up.")
    exit(1)

  headers = all_values[0]
  existing_data = all_values[1:]  # Skip header row

  # Create a dictionary of existing data by date
  existing_by_date = {}
  for i, row_data in enumerate(existing_data):
    if row_data and row_data[0]:  # Check if date column exists
      row_num = i + 2  # +2 because row 1 is headers and sheets are 1-indexed
      existing_by_date[row_data[0]] = row_num

  print(f"Found {len(existing_by_date)} existing rows in spreadsheet")

  # Update or append each new row
  updates_count = 0
  inserts_count = 0

  for row in data_rows:
    date_str = row['date']

    # Convert row dict to list in correct column order, preserving types
    row_values = []
    for field in FIELDNAMES:
      value = row.get(field)
      if value is None or value == '':
        row_values.append('')
      else:
        row_values.append(value)  # Keep original type (int, float, str)

    if date_str in existing_by_date:
      # Update existing row
      row_num = existing_by_date[date_str]
      worksheet.update(f'A{row_num}', [row_values], value_input_option='USER_ENTERED')
      print(f"  Updated row {row_num} for {date_str}")
      updates_count += 1
    else:
      # Append new row
      worksheet.append_row(row_values, value_input_option='USER_ENTERED')
      print(f"  Inserted new row for {date_str}")
      inserts_count += 1

  print(f"\nSync complete!")
  print(f"  Updated: {updates_count} rows")
  print(f"  Inserted: {inserts_count} rows")
  print(f"  Total processed: {len(data_rows)} days")

except Exception as e:
  print(f"Error updating Google Sheets: {e}")
  exit(1)
