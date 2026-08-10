|  |  |  |
| --- | --- | --- |
# IT Interface Terms of NNSH Splunk Platform
|  | | |
| **This document is signed electronically using QualityDocs.**  **Signatures appear on a separate signature page.** | | |
|  | | |
| **Prepared by:** |  |  |
| **Dean Wende Wu**  **WEWU**  Security Consultant  NNIT | Date  \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ | Signature  **\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_** |
| **Approved by:** | |  |  |
| **Li Wei, David**  **WZZL**  Sr. Digital Product Manager  190101 Frontline Support & Insights | | Date  \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ | Signature  **\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_** |

目录

[1. Purpose 3](#_Toc180046850)

[2. Scope of data transfer 3](#_Toc180046851)

[3. Description of IT interface 3](#_Toc180046852)

[3.1. High-level functionality and business context 3](#_Toc180046853)

[3.2. Data flow diagram 4](#_Toc180046854)

[3.3. Technical details 5](#_Toc180046855)

[3.4. Compliance status and impact 5](#_Toc180046856)

[4. Documentation 6](#_Toc180046857)

[5. Information security 6](#_Toc180046858)

[6. Operations and maintenance 6](#_Toc180046859)

[6.1. Change management 6](#_Toc180046860)

[6.2. Incident management 6](#_Toc180046861)

[6.3. Service level agreement (SLA) / service level objectives (SLO) 6](#_Toc180046862)

[7. References 7](#_Toc180046863)

[8. Change log 7](#_Toc180046864)

## Purpose

This document describes the interface of the NNSH Splunk platform, and the business need the IT interface addresses; and it provides information about the setup, functionalities, information security measures as well as the terms for using the IT interface including support and service levels.

Go to the IT&Q Portal to see definitions of terms[[1]](#footnote-2) used in this document.

## Scope of data transfer

This ‘*Interface Terms of Service*’ document covers the below data transfers:

| **IT interface details** | **Data providing IT system** | **Data transfer via IT interface components** | **Data receiving IT system** |
| --- | --- | --- | --- |
| Name: DB Connection Collection Log  Type: application | NNSH IT system | DB Connection | NNSH Splunk Platform |
| Name: File Log Collection  Type: application | NNSH IT system | Script collection log | NNSH Splunk Platform |
| Name: API Collection Log  Type: application | NNSH IT system | HTTP APIs | NNSH Splunk Platform |
| Name: Event Hub Collection Log  Type: application | NNSH IT system | Azure Event Hub | NNSH Splunk Platform |

## Description of IT interface
## High-level functionality and business context

The below table outlines how each key functionality of the IT interface serves a specific business need.

| **IT interface component** | **High-level functionality** |
| --- | --- |
| DB Connection | The application logs will be added in the specific tables in Database.  The NNSH Splunk platform reads the log tables in the database to import the application log. |
| File log collection | The applications in NNSH internal network will export application logs to log files and upload these log files to a log hub server in DMZ.  The NNSH Splunk Heavy Forwarder server will read these log files via SFTP and import the application logs in files. |
| HTTP APIs | Applications send the logs to HTTP API interface which was opened on the NNSH Splunk platform with HTTPS protocol. |
| Azure Event Hub | Some applications on Azure China will export logs to Azure Event Hub.  NNSH Splunk platform collects these application logs through the Event Hub. |

The IT interface makes the following data available for consumption:

| **Data entity** | **Description** | **Data Owner (if assigned)** |
| --- | --- | --- |
| time | Used to record the time of an event | NNSH IT System Owner |
| subject | Used to record the subject of the operation of the event, such as User, UserID, etc. | NNSH IT System Owner |
| object | Objects used to record the occurrence of an event, such as Hostname, target user, etc. | NNSH IT System Owner |
| operation | Used to record detailed operations, such as adding, deleting, changing and checking | NNSH IT System Owner |
| result | Used to record the result of an operation | NNSH IT System Owner |

### Data flow diagram

The system will be used as Log management platform and collect application and database log from resources which need log monitoring.

Platform Architecture Diagram:

![](data:image/png;base64...)

### Technical details

| **IT interface component** | **High-level functionality** |
| --- | --- |
| DB Connection | The application logs will be logged in the specific tables in Database servers. This step will be performed by application developing team.  The database connection plugin will be installed on NNSH Splunk Heavy forwarder server.  The DB connection and reading tasks will be setting in database connection plugin.  The log reading tasks will run regularly, customized according to the application requirement. |
| File log collection | The applications in NNSH internal network will export application logs to log files and send these log files to a log hub server in DMZ.  The NNSH Splunk Heavy Forwarder server will read these log files via SFTP and save these log files in the specific file directories, responding to each application.  The NNSH Splunk P will monitor the specific file directories and import the logs if any updating of files. |
| HTTP APIs | The Splunk software on NNSH Splunk Heavy Forwarder server is to generate unite token for each application, while set up HTTP API interface.  Application is to send logs via HTTP API interface, with HTTPS protocol. The transferring must be authorized with the token for each application. |
| Azure Event Hub | Some applications will export logs to Azure Event Hub.  NNSH Splunk platform collects these application logs through the Event Hub with a plugin developed in Python.  The NNSH Splunk platform needs to be authorized by Azure China platform with a read-only Application account, before logs reading from Event Hub. |

### Compliance status and impact

| **Regulatory requirement** | **Impact** | **Validated** | **Next periodic review** |
| --- | --- | --- | --- |
| GxP | No | No |  |
| Sarbanes-Oxley | No | No |  |
| GDPR/PIPL (personal data) | Yes | Yes |  |
| HIPAA | No | No |  |

The data consumer is responsible for any use of the data in compliance with the requirements.

## Documentation

| **Documentation** | **Reference / ID** |
| --- | --- |
| *Specification* |  |
| ITQ\_AI1\_User Requirements Specification (URS)\_Use Case and Row based\_NNSH Splunk Platform | F-01069157 |
| IT Functional-Design Specification \_NNSH Splunk Platform | F-01069158 |
| IT Operation and Maintenance Description\_NNSH Splunk Platform | <Reference/ID> |
| Instruction of security log management for NNSH Azure China Cloud | <Reference/ID> |

## Information security

The below security measures are in place:

| **Security measure** | **Parameters** |
| --- | --- |
| Network security | * Only open the necessary ports to specific IP address sources. |
| Authentication and authorisation | * When the NNSH Splunk platform connects to the log resources of applications systems to read and logs, authentication is required and the least privilege will be granted. * When the application system sends logs through an interface, authentication and authorization are required. |
| Encryption | * All log data must be encrypted during transmission. |
| Anti-DDoS | * HTTP API interface is protected by Anti-DDoS system |
| Web attack defence | * HTTP API interface is protected by WAF(Web Application Firewall), o defend against web layer attacks |

## Operations and maintenance
### Change management

Change control is handled according to ‘IT Operation and Maintenance Description NNSH Splunk Platform’ [4] and ‘Manage IT systems including digital solutions’ [3].

### Incident management

Monitoring and support of the IT interface is handled following NNSH IT Incident management process.

### Service level agreement (SLA) / service level objectives (SLO)

For an overview of the interfaces/integrations and SLAs governing the Vault Quality system, please refer to ServiceNow and the system description with ID #6873.

| **Metric** | **Target** | **Acceptable range** |
| --- | --- | --- |
| Uptime | 99% | 98.5-99.9% |
| Response time | 500 milliseconds | 500-1000 milliseconds |
| Error rate | Less than 1% | Less than 1-3% |
| Scheduled maintenance | 3 days’ notice | 2-7 days’ notice |

## References

|  |  |
| --- | --- |
| [1] | F-01069157 *ITQ\_AI1\_User Requirements Specification (URS)\_Use Case and Row based\_NNSH Splunk Platform* |
| [2] | F-01069158 IT Functional-Design Specification \_NNSH Splunk Platform |
| [3] | IT Operation and Maintenance Description\_NNSH Splunk Platform |
|  | Instruction of security log management for NNSH Azure China Cloud |
| [4] | F-01069158 *Protecting and handling information.* |
| [5] | *Q187219 Manage IT systems including digital solutions.* |

## Change log

| **Version no** | **Date** | **Change description** |
| --- | --- | --- |
| 1.0 |  | New document |

1. [↑](#footnote-ref-2)