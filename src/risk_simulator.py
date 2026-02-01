"""
Real-time risk simulator - reads synthetic data and sends risks at different intervals.
This processes all risks from synthetic_data.json through the agent and saves them to a live stream.
"""

import json
import os
import time
import random
from datetime import datetime, timezone, timedelta
from agent import analyze_caption

def simulate_risk_arrival():
    """Load synthetic data and process all risks with simulated arrival times."""
    
    # Load synthetic data
    with open("../data/synthetic_data.json", "r", encoding="utf-8") as f:
        posts = json.load(f)
    
    print(f"🚀 Starting risk simulation with {len(posts)} posts\n")
    
    all_risks = []
    
    # Process all posts
    for idx, post in enumerate(posts, 1):
        caption = post["caption"]
        print(f"[{idx}/{len(posts)}] Processing: {caption[:60]}...", flush=True)
        
        try:
            result = analyze_caption(caption)
            
            # Auto-filter low confidence neutral posts
            if result['confidence'] < 0.4 and result['risk_type'] not in {"service_signal", "fraud_signal"}:
                print(f"   ℹ️ Skipped (low confidence)")
                continue
            
            # Create risk record
            risk_record = {
                "post_id": post["id"],
                "caption": caption,
                "time_detected": datetime.now(timezone.utc).isoformat(),
                "action": "pending",
                "status": "new",
                "department": result['department'],
                **result
            }
            
            all_risks.append(risk_record)
            print(f"   ✓ Signal detected: {result['risk_type']} ({result['risk_level']})")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    # Save all risks at once
    with open("../output/risks.json", "w", encoding="utf-8") as f:
        json.dump(all_risks, f, indent=2)
    
    print(f"\n✅ Analysis complete! Found {len(all_risks)} risk signals.")
    print(f"📁 Saved to ../output/risks.json")
    
    return all_risks

if __name__ == "__main__":
    simulate_risk_arrival()
