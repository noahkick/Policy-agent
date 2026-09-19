# Data Retention Policy

**Policy ID:** DEMO-DATA-RETENTION  
**Version:** 1.0  
**Effective date:** 2026-02-01  
**Scope:** region=ALL; department=ALL; vendor=ALL

## Purpose and Definitions

This fictional policy establishes retention periods for selected customer-data records. **Customer data** means account, transaction, and support records. **Standard retention period** means 365 days after the record's last business use. **Support case data** means the messages and attachments associated with a customer support case. Retention is measured from the last business use unless a section states another event.

## Standard Rule

Customer data may be retained for the standard retention period of 365 days after last business use. The retain action is allowed for customer data when the requested retention period is 365 days. At the end of that period, the owning team must delete the data or irreversibly anonymize it unless an exception in this policy applies.

## Support Exception

Support case data may be retained for 180 days after the case is closed. The retain action is allowed for support case data when the requested retention period is 180 days. A legal hold or an unresolved fraud investigation suspends deletion for the affected records, but the hold owner must document the reason and review it every 90 days.

## Regional Privacy Requirement

Customer data processed for a resident of the **EU** may be retained for no more than 30 days after last business use. This regional rule applies to all roles and departments when the location is EU and the resource is customer data. The EU rule is an exception to the 365-day standard and does not extend the period for support case data unless a separate lawful hold is documented.

## Unknown Cases

This policy does not state a retention period for raw security telemetry, marketing prospects, employee records, or datasets that are not customer data or support case data. It also does not determine whether a particular legal hold exists. The policy agent must return UNKNOWN when the requested resource, region, or applicable exception is not supplied or not covered here.

## Ownership

Data owners are responsible for scheduled deletion and for recording any approved hold. No team may extend a stated period merely because storage is convenient.