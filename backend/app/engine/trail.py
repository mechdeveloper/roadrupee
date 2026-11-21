"""Complaint trail funnel, computed from the data (never hard-coded)."""
from __future__ import annotations


def funnel(complaints, wo) -> dict:
    """total -> duplicates -> unique issues -> linked to a work order (held / failed) -> open or in progress / forwarded / rejected.

    A complaint is 'failed' when any work order it is linked to was reopened within 30 days, otherwise 'held'.
    Statuses come straight from complaints.status; the groups below the unique-issue line sum to it.
    """
    failed_by: dict[str, bool] = {}
    for r in wo.itertuples():
        for cid in str(r.linked_complaint_ids or "").split("|"):
            cid = cid.strip()
            if cid and cid != "nan":
                failed_by[cid] = failed_by.get(cid, False) or bool(r.reopened)
    st = complaints.status.fillna("")
    dup = st == "Closed - Duplicate"
    uniq = complaints[~dup]
    linked = uniq.complaint_id.isin(failed_by)
    failed = int(sum(failed_by[c] for c in uniq.complaint_id[linked]))
    s = uniq.status.fillna("")
    return {
        "total": int(len(complaints)),
        "duplicates": int(dup.sum()),
        "unique": int(len(uniq)),
        "linked": int(linked.sum()),
        "held": int(linked.sum()) - failed,
        "failed": failed,
        "open_or_in_progress": int(s.isin(["Open", "In Progress"]).sum()),
        "forwarded": int(s.str.startswith("Forwarded").sum()),
        "rejected": int(s.str.startswith("Rejected").sum()),
    }
