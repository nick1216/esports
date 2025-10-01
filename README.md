# ⚡ Esports EV Finder

Find positive Expected Value (EV) betting opportunities by comparing Pinnacle's sharp odds with CS500 soft book odds.

## 🎯 Features

- **Real-time Odds Comparison**: Compare Pinnacle (sharp) with CS500 (soft book)
- **EV Calculation**: Automatic expected value calculations using de-vigged odds
- **Bet Tracking**: Log and track all your bets with results
- **Closing Line Value (CLV)**: Track your CLV to measure betting skill
- **Match Archive**: Historical data of all past matches with EV data
- **Beautiful Dashboard**: Modern UI with charts and analytics
- **Automatic Scraping**: Scheduled odds updates every 5 minutes
- **Multiple Sports**: CS2 and League of Legends support

## 📊 What is EV?

Expected Value (EV) measures the theoretical profit/loss of a bet over the long term. A +5% EV bet means you expect to profit 5% of your stake over many repetitions.

**Formula**: EV = (Fair Probability × Payout) - 1

## 🚀 Quick Start (Railway Deployment)

### Prerequisites

- GitHub account
- Railway account (sign up at [railway.app](https://railway.app))

### Deploy in 5 Minutes

1. **Push to GitHub**:

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

2. **Deploy on Railway**:

   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway auto-detects the Dockerfile and deploys!

3. **Access your app**:
   - Railway provides a public URL
   - Click "View Logs" to monitor deployment
   - App will be live in ~3-5 minutes

### Environment Variables (Optional)

Railway auto-detects most settings. If needed, add:

- `PORT` - Auto-injected by Railway (default: 8000)
- `DISPLAY` - Set to `:99` (for headless browser)

## 🎮 Usage

### Main Dashboard

- View current EV opportunities
- Filter by sport (CS2/LoL) or minimum EV
- Click "Bet" to log a bet

### Bet Logs

- Track all your bets
- View performance metrics (ROI, CLV, Total EV)
- Update bet results with dropdown
- Analyze with charts (EV vs AV, CLV tracking, etc.)

### Archive

- Historical match data
- Closing line movements
- Filter by sport or date range
- Clear archive as needed

## 📈 Key Metrics Explained

- **EV %**: Expected value as percentage of stake
- **EV $**: Expected value in dollar amount
- **CLV**: Closing Line Value - compares your bet odds to closing odds
- **+CLV Rate**: Percentage of bets beating the closing line
- **ROI**: Return on Investment from settled bets

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla JavaScript with Chart.js
- **Database**: SQLite
- **Scraping**: nodriver (Chrome automation)
- **Scheduler**: APScheduler
- **Deployment**: Docker on Railway

## 📖 API Endpoints

### Markets

- `GET /api/markets` - Get matched markets with EV
- `GET /api/markets/positive` - Get only +EV markets
- `POST /api/scrape/all` - Trigger manual scrape

### Bets

- `GET /api/bets` - Get all bets
- `POST /api/bets` - Place a new bet
- `PUT /api/bets/{id}` - Update bet result

### Archive

- `GET /api/archive/matches` - Get archived matches
- `DELETE /api/archive/clear` - Clear all archive

### Stats

- `GET /api/stats` - Market statistics
- `GET /api/bets/stats/summary` - Betting statistics

## 🔧 Development

### Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
uvicorn api:app --reload
```

### Run with Docker

```bash
docker build -t esports-ev .
docker run -p 8000:8000 esports-ev
```

## 💰 Pricing (Railway)

- **Hobby Plan**: $5/month
- **Recommended**: 1GB RAM ($7/month total)
- **First $5 FREE** for new accounts

## 🤝 Contributing

This is a personal project, but suggestions are welcome!

## ⚖️ Disclaimer

This tool is for educational and analytical purposes. Always gamble responsibly and within your means. Past performance does not guarantee future results.

## 📝 License

MIT License - feel free to use and modify as needed.

## 🔗 Links

- [Railway Documentation](https://docs.railway.app)
- [Pinnacle](https://www.pinnacle.com)
- [FastAPI Docs](https://fastapi.tiangolo.com)

---

**Built with ❤️ for finding +EV opportunities**
