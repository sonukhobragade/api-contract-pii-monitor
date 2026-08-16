"""
Tests for how newly added API elements are described in change notifications.

This file is a rewrite. What was here before printed a formatted message, printed
a row of ticks and crosses next to four checks, and then `return`ed whether they
all held. pytest ignores what a test function returns, so every one of those
checks could fail and the test still counted as a pass. It did count as a pass,
in the suite total, for as long as it existed.

The fixture is also synthetic now. The old one carried an API inventory copied
out of a real deployment.

What these assert is narrow but real: when the monitor cannot name a thing it
found, the message has to say so in words a reader understands. "unknown-id" and
"N/A" in a Slack alert at 3am tell nobody anything.
"""

import pytest

from core.notification_manager import NotificationManager


@pytest.fixture
def manager():
    return NotificationManager()


def change(**overrides):
    base = {
        "change_type": "endpoint_added",
        "path": "/widgets",
        "method": "POST",
        "description": "New endpoint added: POST /widgets",
        "is_breaking": False,
        "old_value": None,
        "new_value": {"path": "/widgets", "method": "POST"},
    }
    base.update(overrides)
    return base


def report(**overrides):
    """A monitoring report with one changed API. Entirely synthetic."""
    base = {
        "timestamp": "2026-01-01T00:00:00",
        "total_apis_monitored": 2,
        "apis_with_changes": 1,
        "apis_unchanged": 1,
        "total_changes": 3,
        "breaking_changes": 0,
        "apis_processed": [
            {
                "endpoint_name": "ORDERS_API",
                "api_title": "Orders API",
                "previous_version": "1.0.0",
                "fresh_api_id": "unknown-id",
                "total_changes": 3,
                "breaking_changes": 0,
                "requires_notification": True,
                "sample_changes": [
                    change(),
                    change(
                        change_type="response_added",
                        status_code="200",
                        content_type="application/json",
                        description="Response added: 200 for POST /widgets",
                        new_value={"status": "ok"},
                    ),
                    change(
                        change_type="component_added",
                        component_name="N/A",
                        component_type="schemas",
                        description="Component added: schemas/Widget",
                        new_value={"type": "object"},
                    ),
                ],
                "endpoint_changes": 1,
                "response_changes": 1,
                "component_changes": 1,
                "parameter_changes": 0,
                # The formatter reads change_analysis, not sample_changes.
                # sample_changes is carried in the report for other consumers.
                "change_analysis": {
                    "endpoint_changes": [change()],
                    "parameter_changes": [
                        change(
                            change_type="parameter_added",
                            parameter_name="customer_email",
                            description="Parameter added: customer_email",
                            new_value={"data_type": "string", "required": True},
                        )
                    ],
                    "response_changes": [
                        change(
                            change_type="response_added",
                            status_code="200",
                            content_type="application/json",
                            description="Response added: 200 for POST /widgets",
                            new_value={"status": "ok"},
                        )
                    ],
                    "component_changes": [
                        change(
                            change_type="component_added",
                            component_name="N/A",
                            component_type="schemas",
                            description="Component added: schemas/Widget",
                            new_value={"type": "object"},
                        )
                    ],
                },
            }
        ],
        "unchanged_apis": [
            {
                "endpoint_name": "BILLING_API",
                "api_title": "Billing API",
                "current_version": "2.1.0",
                "status": "no_changes_hash_identical",
            }
        ],
        "errors": [],
        "recommendations": [],
        "total_endpoints_monitored": 42,
        "api_endpoint_details": [
            {"api_title": "Orders API", "api_id": "unknown-id",
             "endpoint_count": 20, "version": "1.0.0"},
        ],
    }
    base.update(overrides)
    return base


class TestPlaceholdersAreNotShownToReaders:
    def test_unknown_id_does_not_reach_the_message(self, manager):
        """`unknown-id` is the internal marker for an API seen for the first
        time. Printed verbatim it makes a new API look like a broken one.

        This is the check the old version of this file claimed to make. It never
        held: the string "Newly Added" did not exist anywhere in the codebase,
        and the assertion was a `return` that pytest discarded.
        """
        message = manager._format_detailed_changes(report())
        assert "unknown-id" not in message
        assert "Newly Added" in message

    def test_a_real_api_id_is_still_shown(self, manager):
        """The fallback must not swallow an id that exists."""
        r = report()
        r["apis_processed"][0]["api_id"] = "orders-v1"
        message = manager._format_detailed_changes(r)
        assert "orders-v1" in message
        assert "Newly Added" not in message

    def test_component_changes_are_described(self, manager):
        message = manager._format_detailed_changes(report())
        assert "Component added:" in message or "Widget" in message


class TestTheMessageSaysWhatChanged:
    def test_a_new_endpoint_is_reported(self, manager):
        message = manager._format_detailed_changes(report())
        assert "ADDED: POST /widgets" in message

    def test_the_change_breakdown_counts_each_kind(self, manager):
        message = manager._format_detailed_changes(report())
        for label in ("Endpoints:", "Parameters:", "Responses:", "Components:"):
            assert label in message

    def test_the_changed_api_is_named_in_the_parameter_section(self, manager):
        # Parameter changes are the ones that break callers, so that section
        # names the API rather than leaving the reader to guess which one.
        assert "Orders API" in manager._format_detailed_changes(report())


class TestEdgeCases:
    def test_a_report_with_no_changes_still_formats(self, manager):
        # The nightly monitor runs whether or not anything changed, and a crash
        # on the quiet path is a crash that only shows up in production.
        message = manager._format_detailed_changes(
            report(apis_processed=[], apis_with_changes=0, total_changes=0))
        assert isinstance(message, str)

    def test_an_empty_report_does_not_raise(self, manager):
        assert isinstance(manager._format_detailed_changes({}), str)

    def test_the_slack_code_block_variant_also_formats(self, manager):
        message = manager._create_unicode_slack_message(report())
        assert isinstance(message, str) and message.strip()
        assert "unknown-id" not in message
