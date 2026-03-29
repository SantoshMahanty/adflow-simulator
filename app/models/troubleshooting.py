from datetime import datetime

from . import TABLE_PREFIX, db


class TroubleshootingIssue(db.Model):
    __tablename__ = f"{TABLE_PREFIX}troubleshooting_issues"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    symptoms = db.Column(db.Text, nullable=False)
    likely_causes = db.Column(db.Text, nullable=False)
    where_to_check = db.Column(db.Text, nullable=False)
    recommended_fix = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(30), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    related_module = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class TroubleshootingSheetRow(db.Model):
    __tablename__ = f"{TABLE_PREFIX}troubleshooting_sheet_rows"

    id = db.Column(db.Integer, primary_key=True)
    issue_title = db.Column(db.String(160), nullable=False)
    line_item_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}line_items.id", ondelete="SET NULL"))
    campaign_name = db.Column(db.String(160), nullable=False)
    problem = db.Column(db.Text, nullable=False)
    possible_reason = db.Column(db.Text, nullable=False)
    where_to_check = db.Column(db.Text, nullable=False)
    suggested_fix = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(30), nullable=False)
    owner = db.Column(db.String(120), nullable=False)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(50), nullable=False, default="open")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    line_item = db.relationship("LineItem", back_populates="troubleshooting_rows")
