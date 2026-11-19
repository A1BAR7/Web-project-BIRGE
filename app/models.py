"""Persistent records for Birge's existing workflows."""

from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Identity,
    Index, Integer, String, Text, false, func, text, true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


IDENTIFIER = BigInteger().with_variant(Integer, 'sqlite')


class LostItem(Base):
    __tablename__ = 'lost_items'
    __table_args__ = (
        CheckConstraint("status IN ('lost', 'found')", name='ck_lost_status'),
        CheckConstraint('owner_id > 0', name='ck_lost_owner'),
    )

    id: Mapped[int] = mapped_column(IDENTIFIER, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(5))
    place: Mapped[str] = mapped_column(String(120))
    desc: Mapped[str] = mapped_column(String(500))
    owner_id: Mapped[int] = mapped_column(BigInteger)
    resolved: Mapped[bool] = mapped_column(Boolean, server_default=false())
    images: Mapped[list['LostItemImage']] = relationship(
        back_populates='item', cascade='all, delete-orphan', passive_deletes=True,
        lazy='selectin', order_by='LostItemImage.position',
    )


class LostItemImage(Base):
    __tablename__ = 'lost_item_images'

    position: Mapped[int] = mapped_column(IDENTIFIER, primary_key=True)
    id: Mapped[str] = mapped_column(String(32), unique=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('lost_items.id', ondelete='CASCADE'), index=True)
    url: Mapped[str] = mapped_column(String(100))
    item: Mapped[LostItem] = relationship(back_populates='images')


class Skill(Base):
    __tablename__ = 'skills'
    __table_args__ = (
        CheckConstraint("kind IN ('teach', 'learn')", name='ck_skill_kind'),
        CheckConstraint('owner_id > 0', name='ck_skill_owner'),
    )

    id: Mapped[int] = mapped_column(IDENTIFIER, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    person: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(5))
    detail: Mapped[str] = mapped_column(String(500))
    exchange: Mapped[str] = mapped_column(String(120))
    owner_id: Mapped[int] = mapped_column(BigInteger)
    active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    requests: Mapped[list['SkillRequest']] = relationship(
        back_populates='skill', cascade='all, delete-orphan', passive_deletes=True,
        lazy='raise', order_by='SkillRequest.id',
    )


class SkillRequest(Base):
    __tablename__ = 'skill_requests'
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'accepted', 'rejected')", name='ck_request_status'),
        CheckConstraint('applicant_id > 0', name='ck_request_applicant'),
        Index(
            'uq_skill_requests_pending', 'skill_id', 'applicant_id', unique=True,
            postgresql_where=text("status = 'pending'"), sqlite_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[int] = mapped_column(IDENTIFIER, primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey('skills.id', ondelete='CASCADE'), index=True)
    applicant_id: Mapped[int] = mapped_column(BigInteger)
    message: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(8), server_default='pending')
    skill: Mapped[Skill] = relationship(back_populates='requests')


class Confession(Base):
    __tablename__ = 'confessions'
    __table_args__ = (CheckConstraint('author_id > 0', name='ck_confession_author'),)

    id: Mapped[int] = mapped_column(IDENTIFIER, primary_key=True)
    text: Mapped[str] = mapped_column(String(280))
    author_id: Mapped[int] = mapped_column(BigInteger)
    reactions: Mapped[list['ConfessionLike']] = relationship(
        back_populates='confession', cascade='all, delete-orphan', passive_deletes=True,
        lazy='raise',
    )


class ConfessionLike(Base):
    __tablename__ = 'confession_likes'
    __table_args__ = (CheckConstraint('user_id > 0', name='ck_like_user'),)

    post_id: Mapped[int] = mapped_column(ForeignKey('confessions.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    confession: Mapped[Confession] = relationship(back_populates='reactions')


class FoodItem(Base):
    __tablename__ = 'food_items'
    __table_args__ = (
        CheckConstraint("currency = 'KZT'", name='ck_food_currency'),
        CheckConstraint('price > 0 AND price <= 1.7976931348623157e308', name='ck_food_price'),
        CheckConstraint(
            "length(trim(name)) > 0 AND length(trim(category)) > 0 AND length(trim(canteen)) > 0",
            name='ck_food_labels',
        ),
        CheckConstraint(
            "image_kind IN ('placeholder', 'representative', 'authentic')", name='ck_food_image_kind',
        ),
    )

    id: Mapped[int] = mapped_column(IDENTIFIER, Identity(start=10011), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(1000))
    price: Mapped[float] = mapped_column(Float(53))
    currency: Mapped[str] = mapped_column(String(3))
    category: Mapped[str] = mapped_column(String(80))
    canteen: Mapped[str] = mapped_column(String(100))
    image_url: Mapped[str] = mapped_column(Text)
    available: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    image_kind: Mapped[str] = mapped_column(String(14))
    image_alt: Mapped[str] = mapped_column(Text)
    image_credit: Mapped[str] = mapped_column(Text)
    image_source: Mapped[str] = mapped_column(Text)
