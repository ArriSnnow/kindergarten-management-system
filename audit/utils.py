from audit.models import AuditLog


def log_action(actor, action, instance, details=''):
    """Records an immutable audit trail entry for a sensitive admin action."""
    AuditLog.objects.create(
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        action=action,
        model_name=instance._meta.model_name,
        object_id=str(instance.pk),
        object_repr=str(instance),
        details=details,
    )
