"""
Pydantic data models for the AI-Powered Lost & Found System.

Three core models:
- LostItemReport: submitted by passengers
- FoundItemRecord: registered by airport staff
- MatchResult: AI-generated match between lost and found items
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field


# ─── Enums ───────────────────────────────────────────────────────────

class LostItemStatus(str, Enum):
    ACTIVE = "active"
    MATCHED = "matched"
    CLOSED = "closed"


class FoundItemStatus(str, Enum):
    UNCLAIMED = "unclaimed"
    MATCHED = "matched"
    CLAIMED = "claimed"


class MatchStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ItemCategory(str, Enum):
    PHONE = "phone"
    LAPTOP = "laptop"
    TABLET = "tablet"
    WALLET = "wallet"
    BAG = "bag"
    LUGGAGE = "luggage"
    WATCH = "watch"
    JEWELRY = "jewelry"
    PASSPORT = "passport"
    KEYS = "keys"
    HEADPHONES = "headphones"
    CAMERA = "camera"
    CLOTHING = "clothing"
    BOOK = "book"
    GLASSES = "glasses"
    UMBRELLA = "umbrella"
    CHARGER = "charger"
    OTHER = "other"


class AirportLocation(str, Enum):
    TERMINAL_1 = "Terminal 1"
    TERMINAL_2 = "Terminal 2"
    TERMINAL_3 = "Terminal 3"
    GATE_A = "Gates A"
    GATE_B = "Gates B"
    GATE_C = "Gates C"
    AIRCRAFT = "Aircraft"
    SECURITY = "Security"
    BAGGAGE_CLAIM = "Baggage Claim"
    LOUNGE = "Lounge"
    RESTROOM = "Restroom"
    FOOD_COURT = "Food Court"
    PARKING = "Parking"


# ─── Core Models ─────────────────────────────────────────────────────

class LostItemReport(BaseModel):
    """A lost item report submitted by a passenger."""

    case_id: UUID = Field(default_factory=uuid4)
    passenger_name: str
    contact_email: str
    contact_phone: str = ""
    item_description: str
    item_category: str = "other"
    item_color: str = ""
    item_brand: str = ""
    location_last_seen: str = ""
    time_last_seen: Optional[datetime] = None
    optional_photo_path: Optional[str] = None
    status: LostItemStatus = LostItemStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FoundItemRecord(BaseModel):
    """A found item record registered by airport staff."""

    found_id: UUID = Field(default_factory=uuid4)
    staff_id: str
    item_description: str = ""
    item_category: str = "other"
    item_color: str = ""
    item_brand: str = ""
    location_found: str = ""
    time_found: Optional[datetime] = None
    photo_path: Optional[str] = None
    optional_notes: str = ""
    status: FoundItemStatus = FoundItemStatus.UNCLAIMED
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MatchResult(BaseModel):
    """An AI-generated match between a lost report and a found item."""

    match_id: UUID = Field(default_factory=uuid4)
    lost_case_id: UUID
    found_item_id: UUID
    confidence_score: float = Field(ge=0.0, le=1.0)
    match_reasons: list[str] = Field(default_factory=list)
    status: MatchStatus = MatchStatus.PENDING
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class NotificationLog(BaseModel):
    """Log entry for a notification sent (or simulated) to a passenger."""

    notification_id: UUID = Field(default_factory=uuid4)
    case_id: UUID
    match_id: UUID
    passenger_email: str
    confidence_score: float
    found_item_description: str
    message: str = ""
    sent_at: datetime = Field(default_factory=datetime.utcnow)
