from datetime import date

from .domain import Authority, Claim, Conflict, Expert, Resolution, Source, Visibility


SOURCES = (
    Source(
        id="src-be-remote-2026",
        title="Belgium Remote Work Abroad Policy 2026",
        source_type="official_policy",
        authority=Authority.OFFICIAL,
        owner="People Operations Belgium",
        country="BE",
        effective_from=date(2026, 1, 1),
        effective_until=None,
        visibility=Visibility.HR,
        content="Belgian employees may work temporarily from another EU country. Manager approval is required only when the assignment exceeds 10 working days.",
    ),
    Source(
        id="src-be-handbook-2024",
        title="Belgium Employee Handbook 2024",
        source_type="employee_handbook",
        authority=Authority.OFFICIAL,
        owner="People Operations Belgium",
        country="BE",
        effective_from=date(2024, 1, 1),
        effective_until=date(2025, 12, 31),
        visibility=Visibility.HR,
        content="Manager approval is needed for international remote work exceeding 5 working days.",
        superseded_by="src-be-remote-2026",
    ),
    Source(
        id="src-teams-mobility",
        title="Teams — HR Global Mobility: 2026 remote-work update",
        source_type="teams_message",
        authority=Authority.COLLABORATIVE,
        owner="Global Mobility Team",
        country="BE",
        effective_from=date(2026, 1, 1),
        effective_until=None,
        visibility=Visibility.HR,
        content="Confirmed: the Belgium threshold changed from 5 to 10 working days on 1 January 2026. Please use the published policy.",
    ),
    Source(
        id="src-nl-remote-2026",
        title="Netherlands Remote Work Abroad Policy 2026",
        source_type="official_policy",
        authority=Authority.OFFICIAL,
        owner="People Operations Netherlands",
        country="NL",
        effective_from=date(2026, 1, 1),
        effective_until=None,
        visibility=Visibility.HR,
        content="Dutch employees require approval for assignments exceeding 15 working days.",
    ),
    Source(
        id="src-shared-pdf",
        title="Remote-work notes.pdf",
        source_type="shared_file",
        authority=Authority.UNVERIFIED,
        owner=None,
        country=None,
        effective_from=None,
        effective_until=None,
        visibility=Visibility.INTERNAL,
        content="People can work abroad for up to 20 days without approval.",
    ),
    Source(
        id="src-be-overtime-a",
        title="Belgium Payroll Procedure — Overtime 2026",
        source_type="official_policy",
        authority=Authority.OFFICIAL,
        owner="Payroll Operations Belgium",
        country="BE",
        effective_from=date(2026, 1, 1),
        effective_until=None,
        visibility=Visibility.PAYROLL,
        content="Process qualifying overtime with the standard 150% premium.",
    ),
    Source(
        id="src-be-overtime-b",
        title="Belgium Customer Configuration Guide — Overtime",
        source_type="official_policy",
        authority=Authority.OFFICIAL,
        owner="Payroll Compliance Belgium",
        country="BE",
        effective_from=date(2026, 2, 1),
        effective_until=None,
        visibility=Visibility.PAYROLL,
        content="For this customer configuration, qualifying overtime must be processed with a 200% premium.",
    ),
)

CLAIMS = (
    Claim("clm-be-10-days", "src-be-remote-2026", "remote_work_abroad_approval_threshold", "Approval is required above 10 working days.", "BE", date(2026, 1, 1), None, 10),
    Claim("clm-be-5-days", "src-be-handbook-2024", "remote_work_abroad_approval_threshold", "Approval is required above 5 working days.", "BE", date(2024, 1, 1), date(2025, 12, 31), 5),
    Claim("clm-teams-10-days", "src-teams-mobility", "remote_work_abroad_approval_threshold", "Belgium threshold changed to 10 working days.", "BE", date(2026, 1, 1), None, 10),
    Claim("clm-nl-15-days", "src-nl-remote-2026", "remote_work_abroad_approval_threshold", "Approval is required above 15 working days.", "NL", date(2026, 1, 1), None, 15),
    Claim("clm-unowned-20-days", "src-shared-pdf", "remote_work_abroad_approval_threshold", "Approval is required above 20 working days.", None, None, None, 20),
    Claim("clm-overtime-150", "src-be-overtime-a", "overtime_premium", "Qualifying overtime gets a 150% premium.", "BE", date(2026, 1, 1), None, 150),
    Claim("clm-overtime-200", "src-be-overtime-b", "overtime_premium", "This customer configuration gets a 200% premium.", "BE", date(2026, 2, 1), None, 200),
)

CONFLICTS = (
    Conflict("conf-remote-history", "clm-be-5-days", "clm-be-10-days", "superseded_policy", "resolved", "medium"),
    Conflict("conf-overtime-current", "clm-overtime-150", "clm-overtime-200", "current_policy_conflict", "open", "high"),
)

EXPERTS = (
    Expert("exp-anna", "Anna De Smet", "Payroll Compliance", ("overtime_premium", "payroll_compliance"), ("BE",)),
    Expert("exp-sarah", "Sarah Peeters", "People Operations", ("remote_work_abroad_approval_threshold", "global_mobility"), ("BE",)),
)

RESOLUTIONS: tuple[Resolution, ...] = ()
