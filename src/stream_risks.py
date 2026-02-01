"""
Risk Stream Generator - Simulates risks arriving at different times.
This adds risks to the risks.json file at intervals, with random delays.
"""

import json
import time
import random
import sys
from datetime import datetime, timezone
from agent import analyze_caption

def stream_risks_gradually(delay_between_risks=2, shuffle=True):
    """
    Load all synthetic posts, analyze them, and stream results to risks.json at intervals.
    
    Args:
        delay_between_risks: Seconds to wait between adding each risk (default: 2 seconds)
        shuffle: Randomize the order of risks (default: True)
    """
    
    # Load synthetic data
    with open("../data/synthetic_data.json", "r", encoding="utf-8") as f:
        posts = json.load(f)
    
    # Randomize order if specified
    if shuffle:
        random.shuffle(posts)
    
    print(f"🚀 Starting real-time risk stream with {len(posts)} posts")
    print(f"⏱️  Delay between risks: {delay_between_risks} seconds\n")
    
    all_risks = []
    signal_count = 0
    
    for idx, post in enumerate(posts, 1):
        caption = post["caption"]
        print(f"[{idx}/{len(posts)}] {caption[:60]}...", end=" ", flush=True)
        
        try:
            # Analyze the caption
            result = analyze_caption(caption)
            
            # Auto-filter low confidence neutral posts
            if result['confidence'] < 0.4 and result['risk_type'] not in {"service_signal", "fraud_signal"}:
                print("(skipped - low confidence)")
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
            signal_count += 1
            
            print(f"✓ {result['risk_type']} ({result['risk_level']})")
            
            # Save to file after each risk
            with open("../output/risks.json", "w", encoding="utf-8") as f:
                json.dump(all_risks, f, indent=2)
            
            print(f"   → Risk #{signal_count} added to dashboard. Total: {len(all_risks)}")
            
            # Wait before processing next risk
            if idx < len(posts):
                time.sleep(delay_between_risks)
            
        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}")
            continue
    
    print(f"\n✅ Stream complete!")
    print(f"📊 Found {signal_count} risk signals from {len(posts)} posts")
    print(f"📁 All risks saved to ../output/risks.json")
    print(f"\n🎬 Keep the dashboard open to see risks arrive in real-time!")
    
    return all_risks

if __name__ == "__main__":
    # Parse command line arguments
    delay = 2
    shuffle = True
    
    if len(sys.argv) > 1:
        try:
            delay = float(sys.argv[1])
        except ValueError:
            print(f"Invalid delay: {sys.argv[1]}, using default 2 seconds")
    
    if len(sys.argv) > 2:
        shuffle = sys.argv[2].lower() in {"true", "1", "yes"}
    
    stream_risks_gradually(delay_between_risks=delay, shuffle=shuffle)
