"""
agent.py — Gemini AI Reasoning Engine
=======================================
Implements the Reasoning → Planning → Action stages of the pipeline.
Now includes memory reflection — Gemini reads past decisions before reasoning.
"""

import os
import json
import re
import concurrent.futures
from google import genai
from google.genai import types
from memory import get_reflection_context, get_override_patterns

_GEMINI_TIMEOUT_SECONDS = 90


# ---------------------------------------------------------------------------
# MOCK FALLBACK RESPONSES (one per company profile)
# The two mocks intentionally choose different strategies to demonstrate
# hyper-personalisation even without a live API key.
# ---------------------------------------------------------------------------

# --- AcmeMfg GmbH: single-source, conservative → SPLIT_ORDER ---
_MOCK_ACME = {
    "reasoning_trace": [
        {
            "step": 1,
            "stage": "Perception Analysis",
            "thought": (
                "A HIGH-severity Port Strike is active at Rotterdam — Europe's largest port, "
                "handling ~11% of all EU imports. Our active PO of 1,000 units from Precision "
                "Parts GmbH (Stuttgart) transits exclusively through this hub. Memory check: "
                "no prior Rotterdam disruption recorded for AcmeMfg — applying conservative "
                "defaults per company risk policy (risk_appetite: low)."
            ),
        },
        {
            "step": 2,
            "stage": "Inventory Risk Assessment",
            "thought": (
                "ERP: 500 units on-hand ÷ 50 units/day = 10.0 days buffer. "
                "Haversine transit model adds 2.77 days of delay. "
                "Net buffer after delay: 10.0 − 2.77 = 7.23 days. "
                "Safety stock threshold: 3 days → net buffer (7.23d) exceeds threshold, "
                "but if strike extends beyond 7 days the 1,000-unit PO is fully stuck. "
                "Revenue at risk: $85,000/day × potential 7-day exposure = $595,000. "
                "Urgency classification: MEDIUM, trending HIGH."
            ),
        },
        {
            "step": 3,
            "stage": "Supplier Trade-off Simulation",
            "thought": (
                "Option A — Wait (Primary only): $0 premium. Risk: catastrophic if strike "
                "extends >7 days. Unacceptable for low risk-appetite profile. "
                "— "
                "Option B — Activate Secondary (Monterrey): 14-day sea freight or 7-day air. "
                "Air: $38 + $8 surcharge = $46 × 500 units = $23,000. Exceeds $20,000 HITL "
                "threshold. Covers gap with 3-day margin. "
                "— "
                "Option C — Split Order: Emergency 500-unit air order to Supplier B (keeps "
                "primary PO active). Net cost premium = $4,000 (500 × $8 air surcharge only). "
                "Below HITL threshold? No — total order is $23,000, still requires approval. "
                "However, this preserves the supplier relationship and limits cancellation "
                "penalties. Optimal for AcmeMfg's low risk appetite."
            ),
        },
        {
            "step": 4,
            "stage": "Decision & Strategy",
            "thought": (
                "Selecting SPLIT_ORDER. Rationale: (1) $4,000 premium = 4.7% of one day's "
                "production value — minimal insurance cost. (2) Cancelling Precision Parts GmbH "
                "PO would trigger €8,500 cancellation clause and damage 6-year relationship. "
                "(3) Split maintains dual-source redundancy. (4) If strike resolves in <5 days, "
                "Supplier B order redirected to replenish safety stock — no waste."
            ),
        },
        {
            "step": 5,
            "stage": "Action Execution",
            "thought": (
                "Drafting emergency PO to Motores Avanzados S.A. Total order value $23,000 "
                "EXCEEDS $20,000 autonomous threshold → HITL flag set. Escalating to Supply "
                "Chain Manager, 4-hour decision deadline. Secondary: flagging EuroAuto "
                "Industries account manager re: potential 2-day SLA buffer consumption."
            ),
        },
    ],
    "risk_assessment": {
        "stockout_probability": "MEDIUM",
        "days_until_critical": 7.2,
        "financial_exposure_usd": 85_000,
        "confidence_score": 0.88,
    },
    "chosen_strategy": {
        "id": "SPLIT_ORDER",
        "name": "Split Order Strategy",
        "description": (
            "Place an emergency 500-unit air-freight order with Supplier B (Monterrey) to "
            "bridge the gap, while keeping the Supplier A PO active for when Rotterdam clears."
        ),
        "primary_action": "Activate Supplier B — Motores Avanzados S.A. (Monterrey) for 500 units via air freight",
        "cost_premium_usd": 4_000,
        "risk_reduction": "Reduces stockout probability from MEDIUM to LOW; eliminates Rotterdam single-point-of-failure",
    },
    "draft_email": {
        "to": "procurement@motoresavanzados.mx",
        "subject": "URGENT: Emergency Purchase Order — ISM-4400 Servo Motors (500 units)",
        "body": (
            "Dear Procurement Team at Motores Avanzados S.A.,\n\n"
            "I am writing on behalf of AcmeMfg GmbH regarding an urgent supply chain situation.\n\n"
            "Due to an active Port Strike at Rotterdam (High severity), our primary inbound "
            "shipment is significantly delayed. To protect our SLA with EuroAuto Industries, "
            "we require an emergency activation:\n\n"
            "  • SKU:       ISM-4400 Industrial Servo Motor\n"
            "  • Quantity:  500 units\n"
            "  • Delivery:  Air freight (expedited)\n"
            "  • Required:  Within 10 business days\n"
            "  • Ship to:   Paris Distribution Hub, Paris, France\n"
            "  • Price:     $38.00/unit + air-freight surcharge\n\n"
            "Please confirm availability and earliest ship date immediately. "
            "Formal PO will follow within the hour upon your confirmation.\n\n"
            "Best regards,\nSupply Chain Operations — AcmeMfg GmbH\n\n"
            "---\n[AGENT NOTE: Requires Supply Chain Manager approval — order value ($23,000) "
            "exceeds $20,000 autonomous action threshold.]"
        ),
    },
    "hitl_flag": {
        "requires_human_approval": True,
        "reason": "Emergency order value (~$23,000) exceeds the $20,000 autonomous action threshold.",
        "escalate_to": "Supply Chain Manager",
        "deadline_hours": 4,
    },
    "_is_mock": True,
}

# --- TexMex Components: multi-sourced, medium risk → ACTIVATE_SECONDARY directly ---
_MOCK_TEXMEX = {
    "reasoning_trace": [
        {
            "step": 1,
            "stage": "Perception Analysis",
            "thought": (
                "A CRITICAL Factory Fire has been detected at Monterrey — location of our "
                "Primary supplier, Grupo Electrico Monterrey. Unlike AcmeMfg GmbH which "
                "routes through a port hub, this disruption hits the manufacturing source "
                "directly. Active PO: 5,000 units now undeliverable. Memory check: no prior "
                "Monterrey disruption — applying medium risk-appetite defaults. "
                "Note: TexMex's multi-source structure (3 active suppliers) is designed "
                "precisely for this scenario."
            ),
        },
        {
            "step": 2,
            "stage": "Inventory Risk Assessment",
            "thought": (
                "ERP: 3,000 units on-hand ÷ 300 units/day = 10.0 days buffer. "
                "Factory fire = complete shutdown of primary — modelled as 100% transit "
                "disruption (multiplier 5×). Net buffer: 10.0 days. "
                "SLA with Ford Motor Company — Hermosillo Plant: max 2-day delay. "
                "At 300 units/day burn rate and Ford's JIT schedule, we have 10 days "
                "before stockout but only 2 days before SLA breach. "
                "Revenue at risk: $120,000/day. URGENCY: HIGH — SLA at immediate risk."
            ),
        },
        {
            "step": 3,
            "stage": "Supplier Trade-off Simulation",
            "thought": (
                "Option A — Wait: Factory fires average 14–21 day recovery. Unacceptable — "
                "SLA breach in 2 days, Ford production line at risk. Rejected. "
                "— "
                "Option B — Activate Secondary (AutoWire USA, Houston): 5-day lead time "
                "via road freight, $14.50/unit. Emergency 3,000-unit order = $43,500. "
                "Below $50,000 autonomous threshold → no HITL required. Covers 10-day "
                "buffer with minimal SLA impact (2 days late but manageable). "
                "— "
                "Option C — Activate Tertiary (Guangzhou): 18-day sea freight — far exceeds "
                "SLA window. Only viable as supplemental re-stock, not emergency. "
                "Decision: ACTIVATE_SECONDARY immediately, supplement with partial Tertiary "
                "order to rebuild safety stock."
            ),
        },
        {
            "step": 4,
            "stage": "Decision & Strategy",
            "thought": (
                "Selecting ACTIVATE_SECONDARY (AutoWire USA). Rationale: (1) $14.50/unit "
                "vs $12.00/unit primary = $2.50 premium × 3,000 units = $7,500 cost increase "
                "— acceptable given $120,000/day exposure. (2) 5-day lead time just meets "
                "the Ford SLA window with proactive communication. (3) $43,500 order is "
                "below the $50,000 autonomous action limit — no human approval needed. "
                "(4) Simultaneously place 2,000-unit sea-freight order with Guangzhou to "
                "rebuild safety stock (18-day lead, $18,000 — also autonomous)."
            ),
        },
        {
            "step": 5,
            "stage": "Action Execution",
            "thought": (
                "Drafting emergency PO to AutoWire USA Corp. (Houston). Total value $43,500 "
                "is BELOW $50,000 autonomous threshold → email authorised for immediate send. "
                "Parallel action: notifying Ford Motor Company Hermosillo procurement team "
                "of the situation and confirmed 5-day recovery timeline. This proactive "
                "communication is essential for JIT customers — surprises cost relationships."
            ),
        },
    ],
    "risk_assessment": {
        "stockout_probability": "HIGH",
        "days_until_critical": 2.0,
        "financial_exposure_usd": 120_000,
        "confidence_score": 0.92,
    },
    "chosen_strategy": {
        "id": "ACTIVATE_SECONDARY",
        "name": "Activate Secondary Supplier",
        "description": (
            "Immediately activate AutoWire USA Corp. (Houston) for a 3,000-unit emergency "
            "road-freight order. Action is autonomous — below $50,000 threshold. "
            "Supplemental 2,000-unit sea order to Guangzhou placed to rebuild safety stock."
        ),
        "primary_action": "Activate Supplier X2 — AutoWire USA Corp. (Houston) for 3,000 units via road freight",
        "cost_premium_usd": 7_500,
        "risk_reduction": "Prevents Ford SLA breach; reduces stockout probability from HIGH to LOW within 5 days",
    },
    "draft_email": {
        "to": "orders@autowireusa.com",
        "subject": "URGENT: Emergency Purchase Order — AWH-2200 Wire Harness (3,000 units)",
        "body": (
            "Dear AutoWire USA Procurement Team,\n\n"
            "I am writing on behalf of TexMex Components S.A. regarding a critical supply "
            "chain emergency requiring your immediate response.\n\n"
            "Our primary supplier in Monterrey has suffered a factory fire and is unable to "
            "fulfil our active purchase order. To maintain our JIT commitments to Ford Motor "
            "Company — Hermosillo Plant, we require the following emergency order:\n\n"
            "  • SKU:       AWH-2200 Automotive Wire Harness\n"
            "  • Quantity:  3,000 units\n"
            "  • Delivery:  Road freight (expedited)\n"
            "  • Required:  Within 5 business days (Ford SLA window)\n"
            "  • Ship to:   San Antonio Assembly Hub, San Antonio, TX\n"
            "  • Price:     $14.50/unit (agreed framework price)\n\n"
            "This order falls within our autonomous procurement authority ($43,500 < $50,000 "
            "threshold). Please confirm availability within 2 hours.\n\n"
            "Best regards,\nSupply Chain Operations — TexMex Components S.A.\n\n"
            "---\n[AGENT NOTE: Autonomous send authorised — order value within threshold. "
            "No human approval required.]"
        ),
    },
    "hitl_flag": {
        "requires_human_approval": False,
        "reason": "Order value ($43,500) is below the $50,000 autonomous action threshold for TexMex Components.",
        "escalate_to": None,
        "deadline_hours": None,
    },
    "_is_mock": True,
}

MOCK_RESPONSES = {
    "AcmeMfg GmbH": _MOCK_ACME,
    "TexMex Components S.A.": _MOCK_TEXMEX,
}


# ---------------------------------------------------------------------------
# PROMPT BUILDER
# ---------------------------------------------------------------------------

def _build_prompt(
    disruption_event: dict,
    transit_data: dict,
    risk_assessment: dict,
    erp_data: dict,
    memory_context: str = "",
) -> str:
    inv = erp_data["inventory"]
    sla = erp_data["sla"]

    supplier_lines = []
    health_lines = []
    for sup in erp_data["suppliers"].values():
        supplier_lines.append(
            f"  - [{sup['role']}] {sup['name']}, {sup['city']} {sup['country']} | "
            f"Lead time: {sup['normal_lead_time_days']}d | Cost: ${sup['unit_cost_usd']}/unit | "
            f"Active PO: {sup['active_po_units']} units | Transit hub: {sup['transit_hub']}"
        )
        # Derive a simple supplier health score from available ERP signals
        has_active_po = sup["active_po_units"] > 0
        lead_time = sup["normal_lead_time_days"]
        if lead_time <= 7:
            speed_score = "Fast"
        elif lead_time <= 14:
            speed_score = "Moderate"
        else:
            speed_score = "Slow"
        activity = "Active (PO in flight)" if has_active_po else "Dormant (no active PO)"
        cost_rank = sorted(
            erp_data["suppliers"].values(), key=lambda s: s["unit_cost_usd"]
        )
        cost_position = ["Lowest-cost", "Mid-cost", "Highest-cost"][
            [s["name"] for s in cost_rank].index(sup["name"])
            if sup["name"] in [s["name"] for s in cost_rank]
            else 1
        ]
        health_score = 85 if has_active_po else 60
        health_score -= (lead_time // 7) * 5  # penalise long lead times
        health_lines.append(
            f"  - {sup['name']} [{sup['role']}]: Health={health_score}/100 | "
            f"Engagement={activity} | Speed={speed_score} | Cost position={cost_position}"
        )
    suppliers_block = "\n".join(supplier_lines)
    supplier_health_block = "\n".join(health_lines)

    return f"""You are TranSignal, an Autonomous Supply Chain Resilience Agent for a mid-market manufacturer.
Analyse the disruption, assess risk, simulate trade-offs, choose the optimal strategy, and draft an email.
Respond with a single valid JSON object only — no prose, no markdown fences.

=== COMPANY PROFILE ===
Company:          {erp_data['company']}
Product:          {erp_data['product']}
Risk appetite:    {erp_data.get('risk_appetite', 'medium')}
Concentration:    {erp_data.get('concentration_risk', 'medium')} risk

=== DISRUPTION EVENT ===
Type:      {disruption_event.get('event')}
Location:  {disruption_event.get('location')}
Severity:  {disruption_event.get('severity')}
Source:    {disruption_event.get('source', 'Manual trigger')}
Time:      {disruption_event.get('timestamp', 'Now')}

=== LOGISTICS IMPACT (Haversine model) ===
Route:                  {transit_data.get('origin', disruption_event.get('location'))} → {transit_data.get('destination', 'Warehouse')}
Normal transit time:    {transit_data.get('normal_duration_hours')} hours
Disrupted transit time: {transit_data.get('disrupted_duration_hours')} hours
Added delay:            {transit_data.get('delay_added_days')} days
Method:                 {transit_data.get('method', 'Haversine + severity model')}

=== ERP INVENTORY STATUS ===
On-hand:          {inv['on_hand_units']} units
Daily burn rate:  {inv['burn_rate_per_day']} units/day
Buffer days:      {risk_assessment.get('inventory_buffer_days')} days
Safety stock:     {inv['safety_stock_days']} days
Net days after delay: {risk_assessment.get('net_days_remaining')} days
Urgency:          {risk_assessment.get('urgency')}

=== SUPPLIER NETWORK ===
{suppliers_block}

=== SUPPLIER HEALTH SCORES (derived from ERP signals) ===
{supplier_health_block}

=== SLA & FINANCIAL CONTEXT ===
Key customer:            {sla['key_customer']}
Max acceptable delay:    {sla['max_acceptable_delay_days']} days
Revenue at risk/day:     ${sla['daily_production_value_usd']:,}
Autonomous action limit: ${sla['autonomous_action_limit_usd']:,}

=== MEMORY & REFLECTION (historical decisions) ===
{memory_context}

=== EVENT TYPE CONTEXT ===
Supported disruption types and their primary mitigation implications:
- Port Strike / Port Congestion: transit delay — reroute via alternate port or switch to air freight
- Factory Fire: supplier production halt — activate alternate supplier immediately
- Customs Delay / Regulatory Change: administrative delay — expedite documentation or pre-clear customs
- Extreme Weather: route/production disruption — buffer build or freight mode switch
- Semiconductor Shortage / Raw Material Price Spike: allocation scarcity — split-source or pre-buy forward
- Supplier Insolvency: permanent supply loss — urgent alternate qualification + legal review of PO
- Geopolitical Sanctions: trade compliance risk — substitute route and supplier, mandatory legal review

=== INSTRUCTIONS ===
1. In your reasoning, REFERENCE the memory/history above where relevant.
2. Write 5 reasoning steps covering all 5 stages below.
3. Each step must include specific numbers — no vague statements.
4. Choose exactly one strategy ID: WAIT | ACTIVATE_SECONDARY | SPLIT_ORDER | ACTIVATE_TERTIARY | BUFFER_STOCK_BUILD.
   - For Supplier Insolvency: default to ACTIVATE_SECONDARY or ACTIVATE_TERTIARY — WAIT is not viable.
   - For Semiconductor Shortage: prefer SPLIT_ORDER to diversify allocation risk.
   - For Geopolitical Sanctions: always set hitl_flag.requires_human_approval=true for legal review.
5. The company's risk_appetite must influence the strategy (low=cautious, high=aggressive).
6. Set hitl_flag.requires_human_approval=true if order value > autonomous_action_limit OR the event is Geopolitical Sanctions or Supplier Insolvency (mandatory legal/compliance review).
7. BIAS GUARD: Base all supplier recommendations solely on lead time, cost, health score, and disruption proximity. Do not systematically favour or penalise any supplier based on country of origin or geographic region unless the active disruption directly implicates that location.

=== JSON SCHEMA ===
{{
  "reasoning_trace": [
    {{"step": 1, "stage": "Perception Analysis",           "thought": "<specific reasoning>"}},
    {{"step": 2, "stage": "Inventory Risk Assessment",     "thought": "<specific numbers>"}},
    {{"step": 3, "stage": "Supplier Trade-off Simulation", "thought": "<option A vs B vs C with costs>"}},
    {{"step": 4, "stage": "Decision & Strategy",           "thought": "<justification with numbers>"}},
    {{"step": 5, "stage": "Action Execution",              "thought": "<what is executed and why>"}}
  ],
  "risk_assessment": {{
    "stockout_probability": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "days_until_critical": <float>,
    "financial_exposure_usd": <integer>,
    "confidence_score": <float 0.0-1.0>
  }},
  "chosen_strategy": {{
    "id": "<WAIT|ACTIVATE_SECONDARY|SPLIT_ORDER|ACTIVATE_TERTIARY>",
    "name": "<human-readable name>",
    "description": "<1-2 sentences>",
    "primary_action": "<single most important action right now>",
    "cost_premium_usd": <integer>,
    "risk_reduction": "<how risk is reduced>"
  }},
  "draft_email": {{
    "to": "<supplier email>",
    "subject": "<subject line>",
    "body": "<full email body, newlines as \\n>"
  }},
  "hitl_flag": {{
    "requires_human_approval": <true|false>,
    "reason": "<explanation>",
    "escalate_to": "<role or null>",
    "deadline_hours": <integer or null>
  }}
}}"""


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------

def run_agent(
    disruption_event: dict,
    transit_data: dict,
    risk_assessment: dict,
    erp_data: dict,
) -> dict:
    """
    Call Gemini and return a structured JSON decision.
    Falls back to the company-appropriate mock if the API is unavailable.
    Memory reflection is automatically injected into the prompt.
    """
    company = erp_data.get("company", "")

    api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        return MOCK_RESPONSES.get(company, _MOCK_ACME)

    try:
        # Fetch memory before reasoning
        memory_ctx = get_reflection_context(company=company)
        overrides = get_override_patterns()
        if overrides:
            override_lines = "\n".join(
                f"  - Strategy {o['strategy_id']} overridden {o['override_count']}x by humans. Sample reason: \"{o['sample_reason']}\""
                for o in overrides
            )
            memory_ctx += f"\n\n⚠ HUMAN OVERRIDE PATTERNS (avoid recommending these without strong justification):\n{override_lines}"

        client = genai.Client(api_key=api_key)
        prompt = _build_prompt(
            disruption_event, transit_data, risk_assessment, erp_data, memory_ctx
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.15,
                    response_mime_type="application/json",
                ),
            )
            try:
                response = future.result(timeout=_GEMINI_TIMEOUT_SECONDS)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(
                    f"Gemini API call timed out after {_GEMINI_TIMEOUT_SECONDS}s."
                )

        raw_text = response.text or ""

        # Robust JSON extraction: try direct parse first, then strip markdown fences
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            # Strip leading/trailing code fences if present
            clean = re.sub(r"^```(?:json)?\s*\n?", "", raw_text.strip(), flags=re.MULTILINE)
            clean = re.sub(r"\n?```\s*$", "", clean.strip(), flags=re.MULTILINE)
            # Last resort: extract the outermost JSON object
            obj_match = re.search(r"\{[\s\S]*\}", clean)
            if not obj_match:
                raise ValueError(f"No JSON object found in Gemini response: {raw_text[:200]}")
            parsed = json.loads(obj_match.group(0))

        parsed["_is_mock"] = False
        return parsed

    except Exception as exc:
        fallback = dict(MOCK_RESPONSES.get(company, _MOCK_ACME))
        fallback["_api_error"] = str(exc)
        fallback["_is_mock"] = True
        return fallback
