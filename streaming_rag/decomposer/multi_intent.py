"""
Multi-Intent Decomposer for compound streaming utterances.
Parses unsegmented utterances into discrete, search-ready sub-queries while preserving
contextual anchors (e.g., location, subject matter) and avoiding over-fragmentation.
"""

import re
from typing import List, Dict, Any, Tuple


class MultiIntentDecomposer:
    """Deconstructs compound requests into orthogonal search queries with contextual anchors."""

    INTENT_TOPICS = [
        {
            "id": "venue_capacity",
            "regex": r"\b(venue|room|hall|capacity|attendees?|delegates?|people|pax|seats?)\b",
            "query_template": "venue capacity for {capacity} attendees in {location}"
        },
        {
            "id": "cancellation_policy",
            "regex": r"\b(cancellation|cancel|refund|penalty|fee|terms)\b",
            "query_template": "cancellation policy and refund terms workshop {location}"
        },
        {
            "id": "catering_options",
            "regex": r"\b(catering|cater|food|meal|lunch|breakfast|refreshments|dietary)\b",
            "query_template": "catering service options workshop {location}"
        },
        {
            "id": "av_equipment",
            "regex": r"\b(av|audio|visual|projector|screen|mic|wifi|internet)\b",
            "query_template": "IT equipment AV rental guidelines {location}"
        },
        {
            "id": "travel_reimbursement",
            "regex": r"\b(travel|reimbursement|per[- ]diem|airfare|lodging|expense)\b",
            "query_template": "employee travel reimbursement rules"
        },
        {
            "id": "international_travel",
            "regex": r"\b(international|foreign|currency|exchange|overseas)\b",
            "query_template": "international travel foreign currency receipt verification"
        },
        {
            "id": "late_booking",
            "regex": r"\b(late[- ]booking|after\s+travel|retroactive|exception)\b",
            "query_template": "late booking exception policy senior director approval"
        }
    ]

    def extract_context_anchors(self, text: str) -> Dict[str, str]:
        """Extracts key contextual anchors such as location, capacity, event type."""
        anchors = {"location": "", "capacity": "", "event": ""}

        loc_match = re.search(r"\b(pune|mumbai|bangalore|delhi|hyderabad|chennai)\b", text, re.IGNORECASE)
        if loc_match:
            anchors["location"] = loc_match.group(1).title()

        cap_match = re.search(r"\b(\d{1,4})\s*(people|attendees|delegates|persons|pax|seats)?\b", text, re.IGNORECASE)
        if cap_match:
            anchors["capacity"] = cap_match.group(1)

        event_match = re.search(r"\b(workshop|conference|seminar|meeting|training)\b", text, re.IGNORECASE)
        if event_match:
            anchors["event"] = event_match.group(1)

        return anchors

    def decompose(self, accumulated_text: str) -> List[str]:
        """
        Decomposes compound text into discrete search-ready sub-queries.
        Guarantees that distinct orthogonal intents are extracted.
        """
        anchors = self.extract_context_anchors(accumulated_text)
        detected_intents: List[str] = []

        lower = accumulated_text.lower()
        for topic in self.INTENT_TOPICS:
            if re.search(topic["regex"], lower):
                # Build search-ready query with contextual anchors
                loc = anchors.get("location") or "venues"
                cap = anchors.get("capacity") or "30"
                event = anchors.get("event") or "workshop"

                q = topic["query_template"].format(
                    location=loc,
                    capacity=cap,
                    event=event
                ).strip()
                # Clean up any extra spaces
                q = re.sub(r"\s+", " ", q)
                if q not in detected_intents:
                    detected_intents.append(q)

        # Fallback: if no predefined template hits but utterance is compound
        if not detected_intents:
            # Split on coordinating conjunctions
            parts = re.split(r"\band\s+the\b|\band\b|\balso\b|\bas\s+well\s+as\b", accumulated_text, flags=re.IGNORECASE)
            for part in parts:
                clean_part = part.strip().strip(". ,")
                if len(clean_part.split()) >= 2:
                    detected_intents.append(clean_part)

        # Prevent over-fragmentation: deduplicate near-identical queries
        final_queries: List[str] = []
        for q in detected_intents:
            if not any(q.lower() == existing.lower() for existing in final_queries):
                final_queries.append(q)

        return final_queries
