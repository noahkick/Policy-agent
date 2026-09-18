# Security and Device Policy

**Policy ID:** DEMO-SECURITY-DEVICE  
**Version:** 1.0  
**Effective date:** 2026-01-20  
**Scope:** Fictional Acme Demo authentication and device controls for customer-data access.

## Purpose and Definitions

This fictional policy defines minimum technical controls for accessing customer data. A **corporate laptop** is managed, encrypted, patched, and enrolled in endpoint monitoring. A **personal laptop** is unmanaged. **MFA** is the approved multi-factor authentication service. **Emergency access** is access connected to a documented security incident and approved by the on-call security lead.

## Device Rule

Access to customer data from a personal laptop is denied. The access action is denied for customer data when the device is a personal laptop. This prohibition applies to employees, contractors, and vendors, regardless of role, location, or business purpose.

Access from a corporate laptop is allowed only when the device is encrypted, patched, monitored, and MFA is active. The access action is allowed for customer data when the device is a corporate laptop and MFA is active. This rule describes the required controls; it does not grant a role permission that another policy has not granted.

## Emergency Exception

The personal-laptop prohibition may be temporarily bypassed only for a documented security emergency, when the on-call security lead has approved emergency access and MFA is active. The exception applies to an incident responder handling the named incident, requires an emergency ticket, and expires after the incident is closed. For a normal business request, the emergency exception does not apply.

## Authentication Restrictions

Access without MFA is denied for customer data. A user may not satisfy MFA by sharing another person's session or credentials. The security team must record failed access attempts and review emergency access within one business day.

## Scope Boundary

This policy does not specify which job duties require customer data access, how long customer data is retained, or which external vendors are approved. Those questions must be evaluated using the other fictional policies and the facts supplied by the requester. If encryption, patch status, monitoring, or emergency facts are missing, the technical-control answer may be UNKNOWN.