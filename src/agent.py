import json
import re
import requests
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"

ALLOWED_RISK_TYPES = {"rumor", "misinformation", "service_signal", "fraud_signal", "other"}
ALLOWED_RISK_LEVELS = {"low", "medium", "high", "critical"}
ALLOWED_DEPARTMENTS = {
    "Technology & Operations",
    "Customer Support",
    "Marketing & Communications",
    "Risk & Compliance",
}

def clean_json(raw_text):
    """Extract text between the first { and last } to handle extra text around JSON."""
    match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    if match:
        return match.group(0)
    # If no JSON found, return raw text (let json.loads handle the error)
    return raw_text 

def analyze_caption(caption: str):
    prompt = f"""
You are a bank risk signal detection assistant.
Analyze this social media caption and output ONLY valid JSON.

Calculate "confidence" as a decimal between 0.0 and 1.0 based on how strongly the caption supports the selected risk_type and risk_level.
Use this rubric:
- 0.0–0.3: weak/ambiguous signal
- 0.4–0.6: moderate signal
- 0.7–1.0: strong, clear signal
Return confidence as a numeric value (no text, no percent sign).

Caption:
\"{caption}\"

Return JSON in EXACTLY this format:
{{
  "risk_type": "rumor|misinformation|service_signal|fraud_signal|other",
  "risk_level": "low|medium|high|critical",
  "confidence": 0.0,
  "department": "Technology & Operations|Customer Support|Marketing & Communications|Risk & Compliance",
  "why_it_matters": "short explanation",
  "summary": "short summary of the risk",
  "time-detected": "{datetime.utcnow().isoformat()}"
}}
"""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload)
    response.raise_for_status()

    raw_text = clean_json(response.json()["response"].strip())

    try:
        result = json.loads(raw_text)
        return normalize_result(result)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        print(f"Raw text from LLM:\n{raw_text}\n")
        raise

def generate_escalation_options(summary: str, risk_type: str, risk_level: str):
    prompt = f"""
You are a bank risk response assistant.
Given the risk summary, generate EXACTLY 3 concise action options to address it.
Return ONLY valid JSON in this format:
{{
  "options": ["option 1", "option 2", "option 3"]
}}

Risk Type: {risk_type}
Risk Level: {risk_level}
Summary: {summary}
"""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        raw_text = response.json()["response"].strip()
        
        # Try to extract JSON
        cleaned = clean_json(raw_text)
        result = json.loads(cleaned)
        options = result.get("options", [])
        return [str(o).strip() for o in options][:3]
    except (json.JSONDecodeError, requests.RequestException, KeyError) as e:
        print(f"⚠️ Error generating options: {e}")
        print(f"Raw response: {raw_text if 'raw_text' in locals() else 'N/A'}")
        # Fallback options
        return [
            "Monitor virality and track sources",
            "Prepare a holding statement",
            "Coordinate with Communications team"
        ]

def normalize_result(result: dict) -> dict:
    risk_type = str(result.get("risk_type", "other")).strip()
    if "|" in risk_type:
        candidates = [v.strip() for v in risk_type.split("|")]
        risk_type = next((v for v in candidates if v in ALLOWED_RISK_TYPES), "other")
    if risk_type not in ALLOWED_RISK_TYPES:
        risk_type = "other"

    risk_level = str(result.get("risk_level", "low")).strip()
    if "|" in risk_level:
        candidates = [v.strip() for v in risk_level.split("|")]
        risk_level = next((v for v in candidates if v in ALLOWED_RISK_LEVELS), "low")
    if risk_level not in ALLOWED_RISK_LEVELS:
        risk_level = "low"

    try:
        confidence = float(result.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    department = str(result.get("department", "Technology & Operations")).strip()
    if department not in ALLOWED_DEPARTMENTS:
        department = "Technology & Operations"

    return {
        "risk_type": risk_type,
        "risk_level": risk_level,
        "confidence": confidence,
        "department": department,
        "why_it_matters": str(result.get("why_it_matters", "")).strip(),
        "summary": str(result.get("summary", "")).strip(),
        "time-detected": str(result.get("time-detected", "")).strip(),
    }

def risk_chat(caption: str, result: dict):
    print("\n=== Risk Q&A Chat (type 'exit' to quit) ===")
    while True:
        user_q = input("You: ").strip()
        if user_q.lower() in {"exit", "quit"}:
            break

        prompt = f"""
You are a bank risk analyst assistant. Answer user questions about the risk.
Keep answers concise and grounded in the provided context.

Caption: {caption}
Risk Type: {result['risk_type']}
Risk Level: {result['risk_level']}
Confidence: {result['confidence']}
Department: {result['department']}
Why It Matters: {result['why_it_matters']}
Summary: {result['summary']}

User Question: {user_q}
"""
        payload = {"model": MODEL, "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        print("Assistant:", response.json()["response"].strip())

def main():
    # 1) Load posts
    with open("../data/synthetic_data.json", "r", encoding="utf-8") as f:
        posts = json.load(f)

    risks = []

    # 2) Analyze each caption
    for post in posts:
        caption = post["caption"]
        result = analyze_caption(caption)

        print("\n=== Risk Signal ===")
        print(f"Department: {result['department']}")
        print(f"Risk Type: {result['risk_type']}")
        print(f"Risk Level: {result['risk_level']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Description: {result['summary']}")

        action = input("Choose action (dismiss/escalate/other): ").strip().lower()
        while action not in {"dismiss", "escalate", "other"}:
            action = input("Invalid. Choose (dismiss/escalate/other): ").strip().lower()

        risk_record = {
            "post_id": post["id"],
            "caption": caption,
            "time_detected": datetime.utcnow().isoformat(),
            "action": action,
            **result
        }

        if action == "other":
            risk_record["status"] = "in_review"
            risk_chat(caption, result)

        if action == "escalate":
            options = generate_escalation_options(
                summary=result["summary"],
                risk_type=result["risk_type"],
                risk_level=result["risk_level"]
            )
            risk_record["escalation_options"] = options
            print("\nEscalation Options:")
            for i, opt in enumerate(options, 1):
                # Handle both string and dict formats
                if isinstance(opt, dict):
                    display_text = opt.get("description", str(opt))
                else:
                    display_text = str(opt)
                print(f"{i}. {display_text}")

            choice = input("Select escalation option (1-3): ").strip()
            while choice not in {"1", "2", "3"}:
                choice = input("Invalid. Select escalation option (1-3): ").strip().lower()

            chosen_option = options[int(choice) - 1]
            if isinstance(chosen_option, dict):
                chosen_option = chosen_option.get("description", str(chosen_option))
            
            risk_record["action_taken"] = chosen_option
            risk_record["status"] = "actioned"

            print("\n=== Escalation Summary ===")
            print(f"Risk Name: {result['risk_type']}")
            print(f"Action Taken: {chosen_option}")
            print(f"Updated Status: {risk_record['status']}")

        risks.append(risk_record)

    # 3) Save output JSON
    with open("../output/risks.json", "w", encoding="utf-8") as f:
        json.dump(risks, f, indent=2)

    print("\n✅ Done! Saved results to ../output/risks.json")

if __name__ == "__main__":
    main()
