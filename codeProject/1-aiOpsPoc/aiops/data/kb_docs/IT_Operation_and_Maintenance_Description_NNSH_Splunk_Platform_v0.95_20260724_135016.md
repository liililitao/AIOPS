|  |  |  |
| --- | --- | --- |
| **IT Operation and Maintenance Description**  **NNSH Splunk Platform (Log Collection China)** | | |
|  | | |
| **This document is signed electronically using QualityDocs.**  **Signatures appear on a separate signature page.** | | |
|  | | |
| **Prepared by:** |  |  |
| **Dean Wende Wu WEWU**  Security Consultant  NNIT | Date  \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ | Signature  **\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_** |
|  |  |  |
| **Approved by:** |  |  |
| **Li Wei, David**  **WZZL**  Sr. Digital Product Manager  190101 Frontline Support & Insights | Date  \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ | Signature  **\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_** |

Table of Contents

[1. Purpose 2](#_Toc180130652)

[2. Roles and responsibilities 2](#_Toc180130653)

[3. System information and documentation 3](#_Toc180130654)

[3.1. System description 3](#_Toc180130655)

[3.2. System architectural overview 3](#_Toc180130656)

[3.3. System resources 4](#_Toc180130657)

[3.4. Data source 6](#_Toc180130658)

[3.5. System Firewall Specifications 6](#_Toc180130659)

[4. User management activities 7](#_Toc180130660)

[4.1. User administration 7](#_Toc180130661)

[4.2. User support (technical and functional support) 8](#_Toc180130662)

[5. IT risk management 8](#_Toc180130663)

[6. IT process activities 8](#_Toc180130664)

[6.1. IT suppliers – external 8](#_Toc180130665)

[6.2. IT changes 8](#_Toc180130666)

[6.2.1. Normal IT changes 8](#_Toc180130667)

[6.2.2. Emergency IT changes 9](#_Toc180130668)

[6.3. System monitoring 10](#_Toc180130669)

[6.4. IT incidents and IT problems 10](#_Toc180130670)

[6.5. Backup and recovery 10](#_Toc180130671)

[6.6. Information security 11](#_Toc180130672)

[6.7. Person data security 11](#_Toc180130673)

[7. References 11](#_Toc180130674)

[8. Change log 11](#_Toc180130675)

# Purpose

This document describes the operation and maintenance of the NNSH Splunk platform, including details of any system-specific processes and various activities for NNSH Splunk users.

# Roles and responsibilities

| **Role** | **Team/Department** | **Responsibilities** |
| --- | --- | --- |
| NNSH Splunk platform operator | NNIT CN Security team | * - System Technical Support * - System Release * - System Deployment * - System changes on demand * - Access to logs on demand * - Alerts and reports are customized according to requirements * - User management and user rights management * - Provide O&M support in case of incidents |
| NNSH Splunk Platform owner | NNSH GITO | * Approve the account request if no question |

# System information and documentation

## System description

NNSH Splunk platform is a log analytics platform that collects various types of logs and uses them to meet a variety of customised analytics requirements.

## System architectural overview

![](data:image/png;base64...)

## System resources

|  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| **Item** | **Server 1** | **Server 2** | **Server 3** | **Server 4** | **Server 5** | **Server 6** |
| **Server Name** | vm-cdcshared-prd-spl9head | vm-cdcshared-prd-spl9forwarder | vm-cdcshared-prd-spl9index1 | vm-cdcshared-prd-spl9index2 | vm-cdcshared-tst-splunk9 | APPCNBJ173 |
| **IP Address** | 10.31.19.232 | 10.31.19.233 | 10.31.19.234 | 10.31.19.235 | 10.31.19.239 | 10.38.28.48 |
| **Infrastructure Zone** | Azure | Azure | Azure | Azure | Azure | DMZ |
| **Primary Function** | Central Management Server | Forwarder | Storage | Storage | Test | File log hub server |
| **Software Name/Version** | Splunk Enterprise 9.2.2 | Splunk Enterprise 9.2.2 | Splunk Enterprise 9.2.2 | Splunk Enterprise 9.2.2 | Splunk Enterprise 9.2.2 | N/A |
| **Environment** | Virtual | Virtual | Virtual | Virtual | Virtual | Virtual |
| **CPU** | 16 Cores | 16 Cores | 16 Cores | 16 Cores | 4 Cores | 2 Cores |
| **Memory** | 32G | 32G | 32G | 32G | 16G | 16G |
| **Hard Disk** | 1T | 1T | 1T | 1T | 500G | 300G |
| **OS** | Rhel9.4 | Rhel9.4 | Rhel9.4 | Rhel9.4 | Rhel9.4 | Windows server 2019 Standard |
| **Role** | Head | Heavy Forwarder | Index | Index | Test | File log collection and sending |

## Data source

The data source of NNSH Splunk platform can be found in the below table:

|  |  |  |  |
| --- | --- | --- | --- |
| **Log catalog** | **Sources** | **Data input** | **Index** |
| Infrastructure | Windows | Splunk Forwarder | main |
| Linux | Splunk Forwarder | main |
| Azure | Azure Event hub | Azure |
| Security | Bastion host | Syslog TCP: 10514 | bastion |
| DDoS | Exported file from Anti-DDoS | ddos |
| Palo Alto | Syslog TCP: 10515 | panfw |
| Application | Applications | As required | Independent Index |

## System Firewall Specifications

|  |  |  |  |
| --- | --- | --- | --- |
| **Firewall** | **Originating Server** | **Destination Server** | **Port** |
| **Network Security Group** | All NNSH Splunk platform Servers | All NNSH Splunk platform Servers | TCP:8089 |
| **Network Security Group** | All NNSH Splunk platform Servers | All NNSH Splunk platform Servers | TCP: 8000 |
| **Network Security Group** | Management Clients | All NNSH Splunk platform Servers | TCP: 8000 |
| **Network Security Group** | NNSH Splunk platform Heavy Forwarders | NNSH Splunk platform Index Servers | TCP: 9997 |
| **Network Security Group** | NNSH Splunk platform Universal Forwarder | NNSH Splunk platform Heavy Forwarders | TCP: 9997 |
| **Network Security Group** | NNSH Bastion host | NNSH Splunk platform Heavy Forwarders | SYSLOG TCP:10514 |
| **Network Security Group** | PA FW | NNSH Splunk platform Heavy Forwarders | SYSLOG TCP:10515 |
| **Network Security Group** | NNSH Splunk platform Heavy Forwarders | MySQL servers(As application required) | MySQL TCP: 3306 |
| **NNSH Internet FW** | vm-cdcshared-prd-spl9forwarder | APPCNBJ173  143.64.232.101 | SFTP TCP: 22 |

# User management activities

## User administration

Access to the NNSH Splunk platform is controlled via Novo Access, and the user accesses are managed in alignment with ‘Manage users of IT systems’ [6]. A list of user roles and associated access rights as well as the defined approval procedure is available in Novo Access. The maintenance of user accounts as well as machine and service accounts are handled by NNIT China operation team.

Passwords for privileged accounts and service account on the NNSH Splunk platform are kept in NN PIM.

An inactive user report in the NNSH Splunk platform will be set up and run on the first day of each quarter. User accounts that have not logged in for the past three months will be identified, and these inactive accounts will then be disabled.

A user review is performed on a yearly basis and is documented in the User Review Report (URR). The user reviews are handled by NNIT China Security team.

Privileged accesses are reviewed by NNIT China Security team. yearly. Privileged accesses that have been revoked/rejected during the user review are investigated. In case any unauthorised privileged accesses are identified, an IT incident is raised to investigate any potential risk and impact for the improper actions that the revoked users may have performed.

Admin Permission Request Process:

* User apply the administrator account of NNSH Splunk platform in Novo Access.
* After the request is approved by Line manager and the NNSH Splunk platform owner, the NNSH Splunk platform administrator will receive a notifying of account adding.
* NNSH Splunk platform administrator will add an admin account according the notifying of Novo Access, and send the initial password to the Line manager.
* When user logs in the NNSH Splunk platform for the first time, they must change the initial password. The new password must meet the security requirements.

An alert will be set on the NNSH Splunk platform to monitor the abnormal logons and lockout event per 15 minutes, and automatic email alert is configured to send email to security operations team , who will review the alerts and determine if further investigation and analysis are needed.

Configure a report on the NNSH Splunk platform to collect all user login logs from the previous month on the 1st of each month and send it to the administrator's email.

## User support (technical and functional support)

The NNSH Splunk platform was officially supported by Splunk company, reference link: https://splunk.my.site.com/customer/s

# IT risk management

Risk assessments for the NNSH Splunk Platform has been performed and documented in IT risk assessment:

* + An IT risk assessment has been completed and documented in ServiceNow Integrated Risk Management (IRM). ServiceNow ID:15502
  + As part of the IT risk management, this risk assessment is reviewed every 3 years considering emerging knowledge and experience to ensure that the implemented controls of the IT system are effective and relevant.

# IT process activities

## IT suppliers – external

Splunk supporting will provide online troubleshooting and after-sales service support.

NNIT China Security team will provide operation and maintenance services.

## IT changes

ServiceNow ITSM is used for managing IT changes which is handled according to [Q187219] and [Change Control – Q220205]. NN System Manager raise an IT change request or service request to IT system management by ServiceNow.

A list of requests for change is available on the ServiceNow. ‘Normal’ IT changes are prioritized by supplier and approved by NN System Owner and NN System Manager. ‘Emergency’ IT changes are approved by NN System Owner, and NN System Manager create ServiceNow Change Ticket.

The platform and server implementation must be controlled by Change, and all new servers need to be configured according to MSR requirements.

### Normal IT changes

The below changes are considered normal IT changes to the IT system. The normal process for authorisation and implementation will be followed.

|  |  |
| --- | --- |
| **Normal IT change** | **Process** |
| Normal Change  *(i.e. new or change to existing functionality)* | 1. Submission of a change request to the System owner/delegate and logs the change in ServiceNow. 2. NNIT CN Security Team analyses of the change request to determine its impact, risks, and feasibility. 3. Review and approve the change request by the system manager. 4. Deliver the change request to system owner and review and approve the change request by system owner. 5. NNIT CN Security Team plans and schedules the change, including testing, implementation, and back-out plans. 6. Implementation of the change during an approved maintenance window. 7. NNIT CN Security Team tests and verifies of the change to ensure that it meets the desired outcomes and does not adversely affect the environment. 8. Do the UAT of the normal change by the stakeholders. 9. NNIT CN Security Team deploys the standard changes in the production environment. |

### Emergency IT changes

The below changes are considered emergency IT changes to the IT system. Emergency changes are performed when there is a documented need to implement a change without following the normal process for authorisation and implementation of changes. An IT incident is raised to investigate the IT incident and assess the impact.

|  |  |
| --- | --- |
| **Emergency IT change** | **Process** |
| Emergency Change  *(i.e. system failures, security breaches, or other incidents that could have a significant impact on the business)* | 1. NNIT CN Security Team Identifies the emergency situation and the need for an emergency change and logs the change in ServiceNow. 2. NNIT CN Security Team assesses the risks and impacts associated with the change. 3. See approval of the emergency change request from the system owner/delegate and system manager. 4. NNIT CN Security Team develops the change as quickly as possible, while minimizing the risks and impacts. 5. NNIT CN Security Team test the emergency change and ensure all test cases are all passed. 6. Stakeholders do the UAT of the emergency change and ensure all test cases are all passed. 7. NNIT CN Security Team deploys the standard changes in the production environment. 8. Follow-up actions to review and monitor the effectiveness of the emergency change and identify any further actions required by the NNIT CN Security Team. |

## System monitoring

The NNSH Splunk platform is monitored by the NNSH Monitoring platform.

## IT incidents and IT problems

Incident management is handled in accordance with the ‘IT Incident Management for IT Systems - Guidelines’ IT incidents and IT problems are handled through ServiceNow ITSM.

IT security incidents follow NN's internal security incident management process. If an IT security incident occurs, it is handled by the security management team and escalated to GSO via email.

|  |  |  |
| --- | --- | --- |
| Level of problem | Problem resolution time | Example |
| Critical | Within 4 hours | The system is not available for login (the page is stuck without corresponding) |
| High | Within 8 hours | Part of the system is not available, but does not affect the overall use of the system (slow response to page requests, more than 5 seconds interface return value) |
| Medium | Within 24 hours | There are error or warning messages, but the system functions normally (abnormal request logs). |
| Low | Within 48 hours | Consultation on the use of the system |

Incident and Problem management process should be referenced section 6 and 10 in NNIT Operation Manual for Novo Nordisk Shanghai F-01031866.

## Backup and recovery

The system is backed up and restored by a cloud platform.

Backup and recovery management is handled in alignment with ’Backup and recovery of IT solutions’ [10]. Backup of the IT system and the data in the IT system is done.

1. Daily backups are kept 1 month
2. Weekly backups are kept 3 months
3. Monthly backups are kept 6 months

The agreed service levels for Recovery Time Objective (RTO) and Recovery Point Objective (RTO) are defined in ServiceNow ITOM.

The agreed service levels: RTO: 1 day. RTO: 1 day.

The IT system and the data in the IT system is recovered according to the IT recovery plan <document ID>.

The backup and recovery processes were tested as part of the verification activities when the IT system was established and is tested in case of major changes to the IT system.

## Information security

The required information security controls (risk controls and lifecycle controls) are implemented as defined in the IT risk assessment (see section 5).

Security patches are handled by NNIT China Operation Team according to security patch management section 20.9 in NNIT Operation Manual for Novo Nordisk Shanghai F-01031866.

## Person data security

The logs collecting by NNSH Splunk platform may contain personal data, and Consent management is done via upstream systems. The NNSH Splunk platform doesn’t collect any personal data directly.

The usage of employees personal information collected has been documented in NN Privacy Statement, and all NNSH Splunk platform users have signed it via ISOtrain system.

Non-production environment will import data which was exported from production environment, and the data must be anonymized to ensure no real personal data.

# References

|  |  |
| --- | --- |
| [1] | *Q187219 Manage IT systems including digital solutions.* |
| [2] | *Q187218 Ownership of IT systems and IT infrastructure.* |
| [3] | *Q219354 Manage IT Solutions in ServiceNow.* |
| [4] | *Q190751 Protecting and handling information.* |
| [5] | *Q0700796 Manage personal data in IT solutions.* |
| [6] | *Q0355420 Manage users of IT systems.* |
| [7] | *Q0807260 IT supplier management lifecycle.* |
| [8] | *Q0356054 Manage configuration.* |
| [9] | *Q0715589 Acceptance verification and release of IT systems.* |
| [10] | *Q0808604 Backup and recovery of IT solutions.* |
| [11] | *Q212684 Security Patch Management.* |

# Change log

| **Version no** | **Date** | **Change description** |
| --- | --- | --- |
| 1.0 |  | New document |