# Data Access Policy

**Policy ID:** DEMO-DATA-ACCESS  
**Version:** 1.0  
**Effective date:** 2026-01-15  
**Scope:** region=ALL; department=ALL; vendor=ALL

## Purpose and Definitions

This fictional policy defines when employees may access customer data. In this document, **customer data** means account, transaction, and support records classified as Internal or Confidential. A **corporate laptop** is an Acme-managed device with current endpoint protection. A **personal laptop** is any unmanaged computer. **MFA** means multi-factor authentication through the approved identity service.

## Standard Access Rules

Employees may access customer data when the access is required for their assigned work, the employee is using a corporate laptop, and MFA is active. The access action is allowed for the employee's assigned role when the requested resource is customer data. Access must be limited to the minimum records needed for the task.

Analysts may access customer data from a corporate laptop with MFA for reporting and investigation work. Support agents may access customer data from a corporate laptop with MFA only for an active customer case. These rules do not authorize access to payment-card authentication data, which is outside this policy's stated resource scope.

## Remote Work Exception

Participants in the **approved remote-work pilot** may access customer data from a personal laptop only when the pilot manager has approved the participant and the employee uses the managed browser profile with MFA. For this document, that pilot participant role is an explicit exception to the standard corporate-laptop requirement.

## Emergency Access

During a documented security or safety emergency, the on-call security lead may authorize temporary customer-data access for an incident responder. The access requires an emergency ticket and MFA. Emergency access is limited to the incident and must be reviewed within one business day. This section does not define access to data categories other than customer data.

## Restrictions and Exceptions

Access from a personal laptop is not allowed for employees who are not approved remote-work pilot participants. A support agent may not use the emergency rule for ordinary case work. A role, device, or authentication fact that is not stated in this policy is not inferred by this document; additional information is required before a decision can be made.