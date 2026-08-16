"""
Unit tests for PII Detection Module

Tests comprehensive PII detection functionality including:
- Pattern matching for various PII types
- Parameter analysis
- Schema analysis (request/response bodies)
- Compliance scoring
- Report generation

Author: Contract Testing Framework
Date: 2025-01-20
"""

import pytest

from core.pii_detector import (
    PIIDetector,
    PIIType,
    PIISeverity,
    PIIMatch,
    PIIDetectionResult,
    create_pii_summary_report
)


class TestPIIDetector:
    """Test suite for PIIDetector class."""
    
    @pytest.fixture
    def detector(self):
        """Create PIIDetector instance for testing."""
        return PIIDetector()
    
    def test_initialization(self, detector):
        """Test PIIDetector initialization."""
        assert detector is not None
        assert hasattr(detector, 'pii_patterns')
        assert hasattr(detector, 'severity_mapping')
        assert hasattr(detector, 'pii_recommendations')
        
        # Check that all PII types have patterns
        for pii_type in PIIType:
            # USER_ID is registered conditionally: it is only added when
            # user_id is absent from the configured non-PII field list, so it
            # is legitimately missing under the default configuration.
            if pii_type is PIIType.USER_ID:
                continue
            assert pii_type in detector.pii_patterns
            assert pii_type in detector.severity_mapping
    
    def test_pii_pattern_matching(self, detector):
        """Test PII pattern matching functionality."""
        # Test SSN patterns
        assert detector._match_pii_pattern("ssn") == PIIType.SSN
        assert detector._match_pii_pattern("social_security_number") == PIIType.SSN
        assert detector._match_pii_pattern("tax_id") == PIIType.SSN
        
        # Test email patterns
        assert detector._match_pii_pattern("email") == PIIType.EMAIL
        assert detector._match_pii_pattern("email_address") == PIIType.EMAIL
        assert detector._match_pii_pattern("user_email") == PIIType.EMAIL
        
        # Test phone patterns
        assert detector._match_pii_pattern("phone") == PIIType.PHONE
        assert detector._match_pii_pattern("phone_number") == PIIType.PHONE
        assert detector._match_pii_pattern("mobile") == PIIType.PHONE
        
        # Test credit card patterns
        assert detector._match_pii_pattern("credit_card") == PIIType.CREDIT_CARD
        assert detector._match_pii_pattern("card_number") == PIIType.CREDIT_CARD
        
        # Test name patterns
        assert detector._match_pii_pattern("first_name") == PIIType.FIRST_NAME
        assert detector._match_pii_pattern("last_name") == PIIType.LAST_NAME
        assert detector._match_pii_pattern("full_name") == PIIType.FULL_NAME
        
        # Test non-PII
        assert detector._match_pii_pattern("product_id") is None
        assert detector._match_pii_pattern("status") is None
        assert detector._match_pii_pattern("") is None
        assert detector._match_pii_pattern(None) is None
    
    def test_detect_pii_in_parameter(self, detector):
        """Test PII detection in API parameters."""
        # Test parameter with PII in name
        param_schema = {
            "name": "email",
            "type": "string",
            "description": "User email address"
        }
        
        matches = detector.detect_pii_in_parameter(
            "email", param_schema, "query", "/users"
        )
        
        assert len(matches) >= 1
        assert any(match.pii_type == PIIType.EMAIL for match in matches)
        assert any(match.severity == PIISeverity.HIGH for match in matches)
        # The implementation emits "<location>_parameter", matching the
        # snake_case convention the request_body assertions below rely on.
        assert any(match.context == "query_parameter" for match in matches)
    
    def test_detect_pii_in_parameter_description(self, detector):
        """Test PII detection in parameter descriptions."""
        param_schema = {
            "name": "user_info",
            "type": "string",
            "description": "Social security number for verification"
        }
        
        matches = detector.detect_pii_in_parameter(
            "user_info", param_schema, "header", "/verify"
        )
        
        assert len(matches) >= 1
        ssn_match = next((m for m in matches if m.pii_type == PIIType.SSN), None)
        assert ssn_match is not None
        assert ssn_match.severity == PIISeverity.CRITICAL
        assert ssn_match.confidence == 0.8  # Lower confidence for description match
    
    def test_detect_pii_in_schema_object(self, detector):
        """Test PII detection in object schemas."""
        schema = {
            "type": "object",
            "properties": {
                "first_name": {
                    "type": "string",
                    "description": "User's first name"
                },
                "email": {
                    "type": "string",
                    "format": "email"
                },
                "ssn": {
                    "type": "string",
                    "description": "Social security number"
                },
                "product_id": {
                    "type": "string",
                    "description": "Product identifier"
                }
            }
        }
        
        matches = detector.detect_pii_in_schema(schema, "request_body")
        
        # Should detect first_name, email, and ssn
        assert len(matches) >= 3
        
        pii_types_found = {match.pii_type for match in matches}
        assert PIIType.FIRST_NAME in pii_types_found
        assert PIIType.EMAIL in pii_types_found
        assert PIIType.SSN in pii_types_found
        
        # Check severities
        severities_found = {match.severity for match in matches}
        assert PIISeverity.CRITICAL in severities_found  # SSN
        assert PIISeverity.HIGH in severities_found      # Email
        assert PIISeverity.MEDIUM in severities_found    # First name
    
    def test_detect_pii_in_schema_array(self, detector):
        """Test PII detection in array schemas."""
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string"
                    }
                }
            }
        }
        
        matches = detector.detect_pii_in_schema(schema, "response")
        
        assert len(matches) >= 1
        phone_match = next((m for m in matches if m.pii_type == PIIType.PHONE), None)
        assert phone_match is not None
        assert phone_match.severity == PIISeverity.HIGH
    
    def test_detect_pii_in_schema_reference(self, detector):
        """Test PII detection in schema references."""
        # `assert len(matches) >= 0` used to stand here, which is true of every
        # possible implementation including one that returns nothing at all.
        # The $ref handling was rewritten end to end and this test did not
        # notice, which is what a test with no oracle is worth.
        root = {
            "components": {
                "schemas": {
                    "UserProfile": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string"},
                            "order_count": {"type": "integer"},
                        },
                    }
                }
            }
        }

        matches = detector.detect_pii_in_schema(
            {"$ref": "#/components/schemas/UserProfile"}, "response", root_schema=root
        )

        # The reference is followed and the email behind it is found.
        assert [m.pii_type for m in matches] == [PIIType.EMAIL]
        assert matches[0].field_path == "email"

    def test_unresolvable_ref_is_recorded_not_invented(self, detector):
        """A reference that cannot be followed must not become a PII finding.

        It used to emit a fabricated USER_ID match, so a schema containing no
        personal data at all still reported one, and the compliance score moved
        because of a reference the tool had simply failed to read.
        """
        matches = detector.detect_pii_in_schema(
            {"$ref": "#/components/schemas/Missing"}, "response", root_schema={}
        )

        assert matches == []
        assert detector.unresolved_refs
        assert detector.unresolved_refs[0]["ref"] == "#/components/schemas/Missing"

    def test_a_self_referencing_schema_terminates(self, detector):
        """A tree node that points at itself is ordinary. Following it forever
        is not."""
        root = {
            "components": {
                "schemas": {
                    "Node": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string"},
                            "child": {"$ref": "#/components/schemas/Node"},
                        },
                    }
                }
            }
        }

        matches = detector.detect_pii_in_schema(
            {"$ref": "#/components/schemas/Node"}, "response", root_schema=root
        )
        assert [m.pii_type for m in matches] == [PIIType.EMAIL]
    
    def test_analyze_endpoint_pii_comprehensive(self, detector):
        """Test comprehensive endpoint PII analysis."""
        # Mock endpoint data
        parameters = [
            {
                "name": "email",
                "in": "query",
                "type": "string",
                "description": "User email"
            },
            {
                "name": "user_id",
                "in": "path",
                "type": "string"
            }
        ]
        
        request_body_schema = {
            "type": "object",
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "phone": {"type": "string"},
                "address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"}
                    }
                }
            }
        }
        
        response_schemas = {
            "200": {
                "type": "object",
                "properties": {
                    "user_profile": {
                        "type": "object",
                        "properties": {
                            "credit_card": {"type": "string"}
                        }
                    }
                }
            }
        }
        
        result = detector.analyze_endpoint_pii(
            api_id="test-api-123",
            api_title="Test API",
            endpoint_path="/users/{user_id}",
            http_method="POST",
            parameters=parameters,
            request_body_schema=request_body_schema,
            response_schemas=response_schemas
        )
        
        # Verify result structure
        assert isinstance(result, PIIDetectionResult)
        assert result.api_id == "test-api-123"
        assert result.api_title == "Test API"
        assert result.endpoint_path == "/users/{user_id}"
        assert result.http_method == "POST"
        assert result.total_pii_found > 0
        
        # Should have different severity levels
        assert len(result.critical_pii) > 0  # credit_card
        assert len(result.high_pii) > 0     # email, phone, address
        assert len(result.medium_pii) > 0   # first_name, last_name
        # user_id is NOT asserted here. NON_PII_FIELDS defaults to
        # ["user_id","id","uuid"], so under the default configuration the
        # detector deliberately treats it as a business identifier. Asserting
        # otherwise contradicts the shipped default; the opt-in path is
        # covered by test_user_id_detected_when_not_excluded below.
        
        # Compliance score should be affected
        assert result.compliance_score < 100.0
        
        # Should have recommendations
        assert len(result.recommendations) > 0
    
    def test_compliance_score_calculation(self, detector):
        """Test compliance score calculation."""
        # Test with no PII
        matches = []
        score = detector._calculate_compliance_score(matches)
        assert score == 100.0
        
        # Test with critical PII
        critical_match = PIIMatch(
            pii_type=PIIType.SSN,
            severity=PIISeverity.CRITICAL,
            field_name="ssn",
            field_path="/users",
            context="parameter",
            description="Test"
        )
        
        matches = [critical_match]
        score = detector._calculate_compliance_score(matches)
        assert score == 75.0  # 100 - 25 (critical penalty)
        
        # Test with multiple PII types
        high_match = PIIMatch(
            pii_type=PIIType.EMAIL,
            severity=PIISeverity.HIGH,
            field_name="email",
            field_path="/users",
            context="parameter",
            description="Test"
        )
        
        matches = [critical_match, high_match]
        score = detector._calculate_compliance_score(matches)
        assert score == 60.0  # 100 - 25 (critical) - 15 (high)
    
    def test_endpoint_recommendations_generation(self, detector):
        """Test endpoint recommendations generation."""
        # Test with no PII
        matches = []
        recommendations = detector._generate_endpoint_recommendations(matches)
        assert "No PII detected - endpoint appears compliant" in recommendations
        
        # Test with critical PII
        critical_match = PIIMatch(
            pii_type=PIIType.CREDIT_CARD,
            severity=PIISeverity.CRITICAL,
            field_name="card_number",
            field_path="/payment",
            context="request_body",
            description="Test"
        )
        
        matches = [critical_match]
        recommendations = detector._generate_endpoint_recommendations(matches)
        
        # Should include critical recommendations
        critical_recs = [r for r in recommendations if "CRITICAL" in r]
        assert len(critical_recs) > 0
        
        # Should include general security recommendations
        assert any("authentication" in r.lower() for r in recommendations)
        assert any("compliance" in r.lower() for r in recommendations)


class TestPIISummaryReport:
    """Test suite for PII summary report generation."""
    
    def test_create_summary_report_empty(self):
        """Test summary report with empty results."""
        results = []
        report = create_pii_summary_report(results)
        
        assert "error" in report
        assert report["error"] == "No results provided"
    
    def test_create_summary_report_with_data(self):
        """Test summary report with actual data."""
        # Create mock results
        result1 = PIIDetectionResult(
            api_id="api-1",
            api_title="API 1",
            endpoint_path="/users",
            http_method="GET",
            total_pii_found=3,
            compliance_score=75.0
        )
        
        # Add some PII matches
        result1.critical_pii = [
            PIIMatch(
                pii_type=PIIType.SSN,
                severity=PIISeverity.CRITICAL,
                field_name="ssn",
                field_path="/users",
                context="parameter",
                description="Test"
            )
        ]
        
        result1.high_pii = [
            PIIMatch(
                pii_type=PIIType.EMAIL,
                severity=PIISeverity.HIGH,
                field_name="email",
                field_path="/users",
                context="parameter",
                description="Test"
            )
        ]
        
        result1.medium_pii = [
            PIIMatch(
                pii_type=PIIType.FIRST_NAME,
                severity=PIISeverity.MEDIUM,
                field_name="first_name",
                field_path="/users",
                context="parameter",
                description="Test"
            )
        ]
        
        result2 = PIIDetectionResult(
            api_id="api-2",
            api_title="API 2",
            endpoint_path="/products",
            http_method="GET",
            total_pii_found=0,
            compliance_score=100.0
        )
        
        results = [result1, result2]
        report = create_pii_summary_report(results)
        
        # Verify report structure
        assert "summary" in report
        assert "pii_breakdown" in report
        assert "most_common_pii_types" in report
        assert "risk_assessment" in report
        assert "compliance_recommendations" in report
        
        # Verify summary data
        summary = report["summary"]
        assert summary["total_endpoints_analyzed"] == 2
        assert summary["endpoints_with_pii"] == 1
        assert summary["pii_exposure_rate"] == 50.0
        assert summary["average_compliance_score"] == 87.5  # (75 + 100) / 2
        
        # Verify PII breakdown
        breakdown = report["pii_breakdown"]
        assert breakdown["critical"] == 1
        assert breakdown["high"] == 1
        assert breakdown["medium"] == 1
        assert breakdown["low"] == 0
        assert breakdown["total"] == 3
        
        # Verify most common PII types
        common_pii = report["most_common_pii_types"]
        assert len(common_pii) > 0
        
        # Verify risk assessment
        risk = report["risk_assessment"]
        assert "CRITICAL" in risk  # Should be critical due to SSN
        
        # Verify recommendations
        recommendations = report["compliance_recommendations"]
        assert len(recommendations) > 0
        assert any("URGENT" in rec for rec in recommendations)


class TestPIITypes:
    """Test PII type enumerations and mappings."""
    
    def test_pii_type_enum(self):
        """Test PIIType enumeration."""
        # Test that all expected PII types exist
        expected_types = [
            "SSN", "CREDIT_CARD", "PASSPORT", "DRIVER_LICENSE", "BANK_ACCOUNT",
            "EMAIL", "PHONE", "DATE_OF_BIRTH", "ADDRESS", "IP_ADDRESS",
            "FIRST_NAME", "LAST_NAME", "FULL_NAME", "USERNAME", "USER_ID"
        ]
        
        for type_name in expected_types:
            assert hasattr(PIIType, type_name)
            pii_type = getattr(PIIType, type_name)
            assert isinstance(pii_type, PIIType)
    
    def test_pii_severity_enum(self):
        """Test PIISeverity enumeration."""
        expected_severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        
        for severity_name in expected_severities:
            assert hasattr(PIISeverity, severity_name)
            severity = getattr(PIISeverity, severity_name)
            assert isinstance(severity, PIISeverity)
    
    def test_severity_mapping_completeness(self):
        """Test that all PII types have severity mappings."""
        detector = PIIDetector()
        
        for pii_type in PIIType:
            assert pii_type in detector.severity_mapping
            severity = detector.severity_mapping[pii_type]
            assert isinstance(severity, PIISeverity)


class TestPIIMatchDataclass:
    """Test PIIMatch dataclass functionality."""
    
    def test_pii_match_creation(self):
        """Test PIIMatch creation and attributes."""
        match = PIIMatch(
            pii_type=PIIType.EMAIL,
            severity=PIISeverity.HIGH,
            field_name="user_email",
            field_path="/users/profile",
            context="request_body",
            description="Email field detected",
            pattern_matched="email",
            confidence=0.95,
            recommendations=["Validate email format", "Implement opt-out"]
        )
        
        assert match.pii_type == PIIType.EMAIL
        assert match.severity == PIISeverity.HIGH
        assert match.field_name == "user_email"
        assert match.field_path == "/users/profile"
        assert match.context == "request_body"
        assert match.description == "Email field detected"
        assert match.pattern_matched == "email"
        assert match.confidence == 0.95
        assert len(match.recommendations) == 2
    
    def test_pii_match_defaults(self):
        """Test PIIMatch default values."""
        match = PIIMatch(
            pii_type=PIIType.PHONE,
            severity=PIISeverity.HIGH,
            field_name="phone",
            field_path="/contact",
            context="parameter",
            description="Phone detected"
        )
        
        assert match.pattern_matched is None
        assert match.confidence == 1.0
        assert match.recommendations == []


class TestPIIDetectionResult:
    """Test PIIDetectionResult dataclass functionality."""
    
    def test_detection_result_creation(self):
        """Test PIIDetectionResult creation and defaults."""
        result = PIIDetectionResult(
            api_id="test-api",
            api_title="Test API",
            endpoint_path="/test",
            http_method="GET"
        )
        
        assert result.api_id == "test-api"
        assert result.api_title == "Test API"
        assert result.endpoint_path == "/test"
        assert result.http_method == "GET"
        assert result.total_pii_found == 0
        assert result.critical_pii == []
        assert result.high_pii == []
        assert result.medium_pii == []
        assert result.low_pii == []
        assert result.compliance_score == 100.0
        assert result.recommendations == []


if __name__ == "__main__":
    pytest.main([__file__])


class TestUserIdConfiguration:
    """user_id is PII or not depending on NON_PII_FIELDS, so cover both."""

    def test_user_id_ignored_by_default(self, monkeypatch):
        monkeypatch.delenv("NON_PII_FIELDS", raising=False)
        detector = PIIDetector()
        assert detector._match_pii_pattern("user_id", "body.user_id") is None

    def test_user_id_detected_when_not_excluded(self, monkeypatch):
        monkeypatch.setenv("NON_PII_FIELDS", '["uuid"]')
        detector = PIIDetector()
        assert detector._match_pii_pattern("user_id", "body.user_id") is PIIType.USER_ID

    def test_nested_field_is_judged_by_its_own_name(self, monkeypatch):
        """A non-PII segment in the path must not suppress the fields under it:
        under /users/{user_id} a credit card was reported as clean."""
        monkeypatch.delenv("NON_PII_FIELDS", raising=False)
        detector = PIIDetector()
        got = detector._match_pii_pattern("credit_card", "/users/{user_id}.body.credit_card")
        assert got is PIIType.CREDIT_CARD

    def test_government_identifier_is_not_swallowed_by_the_id_filter(self, monkeypatch):
        """Any field whose name merely contained "id" was discarded, which hid
        tax_id and passport_id."""
        monkeypatch.delenv("NON_PII_FIELDS", raising=False)
        detector = PIIDetector()
        assert detector._match_pii_pattern("tax_id", "body.tax_id") is PIIType.SSN
        assert detector._match_pii_pattern("passport_id", "body.passport_id") is PIIType.PASSPORT


class TestDetectionGapsFoundBeforePublication:
    """
    Each test here corresponds to a case the detector reported clean while
    personal data was present.

    A false negative is the worst outcome this tool can produce. A false
    positive costs somebody ten minutes; a false negative means an API ships
    with personal data in it and a report that says otherwise.
    """

    @pytest.fixture
    def detector(self):
        return PIIDetector()

    @pytest.mark.parametrize("field_name", [
        "government_id", "national_id", "citizen_id", "voter_id",
        "aadhaar_number", "pan_number", "identity_card",
    ])
    def test_government_identifiers_are_detected(self, detector, field_name):
        """The README named `government_id` as release-blocking. No pattern
        matched it, so the one example in the documentation was the one thing
        the detector could not see."""
        schema = {"type": "object", "properties": {field_name: {"type": "string"}}}
        matches = detector.detect_pii_in_schema(schema, "response")
        assert [m.pii_type for m in matches] == [PIIType.GOVERNMENT_ID]
        assert matches[0].severity == PIISeverity.CRITICAL

    @pytest.mark.parametrize("fmt,expected", [
        ("email", PIIType.EMAIL),
        ("idn-email", PIIType.EMAIL),
        ("ipv4", PIIType.IP_ADDRESS),
        ("ipv6", PIIType.IP_ADDRESS),
    ])
    def test_declared_format_is_honoured(self, detector, fmt, expected):
        """OpenAPI states what a string holds. A field called `contact` with
        `format: email` is an email address whatever it is named, and name-only
        matching called it clean."""
        schema = {"type": "object",
                  "properties": {"contact": {"type": "string", "format": fmt}}}
        matches = detector.detect_pii_in_schema(schema, "response")
        assert expected in [m.pii_type for m in matches]

    def test_a_neutral_format_is_not_treated_as_pii(self, detector):
        schema = {"type": "object",
                  "properties": {"created": {"type": "string", "format": "date-time"}}}
        assert detector.detect_pii_in_schema(schema, "response") == []

    def test_format_does_not_double_count_an_already_named_field(self, detector):
        # `email` with `format: email` is one finding, not two, or the risk
        # score reflects how verbose the spec author was.
        schema = {"type": "object",
                  "properties": {"email": {"type": "string", "format": "email"}}}
        matches = detector.detect_pii_in_schema(schema, "response")
        assert len(matches) == 1

    @pytest.mark.parametrize("keyword", ["allOf", "oneOf", "anyOf"])
    def test_composition_branches_are_walked(self, detector, keyword):
        """Composition is ordinary OpenAPI. None of these branches were
        traversed, so anything declared inside one was invisible."""
        schema = {keyword: [
            {"type": "object", "properties": {"ssn": {"type": "string"}}},
        ]}
        matches = detector.detect_pii_in_schema(schema, "request_body")
        assert PIIType.SSN in [m.pii_type for m in matches]

    def test_additional_properties_are_walked(self, detector):
        schema = {"type": "object", "additionalProperties": {
            "type": "object", "properties": {"email": {"type": "string"}}}}
        matches = detector.detect_pii_in_schema(schema, "response")
        assert PIIType.EMAIL in [m.pii_type for m in matches]

    def test_array_items_are_walked_alongside_properties(self, detector):
        """This was an `elif`, so a schema declaring both had its items
        skipped."""
        schema = {
            "type": "array",
            "properties": {"count": {"type": "integer"}},
            "items": {"type": "object", "properties": {"email": {"type": "string"}}},
        }
        matches = detector.detect_pii_in_schema(schema, "response")
        assert PIIType.EMAIL in [m.pii_type for m in matches]

    def test_pii_nested_behind_a_reference_inside_composition(self, detector):
        """The combination is where real specs live: allOf pulling in a shared
        component that holds the personal data."""
        root = {"components": {"schemas": {
            "Contact": {"type": "object",
                        "properties": {"email": {"type": "string"}}}}}}
        schema = {"allOf": [
            {"type": "object", "properties": {"order_id": {"type": "string"}}},
            {"$ref": "#/components/schemas/Contact"},
        ]}
        matches = detector.detect_pii_in_schema(
            schema, "response", root_schema=root)
        assert PIIType.EMAIL in [m.pii_type for m in matches]

    def test_a_genuinely_clean_schema_stays_clean(self, detector):
        """The counterweight: none of the above may be bought by flagging
        everything."""
        schema = {"type": "object", "properties": {
            "order_id": {"type": "string"},
            "quantity": {"type": "integer"},
            "status": {"type": "string", "enum": ["open", "closed"]},
            "items": {"type": "array", "items": {
                "type": "object", "properties": {"sku": {"type": "string"}}}},
        }}
        assert detector.detect_pii_in_schema(schema, "response") == []
