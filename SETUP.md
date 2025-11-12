# Garmin to Google Sheets - Automated Sync Setup

This guide will help you set up automated daily syncing of your Garmin health data to Google Sheets using GitHub Actions.

## Overview

The system will:
- Run automatically every day at 6 AM UTC
- Fetch the last 7 days of Garmin data
- Update existing rows in your Google Sheet (preserving all historical data)
- Add new rows if they don't exist yet

## Prerequisites

- A GitHub account
- A Google account with access to Google Sheets
- Your existing Google Spreadsheet with Garmin data

## Step 1: Google Cloud Setup

### 1.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name it "Garmin Data Sync" (or your preference)
4. Click "Create"

### 1.2 Enable Google Sheets API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Sheets API"
3. Click on it and press "Enable"

### 1.3 Create Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Name: `garmin-sync-bot`
4. Click "Create and Continue"
5. Skip the optional role/access steps (click "Continue" → "Done")

### 1.4 Create Service Account Key

1. Click on the service account you just created
2. Go to the "Keys" tab
3. Click "Add Key" → "Create new key"
4. Select "JSON"
5. Click "Create" - a JSON file will download
6. **Save this file securely** - you'll need it later

### 1.5 Share Your Spreadsheet

1. Open the JSON file you just downloaded
2. Find the `client_email` field (looks like: `garmin-sync-bot@your-project.iam.gserviceaccount.com`)
3. Copy this email address
4. Open your Google Spreadsheet
5. Click "Share" button
6. Paste the service account email
7. Give it "Editor" permissions
8. Uncheck "Notify people"
9. Click "Share"

## Step 2: Get Your Spreadsheet ID

1. Open your Google Spreadsheet
2. Look at the URL: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit`
3. Copy the long string between `/d/` and `/edit` - this is your Spreadsheet ID
4. Save it for later

## Step 3: GitHub Repository Setup

### 3.1 Push Your Code to GitHub

If you haven't already:

```bash
cd c:\Users\pdyxs\dev\garmin-export
git init
git add .
git commit -m "Initial commit - Garmin to Google Sheets sync"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/garmin-export.git
git push -u origin main
```

### 3.2 Configure GitHub Secrets

1. Go to your GitHub repository
2. Click "Settings" → "Secrets and variables" → "Actions"
3. Click "New repository secret" for each of the following:

#### Required Secrets:

**GARMIN_USERNAME**
- Value: Your Garmin Connect email address

**GARMIN_PASSWORD**
- Value: Your Garmin Connect password

**GOOGLE_SHEETS_CREDENTIALS**
- Value: The **entire contents** of your service account JSON file
- Open the JSON file in a text editor
- Copy everything (from `{` to `}` including brackets)
- Paste it as the secret value

**SPREADSHEET_ID**
- Value: Your Spreadsheet ID from Step 2
- Example: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`

**SHEET_NAME** (optional)
- Value: The name of the specific sheet/tab to use
- Example: `Garmin Data` or `Health Metrics`
- Default: `Sheet1` (if not specified)
- To find: Look at the tabs at the bottom of your spreadsheet

**USER_AGE**
- Value: Your age
- Example: `38`

**USER_MAX_HR** (optional)
- Value: Your known max heart rate
- Example: `160`
- Leave empty if you want it calculated from age (220 - age)

## Step 4: Prepare Your Spreadsheet

Make sure your spreadsheet has these headers in the first row (in this exact order):

```
date, sleep_score, sleep_duration_hours, hrv_last_night_avg, hrv_last_night_5min_high, hrv_weekly_avg, hrv_status, resting_heart_rate, max_heart_rate, min_heart_rate, zone_1_minutes, zone_2_minutes, zone_3_minutes, zone_4_minutes, zone_5_minutes, avg_stress_level, max_stress_level, body_battery_charged, body_battery_drained, body_battery_highest, body_battery_lowest, vigorous_intensity_minutes, moderate_intensity_minutes
```

Your existing data should already be in this format if you used the original `garmin.py` script.

## Step 5: Test the Setup

### 5.1 Manual Test Run

1. Go to your GitHub repository
2. Click "Actions" tab
3. Click "Daily Garmin to Google Sheets Sync" workflow
4. Click "Run workflow" dropdown
5. Click the green "Run workflow" button
6. Wait for the workflow to complete (usually 2-5 minutes)
7. Check your Google Spreadsheet - the last 7 days should be updated!

### 5.2 Check the Logs

1. Click on the workflow run to see details
2. Click on the "sync" job
3. Expand each step to see what happened
4. Look for success messages like "Updated row X for YYYY-MM-DD"

## Step 6: Verify Daily Automation

The workflow is now set to run automatically every day at 6 AM UTC. To verify:

1. Wait for the next scheduled run (or check the next day)
2. Go to "Actions" tab to see the run history
3. Verify your spreadsheet is being updated daily

## Troubleshooting

### "Error connecting to Garmin"
- Check your GARMIN_USERNAME and GARMIN_PASSWORD secrets
- Verify you can log in to Garmin Connect manually
- Garmin may require 2FA - you might need an app password

### "Error connecting to Google Sheets"
- Verify GOOGLE_SHEETS_CREDENTIALS is the complete JSON
- Check that the service account email has Editor access to your sheet
- Verify SPREADSHEET_ID is correct

### "Spreadsheet is empty"
- Ensure your spreadsheet has headers in the first row
- Make sure you're using the correct sheet (first sheet/tab)

### Manual Local Testing

You can test locally before pushing to GitHub:

```bash
# Set environment variables (Windows)
set GARMIN_USERNAME=your_email
set GARMIN_PASSWORD=your_password
set GOOGLE_SHEETS_CREDENTIALS={"type":"service_account",...}
set SPREADSHEET_ID=your_sheet_id
set SHEET_NAME=Sheet1
set USER_AGE=38
set USER_MAX_HR=160

# Run the script
python sync_to_sheets.py
```

## Customization

### Change Schedule

Edit `.github/workflows/daily-sync.yml`:

```yaml
schedule:
  - cron: '0 6 * * *'  # Change this line
```

Examples:
- `'0 6 * * *'` - 6 AM UTC daily
- `'0 12 * * *'` - 12 PM UTC daily
- `'0 */12 * * *'` - Every 12 hours
- `'0 8 * * 1,3,5'` - 8 AM UTC on Mon, Wed, Fri

### Change Number of Days

Edit `sync_to_sheets.py`, line 21:

```python
DAYS_TO_FETCH = 7  # Change this number
```

## Support

If you encounter issues:

1. Check the GitHub Actions logs for error messages
2. Verify all secrets are set correctly
3. Test locally first to isolate the issue
4. Check that your spreadsheet structure matches the headers

## Security Notes

- Never commit credentials or the service account JSON file to git
- The `.gitignore` file is set up to prevent this
- GitHub Secrets are encrypted and only accessible to your workflows
- Consider rotating your Garmin password periodically
