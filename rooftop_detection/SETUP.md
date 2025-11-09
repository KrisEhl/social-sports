# Quick Setup Guide

## 1. Clone the Repository
```bash
git clone <repository-url>
cd challenge-02-sports-mapping
```

## 2. Install Dependencies
```bash
pip install -r requirements.txt
```

## 3. Configure Credentials
Copy the template and add your credentials:
```bash
cp copernicus_credentials.json.template copernicus_credentials.json
```

Edit `copernicus_credentials.json` with your Copernicus Data Space credentials.

## 4. Run the App
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## 5. Using Existing Results
If the repository includes pre-computed results in the `results/` folder, you can view them immediately without running detection. Simply:
1. Open the app
2. Select a city/district
3. View the results if the "✅ Results available" message appears

To re-process an area, click "🔄 Re-run Detection"

## Troubleshooting

**"No module named 'streamlit'"**
- Install dependencies: `pip install -r requirements.txt`

**"Authentication failed"**
- Check your credentials in `copernicus_credentials.json`
- Verify your Copernicus Data Space account is active

**"Results not loading"**
- Check that `results/` folder contains `.geojson` files
- Verify the file naming matches: `{city}_rooftops.geojson`
