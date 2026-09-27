import hashlib
from dataclasses import dataclass, field


@dataclass
class ListingStub:
    listing_id: str
    detail_url: str
    title: str


@dataclass
class JobPosting:
    site_id: str
    listing_id: str
    source_url: str
    title: str
    client: str | None = None
    category: str | None = None
    level: str | None = None
    status: str | None = None
    location: str | None = None
    hours: str | None = None
    rate: str | None = None
    duration: str | None = None
    posted_date: str | None = None
    experience: str | None = None
    skills: list[str] = field(default_factory=list)
    description: str = ""
    scrape_note: str | None = None
    extra_fields: dict[str, str] = field(default_factory=dict)

    def content_hash(self) -> str:
        hash_input = (
            f"{self.title}|"
            f"{self.client}|"
            f"{self.category}|"
            f"{self.level}|"
            f"{self.status}|"
            f"{self.location}|"
            f"{self.hours}|"
            f"{self.rate}|"
            f"{self.duration}|"
            f"{self.posted_date}|"
            f"{self.experience}|"
            f"{self.skills}|"
            f"{self.description}|"
            f"{self.scrape_note}|"
            f"{self.extra_fields}"
        )
        return hashlib.sha256(hash_input.encode()).hexdigest()
