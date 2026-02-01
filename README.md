# Real-Time Risk Streaming Dashboard

This prototype simulates social media risks arriving at different times and displays them on a dashboard with real-time notifications.

## How It Works

1. **Risk Analyzer** (`agent.py`): Analyzes synthetic social media posts using OpenAI's API to detect risks
2. **Risk Streamer** (`stream_risks.py`): Simulates real-time arrival of risks at configurable intervals
3. **Live Dashboard** (`app.py`): Shows incoming risks as notification popups and allows users to make decisions

## Usage

### Setup

Make sure you have the required packages:
```bash
pip install streamlit openai requests pandas python-dotenv
```

Set your OpenAI API key:
```bash
$env:OPENAI_API_KEY="your-api-key-here"
```

### Running the Demo

**Terminal 1 - Start the Dashboard:**
```bash
cd comp/src
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`

**Terminal 2 - Stream Risks in Real-Time:**

Start streaming risks with default 2-second intervals:
```bash
cd comp/src
python stream_risks.py
```

Or customize the interval (example: 5 seconds between risks):
```bash
python stream_risks.py 5
```

Or customize both interval and disable shuffling:
```bash
python stream_risks.py 5 false
```

## What to Expect

1. **Dashboard opens** - Initially shows "Waiting for risk signals..."
2. **Risks start arriving** - Each risk appears as a notification popup on the dashboard
3. **Color-coded by severity**:
   - 🔴 **Critical/High** (Red border)
   - 🟡 **Medium** (Yellow border)
   - 🟢 **Low** (Green border)

4. **Department Routing** - Each risk is automatically routed to its department:
   - 💻 Technology & Operations
   - 📞 Customer Support
   - 📢 Marketing & Communications
   - ⚖️ Risk & Compliance

5. **User Decision Making** - For each risk you can:
   - **View Details** - See full analysis and credibility scores
   - **Escalate** - Get AI-generated mitigation options
   - **Dismiss** - Mark as reviewed but not actionable
   - **Save Decision** - Record your action for audit trail

## Dashboard Features

### Real-Time Updates
- Auto-refreshes every 2 seconds
- Shows newly arrived risks with notification popups
- Tracks notification history

### Department Views
- **Admin Dashboard** - Overview of all signals by department
- **Department Tabs** - Filtered view for each department
- **Metrics**:
  - Total Signals
  - 🔴 Critical/High Risks
  - 🟡 Medium Risks
  - Average Confidence Score
  - ✅ Actioned Risks

### Risk Detail View
Shows:
- Full caption from social media
- Risk type and severity level
- Confidence level and credibility score
- Department assignment
- Why it matters (business impact)
- Verification notes
- Option to escalate with AI-generated mitigation strategies

## Architecture

```
Synthetic Data (22 posts)
    ↓
Agent.py (Analyzes each with GPT-4)
    ↓
Stream_risks.py (Sends to dashboard at intervals)
    ↓
risks.json (Real-time updates)
    ↓
App.py Dashboard (Shows notifications)
    ↓
User Makes Decisions (Escalate/Dismiss/Review)
    ↓
Decisions Saved to risks.json (Audit trail)
```

## Example Workflow

1. Dashboard is running and waiting
2. First risk arrives: "Mashreq is down" → Service signal
3. Notification popup shows: 🟡 Medium severity
4. User clicks "View" in notification
5. Detail page shows: "Possible service disruption"
6. User chooses to "Escalate"
7. App generates 3 mitigation options
8. User selects action: "Monitor virality and track sources"
9. Decision recorded with timestamp
10. Dashboard returns to signal list
11. Next risk arrives automatically...

## Customization

### Change Analysis Interval
```bash
python stream_risks.py 3  # 3 seconds between risks
python stream_risks.py 0.5  # 0.5 seconds (faster)
python stream_risks.py 10  # 10 seconds (slower)
```

### Process Risks in Order
```bash
python stream_risks.py 2 false  # 2 seconds, no shuffling
```

### Batch Process All Risks at Once
```bash
python risk_simulator.py  # Analyze all 22 at once
```

## Output Files

- `risks.json` - All detected risks with decisions
- `synthetic_data.json` - Input social media posts
- Dashboard console shows real-time processing logs

## Troubleshooting

**"No risks loaded. Run agent.py first."**
- Start the streamer: `python stream_risks.py`

**Dashboard not updating**
- Check that `stream_risks.py` is running in another terminal
- Ensure risks.json is being written to

**API errors**
- Verify `OPENAI_API_KEY` is set correctly
- Check API quota and rate limits

**Posts being skipped**
- Posts with very low confidence and no fraud/service signals are filtered
- This is expected for neutral/positive posts like "great service!"
