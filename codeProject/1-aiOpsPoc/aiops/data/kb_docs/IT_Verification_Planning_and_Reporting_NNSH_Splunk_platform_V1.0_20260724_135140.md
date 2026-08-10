|  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
# IT Verification Planning and Reporting
|  | | | | | | |
| **This document is signed electronically using QualityDocs.**  **Signatures appear on a separate signature page.** | | | | | | |
|  | | | | | | |
|  | | **IT verification plan:** | | | | |
| Prepared by: | | | Li Peng | LPNL |  |  |
|  | | | Name | Init | Date | Signature |
| Approved by: | | | Li Wei | WZZL |  |  |
|  | | | Name | Init | Date | Signature |

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
|  | **IT verification report (production):** | | | | |
| Prepared by: | | Wu Wende | QWWU |  |  |
|  | | Name | Init | Date | Signature |
| Approved by: | | Li Wei | WZZL |  |  |
|  | | Name | Init | Date | Signature |

## Table of contents

[1. Purpose 3](#_Toc181274809)

[2. Scope 3](#_Toc181274810)

[3. Roles and responsibilities 3](#_Toc181274811)

[4. Verification approach 4](#_Toc181274812)

[4.1 Prerequisites 4](#_Toc181274813)

[4.2 Approach and result 4](#_Toc181274814)

[4.3 Overall acceptance criteria 10](#_Toc181274815)

[4.4 Document management 10](#_Toc181274816)

[5. Verification report production environment 10](#_Toc181274817)

[6. Terms and abbreviations 10](#_Toc181274818)

[7. List of appendices 12](#_Toc181274819)

[8. Enclosures 12](#_Toc181274820)

[9. References 12](#_Toc181274821)

[10. Change log 12](#_Toc181274822)

[11. Appendix 1: [NNSH Splunk platform] URS-UAT Matrix 13](#_Toc181274823)

Purpose

The purpose of this document is to plan and report verification activities applicable to:

|  |  |
| --- | --- |
| **IT system/service and version** | NNSH Splunk Platform (Log Collection China)  Version <1.0> |
| **Change record in ServiceNow and title** | CHG0148573 |

This document is Acceptance verification plan and report on the production environment.

The verification activities outlined in this document will be executed and reported on according to the following NN QMS instructions:

* Manage IT Systems [1]
* Manage IT Security [2]
* Manage IT Infrastructure [3]
* Ownership of IT systems [4]

Scope

This document is to verify all functional and non-functional requirements in the URS, ensuring that these requirements are met.

The validation will include the platform's components and functionalities as follows:

- Splunk Enterprise servers (indexers, search head, heavy forwarder)

- Log interfaces (Infrastructure logs, application logs, etc.)

- Alert, reports and dashboards

- Maintenance and operation

- Security configurations

Roles and responsibilities

Approval of deliverables must be done according to ‘Manage IT Systems’ [1] and as described in this document.

The following roles and responsibilities are required to perform the verification within the scope of this plan.

| **Organisation** | **Role** | **Initials/Name** | **Responsible for** |
| --- | --- | --- | --- |
| NNSH  IT Support China | System Manager | WZZL | * Approval of the plan including the test cases * Approval of the report or verification |
| NNIT CN | Verification SME | JIYT | * Managing verification activities in accordance with the URS, FDS, and the NN QMS |
| NNIT CN | Test Designer | LPNL | * Creates / Designs test cases |
| NNIT CN | Tester | QWWU | * Executes test cases |
| NNIT CN | Test Reviewer | FANY | * Review the test cases * Review the test results |

Table 3: Roles and responsibilities

Verification approach

The verification approach is decided based on the following aspects as listed in Table 5.

| **Basis for planning verification** | **Conclusion** | **Description /Rationale /[ref]** |
| --- | --- | --- |
| **System impact** | Non-GxP | There are no GxP processes and GxP data within the system. |
| **Complexity** | Medium | The system is primarily composed of Splunk software, along with numerous specific configurations and several customized interfaces. |
| **Size** | Limited | The number of servers, log storage capacity, and the logs imported into the platform are all limited. |
| **Risk level** | Low | The verification approach will not impact the normal operation of the platform. |

Table 5: Aspects relevant for verification approach

* 1. Prerequisites

The following prerequisites must be fulfilled prior to verification start:

| **Prerequisites** | **Description** |
| --- | --- |
| **Installation status** | The platform installation is complete. |
| **Verification environment** | The required components and interfaces have all been configured. |
| **IT Operations Support** | The monitoring system has been added and the information in the configuration management system has been completed. |

Table 6: Verification prerequisites

## Approach and result

The verification approach including tests, methods and techniques are outlined in <Table 7, Table 8>.

Traceability between the USR requirements and the test cases are established in <Table 7, Table 8 >.

Table 7: Acceptance verification scope including verification results for functional requirements

| **Verification type: Acceptance** | | **Location: <location of test cases>** | **Location: <location of URS>** | **Verification results**  **Executed: <29-10-2024 to 30-10-2024>** |
| --- | --- | --- | --- | --- |
| **Change ID** | Test techniques (description and rationale) | Test cases | Trace to URS | Execution status |
| CHG0148573 | Search logs using different index names. | TC-LC-001 Splunk Forwarder Collection Log for servers | URS-LC-001 | Passed |
| Search logs using different index names. | TC-LC-002  Event Hub Collection Log for Azure CN cloud | URS-LC-002 | Passed |
| Search logs using different index names. | TC-LC-003  Syslog Collection Log firewall and bastion | URS-LC-003 | Passed |
| Search logs using different index names. | TC-LC-004  File Collection Log for Anti-DDoS | URS-LC-004 | Passed |
| Search logs using different index names. | TC-LC-005  DB Connection Collection Log for application logs | URS-LC-005 | Passed |
| Search logs using different index names. | TC-LC-006  File Collection Log for application logs | URS-LC-006 | Passed |
| Search logs using different index names. | TC-LC-007  API Collection Log for application logs | URS-LC-007 | Passed |
| Search logs using different index names. | TC-LC-008  Event Hub Collection Log for application logs | URS-LC-008 | Passed |
| Check the default Log Storage period | TC-LDS-001  Default Log Storage period test | URS-LDS-001 | Passed |
| Check the customized Log Storage period | TC-LDS-002  Customized Log Storage period test | URS-LDS-002 | Passed |
| Customized log field extraction rules in search window | TC-LA-001  Custom log field extraction test | URS-LA-001 | Passed |
| Rename the names of log fields through commands in search window | TC-LA-002  Test of rename the names of log fields | URS-LA-002 | Passed |
| Calculate fields based on usage requirements in search window | TC-LA-003  Log fields calculate test | URS-LA-003 | Passed |
| Use fuzzy keyword in search window and check the search result | TC-LS-001  Fuzzy keyword search test | URS-LS-001 | Passed |
| Check the log present format in search window | TC-LS-002  Log structured format test | URS-LS-002 | Passed |
| Export the search result to files in csv, json or XML format | TC-LS-003  Log export test | URS-LS-003 | Passed |
| Design alert rules for operations such as adding and deleting users, and then check if the alert can be triggered | TC-CA-001  Customized alert rule test | URS-CA-001 | Passed |
| Set up alert and set the mail sending as action of trigger, then check if the mail is received in targeted mailbox | TC-CA-002  Alert mail sending test | URS-CA-002 | Passed |
| Set up an daily alert to monitor the license usage | TC-CA-003  License usage alert test | URS-CA-003 | Passed |
| Set up an alert rule based on application logs and send alert emails to specific email addresses, then check if the mail is received in targeted mailbox | TC-CA-004  Test of customized alert rules based on application requirements | URS-CA-004 | Passed |
| Set up a report using the extracted logs and send report to a specific mailbox, then check if the mail is received in targeted mailbox | TC-CR-001  Regular report test | URS-CR-001 | Passed |
| Set up a report with pre-process and analyse the log data | TC-CR-002  Test of pre-process logs for a customized report | URS-CR-002 | Passed |
| Set up a customise reports based on the application requirement | TC-CR-003  Test of customised report for application requirement | URS-CR-003 | Passed |
| Set up a comprehensive database audit dashboard based on detailed database log analysis | TC-CD-001 | URS-CD-001 | Passed |
| Set up an OS layer user action audit dashboard | TC-CD-002 | URS-CD-002 | Passed |
| Set up a scheduled task to send dashboard on demand | TC-CD-003 | URS-CD-003 | Passed |
| Set up a customized dashboard based on the analysis of the application logs | TC-CD-004 | URS-CD-004 | Passed |

Table 8: Acceptance verification scope including verification results for non-functional requirements

| **Verification type: Acceptance** | | **Location: <location of test cases>** | **Location: <location of URS>** | **Verification results**  **Executed: <29-10-2024 to 30-10-2024>** |
| --- | --- | --- | --- | --- |
| **Change ID** | Test techniques (description and rationale) | Test cases | Trace to URS | Execution status |
| CHG0148573 | Calculate log data capacity in searching window, to check if log data capacity can be up to 50GB per day | TC-PR-001  Perforce test of log data receiving and index | URS-PR-001 | Passed |
| Open the platform URL and start timing simultaneously to calculate the duration from initiating the request to the page being fully loaded. | TC-PR-002  Page load speed test | URS-PR-002 | Passed |
| Initiate an API request and start timing to calculate the response time of the API request. | TC-PR-003  API response time test | URS-PR-003 | Passed |
| Check the monitoring system setting | TC-AR-001  Test the reliability of log importing interface | URS-AR-001 | Passed |
| Check the monitoring system setting | TC-AR-002  Test the reliability of management interface | URS-AR-002 | Passed |
| Refer to IT Recovery Plan\_NNSH Splunk Platform | TC-AR-003  RPO and RTO test | URS-AR-003 | Passed |
| Open the SNOW and search if any incident related with NNSH Splunk platform | TC-OR-001  Incident management test | URS-OR-001 | Passed |
| Open the SNOW and search if any change related with NNSH Splunk platform | TC-OR-002  Change management test | URS-OR-002 | Passed |
| Check the monitoring system to find the monitoring items for NNSH Splunk platform  Test the on-duty phone | TC-OR-003  Operating time test | URS-OR-003 | Passed |
| Log on the test environment and check the search functions and installed plugins | TC-OR-004  Non-prod environment test | URS-OR-004 | Passed |
| Search the \_Internal logs of NNSH Splunk platform, check the log catalogue and time period | TC-SR-001  Test of NNSH Splunk platform internal logs | URS-SR-001 | Passed |
| Grant the “delete” privilege to an admin user, search specific logs and use the “delete” command in search window | TC-SR-002  Test of log deleting function | URS-SR-002 | Passed |
| Grant the “delete” privilege to an admin user, search specific logs and use the “download” function in search window | TC-SR-003  Test of log export function | URS-SR-003 | Passed |
| Exclude specific logs with the “NOT” command in search window | TC-SR-004  Test of log excluding function | URS-SR-004 | Passed |
| Check the interface setting of NNSH Splunk platform | TC-SR-005  Testing the encryption of logs during transmission | URS-SR-005 | Passed |
| Check the VM disk encryption settings of the NNSH Splunk platform | TC-SR-006  Test of the encryption of logs during storage | URS-SR-006 | Passed |
| Check all users account configurations in the user management interface | TC-SR-007  Test of the account management | URS-SR-007 | Passed |
| Check all privileged account configurations in the role management interface | TC-SR-008  Test of the privilege management | URS-SR-008 | Passed |
| View the rule setting of accounts, and check if the different role is set for different accounts. | TC-SR-009  Test of the SoD settings | URS-SR-009 | Passed |
| Open the password configuration interface and check if the password policy meets security requirements | TC-SR-010  Test of the password policy | URS-SR-010 | Passed |
| Log on the bastion host and open the “Splunk management” application in bastion host | TC-SR-011  Test the log on via bastion host | URS-SR-011 | Passed |
| View the PA firewall and NSG configurations and check the access control setting for the NNSH Splunk platform | TC-SR-012  Test of the PA firewall and NSG settings | URS-SR-012 | Passed |
| Open the time out configuration interface and check if the time out of not active is set as 15 minutes. | TC-SR-013  Test of time out setting | URS-SR-013 | Passed |
| Search the interface logs in search windows and view the log time range | TC-SR-014  Test of records of log transferring | URS-SR-014 | Passed |
| Log on the each server of the NNSH Splunk platform, and check the different log function settings | TC-MR-001  Test of server rule configuration | URS-MR-001 | Passed |
| Check and server capacity configurations | TC-MR-002  Test of the server capacity | URS-MR-002 | Passed |

## Overall acceptance criteria

Overall acceptance criteria applicable to verification are described below

* all test cases in section 5.2 have been executed
* the results have been evaluated against the listed acceptance criteria
* all validation deviations/defects have been resolved and approved.
## Document management

Approval of this document is performed by electronic signature of the document versions in QualityDocs according to the document lifecycle described in section 2.

Approval of the test cases and the corresponding runs listed in Table 7, Table 8 is performed in UAT Test Case\_ NNSH Splunk Platform

| **Document type** | **Documented in** |
| --- | --- |
| Verification plan and report | IT Verification Planning and Reporting\_NNSH Splunk platform |
| Test cases and corresponding test results | UAT Test Case\_NNSH Splunk Platform |
| Change request | CHG0148573 |

Table 9: Archiving details

Verification report production environment

Table 10 below reports on changes from final approved version of this IT verification plan, report and conclusion.

| **Verification plan section** | **Change** |
| --- | --- |
| Section ‎5.2 | Table <7> Table <8> are updated with verification results |
| Conclusion | It is hereby concluded that the verification activities in the production environment have been executed and documented as planned in the verification plan.  All user requirements have been meet according to testing results.  The overall acceptance criteria described in section ‎5.3 have been met.  The Splunk platform set up in CHG0148573 is verified, fit for intended use and ready for use. |

Table 14: Changes from verification plan and conclusion

Terms and abbreviations

| **Abbreviation/term** | **Definition/description** |
| --- | --- |
| CR | Change request (in novoGloW) |
| NN | Novo Nordisk |
| PROD | Production (environment) |
| QA | Quality assurance (responsible) |
| QMS | Quality management system |
| QualityDocs | NN Document management system |
| SME | Subject matter expert |
| SOP | Standard operating procedure |
| TEST | Test (environment) |
| TRM | Traceability matrix |
| URS | User requirement specification |

List of appendices

| **No.** | **Name** | **No. of pages** |
| --- | --- | --- |
| 1 | Appendix 1: Appendix 1: [NNSH Splunk platform] URS-UAT Matrix | 13 |

Enclosures

|  |  |
| --- | --- |
| [1] | Encl.1 UAT Test Case\_NNSH Splunk Platform |
| [2] | Encl.2 UAT Test Case Screenshot\_NNSH Splunk platform |

References

|  |  |
| --- | --- |
| [1] | *187219 Manage IT Systems.* |
| [2] | *187655 Manage IT Security.* |
| [3] | *216301 Manage IT Infrastructure.* |
| [4] | *187218 Ownership of IT Systems.* |
| [5] | *F-01069157 ITQ\_AI1\_User Requirements Specification (URS)\_Use Case and Row based\_NNSH Splunk Platform* |
| [6] | *F-01069158 IT Functional-Design Specification \_NNSH Splunk Platform* |

Change log

| **Version no** | **Date** | **Change description** |
| --- | --- | --- |
| 1.0 | 2024.10.30 | New document |

Appendix 1: [NNSH Splunk platform] URS-UAT Matrix

|  |  |  |  |
| --- | --- | --- | --- |
| **URS No.** | **URS Description** | **Testing Cases** | **Test Results** |
| URS-LC-001 | The NNSH Splunk platform needs to support the collection of logs related to Windows and Linux systems. | TC-LC-001 | OK |
| URS-LC-002 | The NNSH Splunk platform needs to support the collection of logs related to the China Azure Cloud Platform. | TC-LC-002 | OK |
| URS-LC-003 | The NNSH Splunk platform needs to support the collection of PA FW and Bastion Host logs. | TC-LC-003 | OK |
| URS-LC-004 | The NNSH Splunk platform needs to support the collection of logs from Anti-DDoS system. | TC-LC-004 | OK |
| URS-LC-005 | The NNSH Splunk platform needs to support the collection of application logs through the database interface. | TC-LC-005 | OK |
| URS-LC-006 | The NNSH Splunk platform needs to support the collection of logs from files exported by third-party applications in an intranet environment per hour. | TC-LC-006 | OK |
| URS-LC-007 | The NNSH Splunk platform needs to collect application logs through HTTP APIs. | TC-LC-007 | OK |
| URS-LC-008 | The NNSH Splunk platform needs to support the collection of application logs in Azure Event Hub. | TC-LC-008 | OK |
| URS-LDS-001 | The NNSH Splunk platform needs to support 6 months of log storage | TC-LDS-001 | OK |
| URS-LDS-002 | The NNSH Splunk platform needs to adjust log storage time based on application requirements | TC-LDS-002 | OK |
| URS-LA-001 | The NNSH Splunk platform needs to support extract valuable fields from logs and store them as required | TC-LA-001 | OK |
| URS-LA-002 | The NNSH Splunk platform needs to support rename fields based on usage requirements | TC-LA-002 | OK |
| URS-LA-003 | Splunk platform needs to support fuzzy keyword searches.  Splunk platform needs to support the constructed presentation of logs. | TC-LA-003 | OK |
| URS-LS-001 | Splunk platform needs to support fuzzy keyword searches. | TC-LS-001 | OK |
| URS-LS-002 | Splunk platform needs to support the constructed presentation of logs. | TC-LS-002 | OK |
| URS-LS-003 | Splunk platform needs to support the export of search results | TC-LS-003 | OK |
| URS-CA-001 | The NNSH Splunk platform needs to monitor operations such as adding and removing users at the OS layer | TC-CA-001 | OK |
| URS-CA-002 | The NNSH Splunk platform needs to support email alerts | TC-CA-002 | OK |
| URS-CA-003 | The NNSH Splunk platform needs to monitor its own platform license with alerts | TC-CA-003 | OK |
| URS-CA-004 | The NNSH Splunk platform needs to support customized alerts based on the customer’s requirements. | TC-CA-004 | OK |
| URS-CR-001 | The NNSH Splunk platform needs to support the ability to send reports on a regular basis | TC-CR-001 | OK |
| URS-CR-002 | The NNSH Splunk platform needs to support pre-processing of data | TC-CR-002 | OK |
| URS-CR-003 | The NNSH Splunk platform needs to support customized report according to customer’s requirements | TC-CR-003 | OK |
| URS-CD-001 | The NNSH Splunk platform needs to support producing a database audit dashboard | TC-CD-001 | OK |
| URS-CD-002 | The NNSH Splunk platform needs to support producing an OS layer user audit dashboard | TC-CD-002 | OK |
| URS-CD-003 | The NNSH Splunk platform needs to support sending dashboards at regular intervals. | TC-CD-003 | OK |
| URS-CD-004 | The NNSH Splunk platform needs to support customized dashboards according to customer’s requirements. | TC-CD-004 | OK |
| URS-PR-001 | The NNSH Splunk platform can receive and store logs of 50 GB per day | TC-PR-001 | OK |
| URS-PR-002 | The homepage of the NNSH Splunk platform respond user web request in 3 seconds. | TC-PR-002 | OK |
| URS-PR-003 | The average response time of the HTTP API interface must be less than 1 second. | TC-PR-003 | OK |
| URS-AR-001 | The reliability of the each NNSH Splunk platform's interface must reach 99%. | TC-AR-001 | OK |
| URS-AR-002 | The operational reliability of the platform must reach 99.5%. | TC-AR-002 | OK |
| URS-AR-003 | Recovery Time Objective (RTO)=1 day and Recovery Point Objective (RPO)=1 day | TC-AR-003 | OK |
| URS-OR-001 | All operational requirements and platform-related incidents will be recorded and tracked using SNOW. | TC-OR-001 | OK |
| URS-OR-002 | The CMP needs to be set up, and CR management will follow the CIOA agreement. | TC-OR-002 | OK |
| URS-OR-003 | The NNSH Splunk platform needs to be available on 24 hours a day, 7 days a week. Incident and event related with the NNSH Splunk platform will be handled on 24 hours a day, 7 days a week. The customer request will be handled on China Business Days, Monday through Friday 09:00 to 18:00 GMT+8. | TC-OR-003 | OK |
| URS-OR-004 | The system needs to establish a testing environment. The resources for the testing environment should be configured according to the minimum requirements. | TC-OR-004 | OK |
| URS-SR-001 | The audit trail is set up as default. Splunk system can generates audit trails, includes: 1. Creation, change, and cancellation of access authorization 2. Login success/failure, date/time of event and account 3. Who performed the log operation action 4. What was created/modified/deleted related with system management Audit trail records is preserved for 180 days. | TC-SR-001 | OK |
| URS-SR-002 | Admin users can delete logs which contain specific keyword and these activities will be logged.  Only admin user which was granted with "delete" privilege can delete the logs. No data change can be performed. | TC-SR-002 | OK |
| URS-SR-003 | Logs can be exported by a specific ‘individual’ request, and these activities will be logged. | TC-SR-003 | OK |
| URS-SR-004 | Logs which include specific keyword can be temporarily excluded by a specific ‘individual’ request, and these activities will be logged. | TC-SR-004 | OK |
| URS-SR-005 | All log data must be transited in encryption by default. | TC-SR-005 | OK |
| URS-SR-006 | All log data must be stored in encryption by default. | TC-SR-006 | OK |
| URS-SR-007 | User account can be traced to individuals and no shared account is used. All accounts will be individual, and activities will be logged. | TC-SR-007 | OK |
| URS-SR-008 | The NNSH Splunk platform can define user roles based on the supported business process which following the principle of least privilege. | TC-SR-008 | OK |
| URS-SR-009 | The NNSH Splunk platform can Follow the principle of separation of duties, ensuring that responsibilities are separated between different users. | TC-SR-009 | OK |
| URS-SR-010 | The password policy can be set as: i. minimum password length: 14 ii. frequency or triggers for changing passwords:120 days  iii. User will be log off after inactive for 15 minutes.  iv. limits on invalid logon attempts:5 times v. locking of account after invalid logon attempts: 15 mins vi. reset newly issued passwords at first use. vii. token based authentication for application programming interfaces | TC-SR-010 | OK |
| URS-SR-011 | The management interface of the NNSH Splunk platform can only be accessed through the NNSH bastion host. | TC-SR-011 | OK |
| URS-SR-012 | The network of the NNSH Splunk platform is isolated network and controlled by PA firewall and NSG. | TC-SR-012 | OK |
| URS-SR-013 | The user logon session can be set as time out if not active for 15 minutes. | TC-SR-013 | OK |
| URS-SR-014 | All application log transfer activities that pass through the application log transfer interface must be recorded, including the time, source, and transfer result. The interface logs must be stored in a specific log repository and retained for 180 days. | TC-SR-014 | OK |
| URS-MR-001 | Breaking down the system into smaller, independent components that are easier to maintain. | TC-MR-001 | OK |
| URS-MR-002 | It is easy to improve the system processing capacity according to the log receiving capacity requirements. | TC-MR-002 | OK |