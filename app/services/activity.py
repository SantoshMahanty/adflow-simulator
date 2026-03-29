from flask import g

from ..models import ActivityLog, db


def log_activity(entity_type, entity_id, action, message, details=None):
    actor = getattr(g, "user", None)
    log = ActivityLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        message=message,
        details=details or {},
        actor_id=actor.id if actor else None,
    )
    db.session.add(log)
    db.session.commit()
    return log
