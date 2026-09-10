"""Modelos SQLAlchemy — tabelas site_* do site institucional eMe Móveis."""
from __future__ import annotations

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class SiteUser(db.Model):
    __tablename__ = "site_users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def to_dict(self) -> dict:
        return {"id": self.id, "username": self.username}


class SiteProject(db.Model):
    __tablename__ = "site_projects"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image = db.Column(db.Text, nullable=False)
    album = db.Column(db.JSON, nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        album = self.album if isinstance(self.album, list) else ([self.image] if self.image else [])
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            # `image` = nome da coluna; `mainImage` = nome usado pelo frontend React.
            "image": self.image,
            "mainImage": self.image,
            "album": album,
            "description": self.description or "",
        }


class SiteTimeline(db.Model):
    __tablename__ = "site_timeline"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.String(10), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "year": self.year,
            "title": self.title,
            "description": self.description or "",
            "image": self.image or "",
        }


class SiteSettings(db.Model):
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)  # sempre 1
    hero_image = db.Column(db.Text, nullable=True)
    about_image = db.Column(db.Text, nullable=True)
    whatsapp = db.Column(db.String(30), nullable=True)
    instagram = db.Column(db.String(255), nullable=True)
    address_json = db.Column(db.JSON, nullable=True)

    def to_dict(self) -> dict:
        return {
            "heroImage": self.hero_image or "",
            "aboutImage": self.about_image or "",
            "whatsapp": self.whatsapp or "",
            "instagram": self.instagram or "",
            "address": self.address_json or {},
        }
