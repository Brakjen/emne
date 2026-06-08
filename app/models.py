import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Species(Base):
    __tablename__ = "species"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    name_normalized: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    finds: Mapped[list["Find"]] = relationship(back_populates="species")

    @staticmethod
    def normalize(name: str) -> str:
        return " ".join(name.strip().lower().split())


class Find(Base):
    __tablename__ = "finds"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        Enum(
            "tree", "sapling", "burl", "rock", "mushroom",
            "viewpoint", "deadwood", "other",
            name="find_category",
        ),
        default="other",
    )
    status: Mapped[str] = mapped_column(
        Enum("watching", "collected", "passed", name="find_status"),
        default="watching",
        server_default="watching",
    )
    species_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("species.id", ondelete="SET NULL"), nullable=True
    )
    cover_photo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("photos.id", ondelete="SET NULL"), nullable=True
    )
    location: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
    )
    location_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    species: Mapped["Species | None"] = relationship(back_populates="finds")
    visits: Mapped[list["Visit"]] = relationship(
        back_populates="find", cascade="all, delete-orphan", order_by="Visit.visited_at.desc()"
    )
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="find",
        cascade="all, delete-orphan",
        order_by="Photo.created_at.desc()",
        foreign_keys="Photo.find_id",
    )
    cover_photo: Mapped["Photo | None"] = relationship(
        foreign_keys="Find.cover_photo_id", post_update=True
    )


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    find_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("finds.id", ondelete="CASCADE"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    visited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    find: Mapped["Find"] = relationship(back_populates="visits")
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="visit", order_by="Photo.created_at.desc()"
    )


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    find_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("finds.id", ondelete="CASCADE"))
    visit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visits.id", ondelete="SET NULL"), nullable=True
    )
    storage_key: Mapped[str] = mapped_column(String(512))
    thumbnail_key: Mapped[str] = mapped_column(String(512))
    caption: Mapped[str | None] = mapped_column(String(500), nullable=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    find: Mapped["Find"] = relationship(back_populates="photos", foreign_keys="Photo.find_id")
    visit: Mapped["Visit | None"] = relationship(back_populates="photos")


class AppSettings(Base):
    """Single-row application settings for this single-user app."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    region: Mapped[str] = mapped_column(String(255), default="Rogaland, Norway")
    ai_species_id: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_review_checklist: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_collect_timing: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_suggest_metadata: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
