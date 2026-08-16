"""
PII Detection Module for API Contract Testing

This module provides comprehensive detection of Personally Identifiable Information (PII)
in API parameters, request bodies, and response schemas. It identifies potential privacy
risks and compliance issues in OpenAPI specifications.

Author: Contract Testing Framework
Date: 2025-01-20
"""

import re
import logging
import os
import ast
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)


class PIIType(Enum):
    """Enumeration of PII types with severity levels."""
    
    # High Risk PII
    SSN = "social_security_number"
    CREDIT_CARD = "credit_card_number"
    PASSPORT = "passport_number"
    DRIVER_LICENSE = "driver_license"
    BANK_ACCOUNT = "bank_account_number"
    
    # Medium Risk PII
    EMAIL = "email_address"
    PHONE = "phone_number"
    DATE_OF_BIRTH = "date_of_birth"
    ADDRESS = "physical_address"
    IP_ADDRESS = "ip_address"
    
    # Government-issued identifiers other than the ones above. The README
    # advertised `government_id` as a release-blocking detection and no pattern
    # matched it, so a field with that exact name was reported clean.
    GOVERNMENT_ID = "government_id"

    # Low Risk PII
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    FULL_NAME = "full_name"
    USERNAME = "username"
    USER_ID = "user_id"


class PIISeverity(Enum):
    """PII severity levels for compliance and risk assessment."""
    
    CRITICAL = "critical"  # SSN, Credit Cards, Passport
    HIGH = "high"         # Email, Phone, DOB, Address
    MEDIUM = "medium"     # Names, Usernames
    LOW = "low"           # User IDs, non-sensitive identifiers


@dataclass
class PIIMatch:
    """Represents a detected PII instance."""
    
    pii_type: PIIType
    severity: PIISeverity
    field_name: str
    field_path: str
    context: str  # parameter, request_body, response
    description: str
    pattern_matched: Optional[str] = None
    confidence: float = 1.0
    recommendations: List[str] = field(default_factory=list)


@dataclass
class PIIDetectionResult:
    """Results of PII detection analysis."""
    
    api_id: str
    api_title: str
    endpoint_path: str
    http_method: str
    total_pii_found: int = 0
    critical_pii: List[PIIMatch] = field(default_factory=list)
    high_pii: List[PIIMatch] = field(default_factory=list)
    medium_pii: List[PIIMatch] = field(default_factory=list)
    low_pii: List[PIIMatch] = field(default_factory=list)
    compliance_score: float = 100.0
    recommendations: List[str] = field(default_factory=list)

    # Set when the endpoint could not be analysed. Callers used to construct a
    # bare result on exception, and a bare result reads as "0 PII found,
    # compliance 100" — a crash was indistinguishable from a clean endpoint,
    # which is the most dangerous shape a failure can take in a tool like this.
    analysis_failed: bool = False
    analysis_error: Optional[str] = None

    @classmethod
    def failed(cls, api_id: str, api_title: str, endpoint_path: str,
               http_method: str, error: str) -> "PIIDetectionResult":
        """A result that says it does not know, and never says it is clean."""
        return cls(
            api_id=api_id,
            api_title=api_title,
            endpoint_path=endpoint_path,
            http_method=http_method,
            compliance_score=0.0,
            analysis_failed=True,
            analysis_error=str(error)[:500],
            recommendations=[
                "This endpoint was not analysed. Treat it as unknown, not clean."
            ],
        )


class PIIDetector:
    """
    Comprehensive PII detection system for OpenAPI schemas.
    
    Detects PII in:
    - API parameters (query, path, header, cookie)
    - Request body schemas
    - Response schemas
    - Component schemas
    """
    
    def __init__(self):
        """Initialize the PII detector with patterns and severity mappings."""
        # Initialize non-PII fields first, as other methods depend on it
        self._initialize_non_pii_fields()
        self._initialize_pii_patterns()
        self._initialize_severity_mapping()
        self._initialize_recommendations()
        # References that could not be followed. Analysis behind them is
        # incomplete, and a caller that reports "no PII found" without saying
        # so is making a claim it has not checked.
        self.unresolved_refs: List[Dict[str, str]] = []
    
    def _initialize_pii_patterns(self) -> None:
        """Initialize regex patterns for PII detection."""
        self.pii_patterns = {
            # High Risk Patterns
            PIIType.SSN: [
                r'\b(?:\d{3}-\d{2}-\d{4}|\d{9})\b',
                # tax.?id covers TIN/ITIN/tax_id, which is the same class of
                # government identifier and was previously undetected.
                r'ssn|social.?security|tax.?id',
            ],
            PIIType.CREDIT_CARD: [
                r'\b(?:\d{4}[- ]?){4}\b',
                r'credit.?card|cc.?num|card.?number',
            ],
            PIIType.PASSPORT: [
                r'passport',
            ],
            PIIType.DRIVER_LICENSE: [
                r'driver.?licen[sc]e|driving.?licen[sc]e|dl.?number',
            ],
            PIIType.BANK_ACCOUNT: [
                r'bank.?account|account.?number|routing.?number',
            ],
            PIIType.GOVERNMENT_ID: [
                # National identifier schemes. Named explicitly because a
                # generic "id" pattern would match half of every API.
                r'government.?id|national.?id|citizen.?id|voter.?id',
                r'aadhaar|aadhar|pan.?number|nin\b|nino\b|bsn\b|sin\b',
                r'identity.?(?:card|number)|id.?card.?(?:no|number)',
            ],
            
            # Medium Risk Patterns
            PIIType.EMAIL: [
                r'email|e.?mail|mail',
            ],
            PIIType.PHONE: [
                r'phone|mobile|cell|telephone|contact.?number',
            ],
            PIIType.DATE_OF_BIRTH: [
                r'dob|birth.?date|date.?of.?birth|birthday',
            ],
            PIIType.ADDRESS: [
                r'address|street|city|state|zip|postal|country|location',
            ],
            PIIType.IP_ADDRESS: [
                r'ip.?address|ip.?addr|client.?ip|remote.?ip',
            ],
            
            # Low Risk Patterns
            PIIType.FIRST_NAME: [
                r'first.?name|given.?name|fname',
            ],
            PIIType.LAST_NAME: [
                r'last.?name|family.?name|surname|lname',
            ],
            PIIType.FULL_NAME: [
                r'full.?name|complete.?name|display.?name|name',
            ],
            PIIType.USERNAME: [
                r'username|user.?name|login|handle',
            ],
        }
        
        # Only add USER_ID detection if it's not in the non-PII fields
        # This ensures USER_ID detection is completely disabled when non-PII fields include user_id
        if not any("user_id" in pattern.pattern.lower() for pattern in self.non_pii_patterns):
            self.pii_patterns[PIIType.USER_ID] = [
                r'user.?id|uid|customer.?id|client.?id',
            ]
            logger.info("USER_ID detection enabled - not found in non-PII patterns")
        else:
            logger.info("USER_ID detection disabled - found in non-PII patterns")
    
    def _initialize_severity_mapping(self) -> None:
        """Map PII types to severity levels."""
        self.severity_mapping = {
            PIIType.SSN: PIISeverity.CRITICAL,
            PIIType.CREDIT_CARD: PIISeverity.CRITICAL,
            PIIType.PASSPORT: PIISeverity.CRITICAL,
            PIIType.DRIVER_LICENSE: PIISeverity.CRITICAL,
            PIIType.BANK_ACCOUNT: PIISeverity.CRITICAL,
            PIIType.GOVERNMENT_ID: PIISeverity.CRITICAL,
            
            PIIType.EMAIL: PIISeverity.HIGH,
            PIIType.PHONE: PIISeverity.HIGH,
            PIIType.DATE_OF_BIRTH: PIISeverity.HIGH,
            PIIType.ADDRESS: PIISeverity.HIGH,
            PIIType.IP_ADDRESS: PIISeverity.HIGH,
            
            PIIType.FIRST_NAME: PIISeverity.MEDIUM,
            PIIType.LAST_NAME: PIISeverity.MEDIUM,
            PIIType.FULL_NAME: PIISeverity.MEDIUM,
            PIIType.USERNAME: PIISeverity.MEDIUM,
            
            PIIType.USER_ID: PIISeverity.LOW,
        }
    
    def _initialize_recommendations(self) -> None:
        """Initialize security recommendations for each PII type."""
        self.pii_recommendations = {
            PIIType.GOVERNMENT_ID: [
                "Treat national identifiers as the most sensitive class of data",
                "Do not return them in responses unless legally required",
                "Encrypt at rest and restrict access to an audited path",
            ],
            PIIType.USER_ID: [
                "Use opaque, non-sequential identifiers in public responses",
                "Do not expose internal database ids to clients",
                "Scope every lookup to the authenticated caller",
            ],
            PIIType.SSN: [
                "Never store SSN in plain text",
                "Apply strong encryption and access controls",
                "Consider if SSN is truly necessary for business function"
            ],
            PIIType.CREDIT_CARD: [
                "Implement PCI DSS compliance",
                "Use tokenization for card data",
                "Never log credit card numbers",
                "Encrypt all payment data"
            ],
            PIIType.EMAIL: [
                "Implement email validation",
                "Consider hashing for lookups",
                "Provide opt-out mechanisms",
                "Follow CAN-SPAM regulations"
            ],
            PIIType.PHONE: [
                "Validate phone number formats",
                "Implement rate limiting for SMS",
                "Provide opt-out for communications",
                "Consider regional privacy laws"
            ],
            PIIType.ADDRESS: [
                "Encrypt address data",
                "Implement data retention policies",
                "Consider geolocation privacy",
                "Follow regional data laws"
            ],
        }
    
    def _initialize_non_pii_fields(self) -> None:
        """Initialize list of fields that should not be considered PII."""
        # Load .env file if it exists
        env_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
        
        # Get non-PII fields from environment variable
        non_pii_env = os.environ.get('NON_PII_FIELDS', '["user_id","id","uuid"]')
        
        try:
            # Try to parse as array
            self.non_pii_fields = ast.literal_eval(non_pii_env)
            if not isinstance(self.non_pii_fields, list):
                # If not a list, fall back to default
                self.non_pii_fields = ["user_id", "id", "uuid"]
        except (SyntaxError, ValueError):
            # If parsing fails, fall back to comma-separated format
            self.non_pii_fields = [field.strip() for field in non_pii_env.split(',')]
        
        # user_id is NOT force-added back. Re-appending it regardless of what
        # the operator configured made NON_PII_FIELDS a suggestion rather than
        # a setting, and left the conditional USER_ID pattern unreachable.

        # Anchored: these are field names, not regexes. Compiling "id" as a
        # bare pattern made it match inside tax_id, passport_id and
        # national_id, so government identifiers were skipped as non-PII —
        # the opposite of this tool's purpose.
        self.non_pii_patterns = [
            re.compile(rf"^{re.escape(name)}$", re.IGNORECASE)
            for name in self.non_pii_fields
        ]
        
        logger.info(f"Initialized non-PII fields: {self.non_pii_fields}")
    
    def detect_pii_in_parameter(
        self,
        param_name: str,
        param_schema: Dict[str, Any],
        param_location: str,
        endpoint_path: str
    ) -> List[PIIMatch]:
        """
        Detect PII in API parameter.
        
        Args:
            param_name: Parameter name
            param_schema: Parameter schema definition
            param_location: Parameter location (query, path, header, cookie)
            endpoint_path: API endpoint path
            
        Returns:
            List of PII matches found
        """
        matches = []
        context = f"{param_location}_parameter"
        
        # Check if field name or path contains PII indicators
        pii_type = self._match_pii_pattern(param_name, f"{endpoint_path}?{param_name}")
        if not pii_type and f"{endpoint_path}?{param_name}":
            pii_type = self._match_pii_pattern(f"{endpoint_path}?{param_name}", f"{endpoint_path}?{param_name}")
        if pii_type:
            severity = self.severity_mapping[pii_type]
            match = PIIMatch(
                pii_type=pii_type,
                severity=severity,
                field_name=param_name,
                field_path=f"{endpoint_path}?{param_name}",
                context=context,
                description=f"PII detected in {param_location} parameter name",
                pattern_matched=param_name,
                recommendations=self.pii_recommendations.get(pii_type, [])
            )
            matches.append(match)
        
        # Check description for PII patterns
        if 'description' in param_schema and param_schema['description']:
            description = param_schema['description'].lower()
            pii_type = self._match_pii_pattern(description)
            if pii_type:
                severity = self.severity_mapping[pii_type]
                match = PIIMatch(
                    pii_type=pii_type,
                    severity=severity,
                    field_name=param_name,
                    field_path=f"{endpoint_path}?{param_name}",
                    context=f"{param_location}_description",
                    description="PII detected in parameter description",
                    pattern_matched=description,
                    confidence=0.8,
                    recommendations=self.pii_recommendations.get(pii_type, [])
                )
                matches.append(match)
        
        return matches
    
    @staticmethod
    def _dedupe(matches: List[PIIMatch]) -> List[PIIMatch]:
        """
        Collapse repeat findings for the same field and the same PII type.

        A field called `national_id` described as "government identifier"
        matches on its name and again on its description. That is one piece of
        personal data, not two, and counting it twice inflates the totals and
        drags the compliance score down by an amount that depends on how
        thoroughly the spec was documented.

        The highest-confidence match wins, so a name match (1.0) is kept over
        the same finding inferred from prose (0.8).
        """
        best: Dict[tuple, PIIMatch] = {}
        for match in matches:
            key = (match.field_path or match.field_name, match.pii_type)
            current = best.get(key)
            if current is None or match.confidence > current.confidence:
                best[key] = match
        return list(best.values())

    def _resolve_ref(
        self, ref: str, root_schema: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve a local JSON pointer such as `#/components/schemas/Customer`.

        Only local references are resolved. A remote or file reference would
        mean fetching something over the network during analysis, which this
        tool deliberately does not do.
        """
        if not root_schema or not isinstance(ref, str) or not ref.startswith("#/"):
            return None

        node: Any = root_schema
        for part in ref[2:].split("/"):
            # Per RFC 6901.
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node if isinstance(node, dict) else None

    def detect_pii_in_schema(
        self,
        schema: Dict[str, Any],
        context: str,
        base_path: str = "",
        root_schema: Optional[Dict[str, Any]] = None,
        _seen_refs: Optional[set] = None,
    ) -> List[PIIMatch]:
        """
        Detect PII in a JSON schema (request/response body).

        Args:
            schema: JSON schema definition
            context: Context (request_body, response, component)
            base_path: Base path for nested schemas
            root_schema: The whole spec, so `$ref` can be followed. Without it
                references cannot be resolved and are recorded as unresolved
                rather than guessed at.
            _seen_refs: Internal. Guards against a schema that references itself.

        Returns:
            List of PII matches found
        """
        matches = []
        _seen_refs = set() if _seen_refs is None else _seen_refs

        if not isinstance(schema, dict):
            return matches

        # Handle schema references
        if '$ref' in schema:
            ref_path = schema['$ref']
            resolved = self._resolve_ref(ref_path, root_schema)

            if resolved is not None and ref_path not in _seen_refs:
                # Follow it. Previously this returned a fabricated USER_ID match
                # and stopped, so every field behind a $ref went unexamined
                # while the totals gained a finding that was not PII at all.
                return self.detect_pii_in_schema(
                    resolved, context, base_path,
                    root_schema=root_schema, _seen_refs=_seen_refs | {ref_path},
                )

            if ref_path in _seen_refs:
                return matches  # cycle; already walked

            # Genuinely unresolvable. Record it so a reader knows the analysis
            # is incomplete here, but do NOT invent a PII match: a clean report
            # must mean clean, and a fabricated finding corrupts the counts and
            # the compliance score alike.
            self.unresolved_refs.append(
                {"ref": ref_path, "path": base_path, "context": context}
            )
            logger.warning(
                "Unresolved schema reference %s at %s — fields behind it were "
                "not analysed", ref_path, base_path or "<root>"
            )
            return matches

        # Composition keywords. A schema using allOf/oneOf/anyOf is ordinary
        # OpenAPI, and none of these branches were walked, so PII declared
        # inside any of them was silently missed.
        for keyword in ("allOf", "oneOf", "anyOf"):
            for index, subschema in enumerate(schema.get(keyword) or []):
                if isinstance(subschema, dict):
                    matches.extend(self.detect_pii_in_schema(
                        subschema, context, f"{base_path}.{keyword}[{index}]",
                        root_schema=root_schema, _seen_refs=_seen_refs,
                    ))

        # A free-form map: `additionalProperties` carries the value schema.
        extra = schema.get("additionalProperties")
        if isinstance(extra, dict):
            matches.extend(self.detect_pii_in_schema(
                extra, context, f"{base_path}.*",
                root_schema=root_schema, _seen_refs=_seen_refs,
            ))

        # Check properties
        if 'properties' in schema and isinstance(schema['properties'], dict):
            for prop_name, prop_schema in schema['properties'].items():
                # Construct the field path
                field_path = f"{base_path}.{prop_name}" if base_path else prop_name
                
                # Check property name for PII indicators
                pii_type = self._match_pii_pattern(prop_name, field_path)
                if pii_type:
                    severity = self.severity_mapping[pii_type]
                    match = PIIMatch(
                        pii_type=pii_type,
                        severity=severity,
                        field_name=prop_name,
                        field_path=field_path,
                        context=context,
                        description=f"PII detected in {context} property name",
                        pattern_matched=prop_name,
                        recommendations=self.pii_recommendations.get(pii_type, [])
                    )
                    matches.append(match)
                
                # Check property description
                if isinstance(prop_schema, dict) and 'description' in prop_schema and prop_schema['description']:
                    description = prop_schema['description'].lower()
                    pii_type = self._match_pii_pattern(description)
                    if pii_type:
                        severity = self.severity_mapping[pii_type]
                        match = PIIMatch(
                            pii_type=pii_type,
                            severity=severity,
                            field_name=prop_name,
                            field_path=field_path,
                            context=f"{context}_description",
                            description="PII detected in property description",
                            pattern_matched=description,
                            confidence=0.8,
                            recommendations=self.pii_recommendations.get(pii_type, [])
                        )
                        matches.append(match)
                
                # Check the declared format. OpenAPI says what a string holds,
                # and a field named `contact` with `format: email` is an email
                # address no matter what it is called. Name-only matching
                # reported these clean.
                if isinstance(prop_schema, dict):
                    format_type = self._match_pii_format(prop_schema.get('format'))
                    if format_type and format_type != pii_type:
                        matches.append(PIIMatch(
                            pii_type=format_type,
                            severity=self.severity_mapping[format_type],
                            field_name=prop_name,
                            field_path=field_path,
                            context=f"{context}_format",
                            description=(
                                f"PII implied by declared format "
                                f"'{prop_schema.get('format')}'"
                            ),
                            pattern_matched=str(prop_schema.get('format')),
                            confidence=0.9,
                            recommendations=self.pii_recommendations.get(format_type, []),
                        ))

                # Recursively check nested schemas
                if isinstance(prop_schema, dict):
                    nested_matches = self.detect_pii_in_schema(
                        prop_schema, context, field_path,
                        root_schema=root_schema, _seen_refs=_seen_refs,
                    )
                    matches.extend(nested_matches)

        # Handle array items. This was an `elif`, so an array that also declared
        # `properties` never had its items walked.
        if schema.get('type') == 'array' and 'items' in schema:
            items_schema = schema['items']
            if isinstance(items_schema, dict):
                nested_matches = self.detect_pii_in_schema(
                    items_schema, context, f"{base_path}[]",
                    root_schema=root_schema, _seen_refs=_seen_refs,
                )
                matches.extend(nested_matches)

        return self._dedupe(matches)

    # OpenAPI `format` values that identify a person on their own.
    _PII_FORMATS = {
        "email": PIIType.EMAIL,
        "idn-email": PIIType.EMAIL,
        "ipv4": PIIType.IP_ADDRESS,
        "ipv6": PIIType.IP_ADDRESS,
        "hostname": PIIType.IP_ADDRESS,
        "phone": PIIType.PHONE,
        "tel": PIIType.PHONE,
    }

    def _match_pii_format(self, format_value: Any) -> Optional[PIIType]:
        """Map a declared OpenAPI `format` to a PII type, if it implies one."""
        if not isinstance(format_value, str):
            return None
        return self._PII_FORMATS.get(format_value.strip().lower())
    
    def _match_pii_pattern(self, text: str, field_path: str = "") -> Optional[PIIType]:
        """
        Match text against PII patterns.
        
        Args:
            text: Text to analyze
            field_path: Path to the field being analyzed (for non-PII filtering)
            
        Returns:
            PIIType if match found, None otherwise
        """
        if not text or not isinstance(text, str):
            return None
            
        # Debug logging for user_id detection
        if "user_id" in text.lower() or (field_path and "user_id" in field_path.lower()):
            logger.info(f"DEBUG: Found potential user_id in text: '{text}' or field_path: '{field_path}'")
        
        # Check if this field path is in the non-PII list
        if field_path:
            # Debug logging for field paths
            logger.info(f"DEBUG: Checking field_path: '{field_path}' against non-PII patterns: {[p.pattern for p in self.non_pii_patterns]}")
            
            # Matched against the field's own name, not the whole path.
            # Searching the full path meant one non-PII segment suppressed
            # everything below it: under /users/{user_id} a credit card in the
            # request body was reported as clean.
            leaf = field_path.split('.')[-1]
            for pattern in self.non_pii_patterns:
                if pattern.search(leaf):
                    logger.debug(f"Skipping non-PII field {leaf} (pattern: {pattern.pattern})")
                    return None
                    
            # Also check if text matches any non-PII pattern
            if text.lower() == "user_id" or "user_id" in text.lower():
                logger.info(f"DEBUG: Found 'user_id' in text: '{text}', but not filtered by patterns")
            
        text_lower = text.lower()
        
        # Whether user_id counts as PII is decided by NON_PII_FIELDS and
        # applied by the anchored check above. Hardcoding it here as well
        # ignored that setting entirely.
        leaf_name = (field_path.split(".")[-1] if field_path else text).strip().lower()
        for pattern in self.non_pii_patterns:
            if pattern.search(leaf_name):
                return None

        # Previously: if ANY non-PII pattern contained the substring "id",
        # every field whose name merely contained "id" was discarded before
        # pattern matching ran. That silently dropped tax_id, national_id and
        # passport_id — government identifiers this tool exists to find. The
        # non-PII list is already applied against field_path above, on word
        # boundaries, which is the check that was actually intended.

        for pii_type, patterns in self.pii_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    # No special case for USER_ID here: skipping it whenever
                    # the name contained "id" disabled the very pattern that
                    # had just been registered on purpose.
                    return pii_type
                    
        return None
    
    def _validate_pii_match(self, pii_type: PIIType, text: str) -> bool:
        """
        Validate PII match to avoid false positives.
        
        Args:
            pii_type: Detected PII type
            text: Text that matched the pattern
            
        Returns:
            True if valid PII match, False if false positive
        """
        # Filter out schema names that contain PII keywords but aren't actual PII fields
        schema_name_patterns = [
            r'response|request|schema|model|dto|vo|entity|component',
            r'api|gateway|service|controller|handler',
            r'multi|single|list|array|collection',
            r'public|private|internal|external',
            r'init|create|update|delete|get|post|put|patch'
        ]
        
        # If text matches schema name patterns, it's likely a false positive
        for pattern in schema_name_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # Additional checks for specific PII types
        if pii_type == PIIType.BANK_ACCOUNT:
            # Avoid matching schema names like "ApiResponseMultiBannerResponsePublic"
            if 'response' in text or 'api' in text or 'public' in text:
                return False
        
        return True
    
    def analyze_endpoint_pii(
        self,
        api_id: str,
        api_title: str,
        endpoint_path: str,
        http_method: str,
        parameters: List[Dict[str, Any]],
        request_body_schema: Optional[Dict[str, Any]] = None,
        response_schemas: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> PIIDetectionResult:
        """
        Comprehensive PII analysis for an API endpoint.
        
        Args:
            api_id: API identifier
            api_title: API title
            endpoint_path: Endpoint path
            http_method: HTTP method
            parameters: List of parameter definitions
            request_body_schema: Request body schema
            response_schemas: Response schemas by status code
            
        Returns:
            PIIDetectionResult with all findings
        """
        result = PIIDetectionResult(
            api_id=api_id,
            api_title=api_title,
            endpoint_path=endpoint_path,
            http_method=http_method
        )
        
        all_matches = []
        
        # Analyze parameters
        for param in parameters or []:
            param_matches = self.detect_pii_in_parameter(
                param.get('name', ''),
                param,
                param.get('in', 'unknown'),
                endpoint_path
            )
            all_matches.extend(param_matches)
        
        # Analyze request body
        if request_body_schema:
            request_matches = self.detect_pii_in_schema(
                request_body_schema,
                "request_body",
                f"{http_method} {endpoint_path}"
            )
            all_matches.extend(request_matches)
        
        # Analyze response schemas
        if response_schemas:
            for status_code, response_schema in response_schemas.items():
                response_matches = self.detect_pii_in_schema(
                    response_schema,
                    f"response_{status_code}",
                    f"{http_method} {endpoint_path}"
                )
                all_matches.extend(response_matches)
        
        # Categorize matches by severity
        for match in all_matches:
            if match.severity == PIISeverity.CRITICAL:
                result.critical_pii.append(match)
            elif match.severity == PIISeverity.HIGH:
                result.high_pii.append(match)
            elif match.severity == PIISeverity.MEDIUM:
                result.medium_pii.append(match)
            else:
                result.low_pii.append(match)
        
        result.total_pii_found = len(all_matches)
        
        # Calculate compliance score
        result.compliance_score = self._calculate_compliance_score(all_matches)
        
        # Generate recommendations
        result.recommendations = self._generate_endpoint_recommendations(all_matches)
        
        return result
    
    def _calculate_compliance_score(self, matches: List[PIIMatch]) -> float:
        """
        Calculate compliance score based on PII findings.
        
        Args:
            matches: List of PII matches
            
        Returns:
            Compliance score (0-100)
        """
        if not matches:
            return 100.0
        
        penalty_map = {
            PIISeverity.CRITICAL: 25.0,
            PIISeverity.HIGH: 15.0,
            PIISeverity.MEDIUM: 10.0,
            PIISeverity.LOW: 5.0
        }
        
        total_penalty = sum(penalty_map[match.severity] for match in matches)
        score = max(0.0, 100.0 - total_penalty)
        
        return round(score, 1)
    
    def _generate_endpoint_recommendations(
        self,
        matches: List[PIIMatch]
    ) -> List[str]:
        """
        Generate security recommendations based on PII findings.
        
        Args:
            matches: List of PII matches
            
        Returns:
            List of recommendations
        """
        recommendations = set()
        
        if not matches:
            return ["No PII detected - endpoint appears compliant"]
        
        # Add severity-based recommendations
        severities = {match.severity for match in matches}
        
        if PIISeverity.CRITICAL in severities:
            recommendations.add("🔴 CRITICAL: Implement immediate data protection measures")
            recommendations.add("Conduct security audit and penetration testing")
            recommendations.add("Implement data encryption at rest and in transit")
        
        if PIISeverity.HIGH in severities:
            recommendations.add("🟡 HIGH: Review data handling procedures")
            recommendations.add("Implement access logging and monitoring")
            recommendations.add("Consider data minimization strategies")
        
        if len(matches) > 5:
            recommendations.add("Consider endpoint redesign to reduce PII exposure")
        
        # Add general recommendations
        recommendations.add("Implement proper authentication and authorization")
        recommendations.add("Review data retention and deletion policies")
        recommendations.add("Ensure compliance with GDPR, CCPA, and other regulations")
        
        return sorted(list(recommendations))


def create_pii_summary_report(results: List[PIIDetectionResult]) -> Dict[str, Any]:
    """
    Create a summary report of PII detection across multiple endpoints.
    
    Args:
        results: List of PII detection results
        
    Returns:
        Summary report dictionary
    """
    if not results:
        return {"error": "No results provided"}
    
    total_endpoints = len(results)
    endpoints_with_pii = sum(1 for r in results if r.total_pii_found > 0)
    
    total_critical = sum(len(r.critical_pii) for r in results)
    total_high = sum(len(r.high_pii) for r in results)
    total_medium = sum(len(r.medium_pii) for r in results)
    total_low = sum(len(r.low_pii) for r in results)
    
    avg_compliance_score = sum(r.compliance_score for r in results) / total_endpoints
    
    # Find most common PII types
    pii_type_counts = {}
    for result in results:
        all_matches = result.critical_pii + result.high_pii + result.medium_pii + result.low_pii
        for match in all_matches:
            pii_type_counts[match.pii_type.value] = pii_type_counts.get(match.pii_type.value, 0) + 1
    
    most_common_pii = sorted(pii_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "summary": {
            "total_endpoints_analyzed": total_endpoints,
            "endpoints_with_pii": endpoints_with_pii,
            "pii_exposure_rate": round((endpoints_with_pii / total_endpoints) * 100, 1),
            "average_compliance_score": round(avg_compliance_score, 1)
        },
        "pii_breakdown": {
            "critical": total_critical,
            "high": total_high,
            "medium": total_medium,
            "low": total_low,
            "total": total_critical + total_high + total_medium + total_low
        },
        "most_common_pii_types": most_common_pii,
        "risk_assessment": _assess_overall_risk(total_critical, total_high, total_medium, total_low),
        "compliance_recommendations": _generate_compliance_recommendations(
            total_critical, total_high, total_medium, total_low, avg_compliance_score
        )
    }


def _assess_overall_risk(critical: int, high: int, medium: int, low: int) -> str:
    """Assess overall risk level based on PII findings."""
    if critical > 0:
        return "CRITICAL - Immediate action required"
    elif high > 5:
        return "HIGH - Significant privacy risks detected"
    elif high > 0 or medium > 10:
        return "MEDIUM - Moderate privacy concerns"
    elif medium > 0 or low > 0:
        return "LOW - Minor privacy considerations"
    else:
        return "MINIMAL - No significant PII detected"


def _generate_compliance_recommendations(
    critical: int, high: int, medium: int, low: int, avg_score: float
) -> List[str]:
    """Generate compliance recommendations based on findings."""
    recommendations = []
    
    if critical > 0:
        recommendations.extend([
            "🔴 URGENT: Address all critical PII exposures immediately",
            "Implement comprehensive data protection impact assessment (DPIA)",
            "Review and update privacy policies and consent mechanisms"
        ])
    
    if high > 0:
        recommendations.extend([
            "🟡 Implement enhanced security controls for high-risk PII",
            "Consider data pseudonymization or anonymization techniques",
            "Establish data breach response procedures"
        ])
    
    if avg_score < 70:
        recommendations.append("📊 Overall compliance score is below acceptable threshold")
    
    recommendations.extend([
        "📋 Conduct regular PII audits and assessments",
        "🔒 Implement privacy by design principles",
        "📚 Provide privacy training for development teams",
        "⚖️ Ensure compliance with applicable privacy regulations"
    ])
    
    return recommendations
