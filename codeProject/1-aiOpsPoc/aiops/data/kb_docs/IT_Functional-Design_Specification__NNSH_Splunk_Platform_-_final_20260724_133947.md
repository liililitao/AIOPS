|  |  |  |
| --- | --- | --- |
# IT Functional Design Specification
|  | | |
| **This document is signed electronically using QualityDocs.**  **Signatures appear on a separate signature page.** | | |
|  | | |
| **Prepared by:** |  |  |
| **Wu Wende**  **QWWU**  Author  NNIT | Date  \_\_\_\_\_\_\_\_\_\_\_\_\_ | Signature  \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ |
|  |  |  |
| **Reviewed by:** |  |  |
| **Li Peng**  **LPNL**  Security Consultant  NNIT | Date  \_\_\_\_\_\_\_\_\_\_\_\_\_ | Signature  \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ |

|  |  |  |
| --- | --- | --- |
| **Approved by:** |  |  |
| **Li Wei, David**  **WZZL**  Senior IT Consultant  6277 IT Support China | Date  \_\_\_\_\_\_\_\_\_\_\_\_\_ | Signature  \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ |

|  |  |  |
| --- | --- | --- |
| **Approved by:** |  |  |
| **Xie Tao, Tony**  **TAOX**  Sr. BIT Manager, IT Operation  6277 IT Support China | Date  \_\_\_\_\_\_\_\_\_\_\_\_\_ | Signature  \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ |

Table of Contents

[1. Purpose 3](#_Toc180072497)

[2. Scope 3](#_Toc180072498)

[3. Definitions 3](#_Toc180072499)

[4. Specification requirements 3](#_Toc180072500)

[4.1. Functional requirements 4](#_Toc180072501)

[4.1.1 Log Collection 4](#_Toc180072502)

[4.1.2 Log Data Storage 8](#_Toc180072503)

[4.1.3 Log Analysis 8](#_Toc180072504)

[4.1.4 Log Search 9](#_Toc180072505)

[4.1.5 Custom Alerts 11](#_Toc180072506)

[4.1.6 Custom Reports 12](#_Toc180072507)

[4.1.7 Custom Dashboards 13](#_Toc180072508)

[4.2. Non-Functional requirements 15](#_Toc180072509)

[4.2.1 Performance Requirements 15](#_Toc180072511)

[4.2.2 Availability Requirements 16](#_Toc180072512)

[4.2.3 Operation Requirements 17](#_Toc180072513)

[4.2.4 Security Requirements 19](#_Toc180072514)

[4.2.5 Maintainability Requirements 27](#_Toc180072515)

[5. Traceability between user requirement and specification requirement ID 28](#_Toc180072516)

[5.1. Functional requirements 28](#_Toc180072517)

[5.2. Non-Functional requirements 29](#_Toc180072518)

[6. Enclosures 30](#_Toc180072519)

[7. References 30](#_Toc180072520)

## Purpose

The purpose of this document is to describe the functional design specification of the NNSH Splunk platform.

The document provides a description of the user requirements for the NNSH Splunk platform and to specify Novo Nordisk requirements for it.

The system will be used as Log management platform and collect application and database log from any resources where we need to monitor the data.

The system has agent and agentless implement methods. The agent will be installed on the target servers and policy will be configured in such a way to monitor the data. And it can also collect data by using plugins or connection string.

## Scope

The below is covered in this specification:

The scope of this document is to specify functional, non-functional for the NNSH Splunk platform. The requirements must be fulfilled by the service provider responsible for implementing, operating and managing the service for Novo Nordisk.

## Definitions

| **Term** | **Description** |
| --- | --- |
| Head | Central management server |
| Index | Log storage server |
| Heavy Forwarder | Gather and forward logs from Universal Forwarder to Index |
| Universal Forwarder | The light agent installed on server to collect logs |

Go to the [IT&Q Portal][[1]](#footnote-2) to see other definitions of terms used in this document.

## Specification requirements

The system will be used as Log management platform and collect application and database log from resources which need log monitoring.

Platform Architecture Diagram:

![](data:image/png;base64...)

Server Functionality Description:

| **Abbreviation/term** | **Definition/description** |
| --- | --- |
| Head | Central management server |
| Index | Log storage server |
| Heavy Forwarder | Gather and forward logs from Universal Forwarder to Index |
| Universal Forwarder | The light agent installed on server to collect security logs |
| CMP | Configuration Management Plan |

### Functional requirements
### Log Collection

| **FDS ID** | **Description** |
| --- | --- |
| FDS-LC-001 | Collecting security logs from Windows and Linux servers. |
| FDS-LC-002 | Collecting logs of the Azure Cloud Platform. |
| FDS-LC-003 | Collecting PA FW and Bastion host related logs. |
| FDS-LC-004 | Collecting logs exported from Anti-DDoS system. |
| FDS-LC-005 | Collecting relevant logs through the database interface. |
| FDS-LC-006 | Collecting logs in files which are exported by third-party application. |
| FDS-LC-007 | Collecting application logs through HTTP APIs. |
| FDS-LC-008 | Collecting application logs via Azure Event Hub. |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LC-001 |
| **Description** | Collecting security logs from Windows and Linux servers. |
| **Functions** | URS-LC-001: The NNSH Splunk platform needs to support the collection of logs related to Windows and Linux systems.  The Universal Forwarder will be installed on targeted servers and set as transferring the security logs to Splunk Heavy Forwarder server.  The log collecting port is setting as 9997, and the communication port is setting as 8089, on Splunk Heavy Forwarder server. |
| **Data** | Security logs of Windows and Linux servers. |
| **Non-functional attributes** | Encryption: all logs will be encrypted in transmission. |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LC-002 |
| **Description** | Collecting logs related to the Azure Cloud Platform |
| **Functions** | URS-LC-002: The NNSH Splunk platform needs to support the collection of logs related to the China Azure Cloud Platform.  The logs of related resources on China Azure Cloud platform will be exported to Event hubs on Azure CN.  The NNSH Splunk platform collects these logs through the Event Hub with a plugin developed in Python.  The NNSH Splunk platform needs to be authorized by Azure platform with a read-only Application account, before logs reading from Event Hub. |
| **Data** | Azure platform related Logs |
| **Non-functional attributes** | Authorization: The NNSH Splunk platform needs to be authorized by Azure platform with a read-only Application account.  Encryption: All logs will be encrypted in transmission. |
| **Environment** | Azure China Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LC-003 |
| **Description** | Collecting PA FW and Bastion host related logs |
| **Functions** | URS-LC-003: The NNSH Splunk platform needs to support the collection of PA FW and Bastion Host logs.  PA FW and Bastion Host send the security logs via SYSLOG.  Splunk Heavy forwarder open the SYSLOG receiving port for these 2 systems. |
| **Data** | PA FW and Bastion Host related logs |
| **Non-functional attributes** | Access control: The NSG of the NNSH Splunk platform is setting as only allowing the transferring of logs from PA FW and Bastion Host. |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LC-004 |
| **Description** | Collecting logs from Anti-DDoS system. |
| **Functions** | URS-LC-004: The NNSH Splunk platform needs to support the collection of logs from Anti-DDoS system.  The logs of Anti-DDoS system is to be exported as files in a specific directory of Splunk Heavy forwarder.  Splunk Heavy forwarder will monitor the specific directory to import the logs in files. |
| **Data** | The logs of Anti-DDoS system |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform  Anti-DDoS system |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LC-005 |
| **Description** | URS-LC-005: Collecting relevant logs through the database interface |
| **Functions** | URS-LC-005: The NNSH Splunk platform needs to support the collection of application logs through the database interface.  The application logs will be logged in the specific tables in Database servers. This step will be performed by application developing team.  The database connection plugin will be installed on Splunk Heavy forwarder server.  The DB connection and reading tasks will be setting in the Splunk DB connection plugin.  The log reading tasks will run regularly, customized according to the application requirement. |
| **Data** | Application logs |
| **Non-functional attributes** | Encryption: All connection will be encrypted.  Access control: The IP of Splunk Heavy forwarder server and log reading account must be allowed by DB server. |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LC-006 |
| **Description** | Collecting logs in files which are exported by third-party application. |
| **Functions** | URS-LC-006: The NNSH Splunk platform needs to support the collection of logs from files exported by third-party applications in an intranet environment per hour.  The applications in NNSH internal network will export application logs to files and send these log files to a log hub server in DMZ via FTPS.  The Splunk Heavy Forwarder server will read these log files via SFTP and save these log files in the specific file directories responding to each application per hour.  The Splunk software will monitor the specific file directories and import the logs if any updating of files. |
| **Data** | Applications logs. |
| **Non-functional attributes** | Encryption: All connection will be encrypted.  Access control: The IP of Splunk Heavy forwarder server and log reading account must be allowed by DMZ SFTP server. |
| **Environment** | DMZ  Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LC-007 |
| **Description** | Collecting application logs through HTTP APIs.. |
| **Functions** | URS-LC-006: The NNSH Splunk platform needs to collect application logs through HTTP APIs.  The Splunk software on Splunk Heavy Forwarder server is to generate unite token for each application, while set up HTTP API interface.  Application is to send logs via HTTP API interface, with HTTPS protocol. The transferring must be authorized with the token for each application. |
| **Data** | Applications logs |
| **Non-functional attributes** | Encryption: All HTTP connection will be encrypted with TLS 1.2 or higher.  Access control: Only the log transfers with a correct token will be accepted by the Splunk Heavy Forwarder server. |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LC-008 |
| **Description** | Collecting application logs in Azure Event Hub. |
| **Functions** | URS-LC-008: The NNSH Splunk platform needs to support the collection of application logs in Azure Event Hub.  Some applications will export logs to Azure Event Hub.  The NNSH Splunk platform collects these application logs through the Event Hub with a plugin developed in Python.  The NNSH Splunk platform needs to be authorized by Azure platform with a read-only Application account, before logs reading from Event Hub. |
| **Data** | Applications logs |
| **Non-functional attributes** | Authorization: The NNSH Splunk platform needs to be authorized by Azure platform with a read-only Application account  Encryption: All logs will be encrypted in transmission. |
| **Environment** | Azure Cloud Platform |

### Log Data Storage

| **FDS ID** | **Description** |
| --- | --- |
| FDS-LDS-001 | Logs will be stored for 6 months |
| FDS-LDS-002 | Log storage time will be adjusted on demand |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LDS-001 |
| **Description** | Logs will be stored for 6 months |
| **Functions** | URS-LDS-001: The NNSH Splunk platform needs to support 6 months of log storage  Splunk creates a separate index for logs that have a storage requirement of 6 months.  The log storage space will be checked weekly to meet the log storage capacity requirements. |
| **Data** | All logs collected by Splunk |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LDS-002 |
| **Description** | Log storage time will be adjusted on demand |
| **Functions** | URS-LDS-002: The NNSH Splunk platform needs to adjust log storage time based on application requirements  Splunk creates separate index storage for logs that have other period needs.  The log storage space will be checked weekly to meet the log storage capacity requirements. |
| **Data** | All logs collected by Splunk |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

* + 1. Log Analysis

| **FDS ID** | **Description** |
| --- | --- |
| FDS-LA-001 | Data in logs will be extracted according to Splunk rules |
| FDS-LA-002 | Extracted field names will be normalised |
| FDS-LA-003 | Extracted field values can be calculated |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LA-001 |
| **Description** | Data in logs will be extracted according to Splunk rules |
| **Functions** | URS-LA-001: The NNSH Splunk platform needs to support extract valuable fields from logs and store them as required  By using custom field extraction rules, the Splunk system can perform customization and extraction of specific log fields. These custom field extraction rules can be saved on the platform and automatically invoked when searching for specific logs, or they can be manually invoked based on user requirements. |
| **Data** | All logs collected by Splunk |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LA-002 |
| **Description** | Extracted field names will be normalised |
| **Functions** | URS-LA-002: The NNSH Splunk platform needs to support rename fields based on usage requirements  The NNSH Splunk platform can rename the names of log fields through commands. The renamed fields can then be used in the process of statistics and analysis. |
| **Data** | All logs collected by Splunk |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LA-003 |
| **Description** | Extracted field values can be calculated |
| **Functions** | URS-LA-003: The NNSH Splunk platform needs to support calculate fields based on usage requirements  New data is generated by the NNSH Splunk platform engineers manually extracting relevant fields from logs and performing calculations. |
| **Data** | All logs collected by Splunk |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

* + 1. Log Search

| **FDS ID** | **Description** |
| --- | --- |
| FDS-LS-001 | The NNSH Splunk platform will use inverted indexes to build index tables for logs |
| FDS-LS-002 | The NNSH Splunk platform will present search results in a structured format |
| FDS-LS-003 | The NNSH Splunk platform will support multiple file formats for exporting search results. |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LS-001 |
| **Description** | The NNSH Splunk platform will use inverted indexes to build index tables for logs |
| **Functions** | URS-LS-001: Splunk platform needs to support fuzzy keyword searches.  The NNSH Splunk platform enables fuzzy keyword searches using an inverted index. |
| **Data** | All logs collected by Splunk |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LS-002 |
| **Description** | The NNSH Splunk platform will present search results in a structured format |
| **Functions** | URS-LS-002: Splunk platform needs to support the constructed presentation of logs.  The NNSH Splunk platform achieves a structured presentation of logs by building an internal knowledge base. |
| **Data** | All logs collected by Splunk |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-LS-003 |
| **Description** | The NNSH Splunk platform will support multiple file formats for exporting search results. |
| **Functions** | URS-LS-003: Splunk platform needs to support the export of search results  The NNSH Splunk platform can export search results to csv, json and XML files. |
| **Data** | All logs collected by Splunk |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

* + 1. Custom Alerts

| **FDS ID** | **Description** |
| --- | --- |
| FDS-CA-001 | The NNSH Splunk platform will design rules to monitor alerts at the operating system level for actions such as adding and removing users. |
| FDS-CA-002 | The NNSH Splunk platform can send alert emails to specific email addresses as needed. |
| FDS-CA-003 | The NNSH Splunk platform designs alert rules to monitor license usage. |
| FDS-CA-004 | The NNSH Splunk platform will customise alerting rules based on application requirements |

|  |  |
| --- | --- |
| **FDS ID** | FDS-CA-001 |
| **Description** | The NNSH Splunk platform will design rules to monitor alerts at the operating system level for actions such as adding and removing users. |
| **Functions** | URS-CA-001: The NNSH Splunk platform needs to monitor operations such as adding and removing users at the OS layer  The NNSH Splunk platform engineers analyse system logs to design alert rules for operations such as adding and deleting users. |
| **Data** | Windows and Linux system logs |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-CA-002 |
| **Description** | The NNSH Splunk platform can send alert emails to specific email addresses as needed. |
| **Functions** | URS-CA-002: The NNSH Splunk platform needs to support email alerts  To configure the email sending functionality, an email account and password need to be set up in the system beforehand. This email account must allow the NNSH Splunk platform to connect and send emails.  Then, While setting up the alert on the NNSH Splunk platform, the email recipient addresses can be configured according to user requirements. Once the alert is triggered, the system can send alert emails to the specified email addresses. |
| **Data** | Application-specific logs |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-CA-003 |
| **Description** | The NNSH Splunk platform designs alert rules to monitor license usage. |
| **Functions** | URS-CA-003: The NNSH Splunk platform needs to monitor its own platform license with alerts  Configure an daily alert to send an email to the NNSH Splunk platform administrator when license usage exceeds 95%. |
| **Data** | Splunk's own log |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-CA-004 |
| **Description** | The NNSH Splunk platform will customise alerting rules based on application requirements |
| **Functions** | URS-CA-004: The NNSH Splunk platform needs to support customized alerts based on the customer’s requirements.  The NNSH Splunk platform can configure different alert rules based on application requirements and send alert emails to specific email addresses. |
| **Data** | Application-specific logs |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

* + 1. Custom Reports

| **FDS ID** | **Description** |
| --- | --- |
| FDS-CR-001 | Configure a regular report to send reports on a regular time period to a specific email. |
| FDS-CR-002 | Specific data will be counted to further analyse the data |
| FDS-CR-003 | The NNSH Splunk platform can customise reports based on application requirements. |

|  |  |
| --- | --- |
| **FDS ID** | FDS-CR-001 |
| **Description** | Configure a regular report to send reports on a regular time period to a specific email. |
| **Functions** | URS-CR-001: The NNSH Splunk platform needs to support the ability to send reports on a regular basis  The NNSH Splunk platform can extract specific logs as needed on a regular time period, then generate reports using the extracted logs and send report to the specific mailboxes. |
| **Data** | Specific logs |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-CR-002 |
| **Description** | Specific data will be counted to further analyse the data |
| **Functions** | URS-CR-002: The NNSH Splunk platform needs to support pre-processing of data  The NNSH Splunk platform engineers pre-process and analyse the data with extracted fields and usage scenarios. |
| **Data** | Specific logs |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-CR-003 |
| **Description** | The NNSH Splunk platform can customise reports based on application requirements. |
| **Functions** | URS-CR-003: The NNSH Splunk platform needs to support customized report according to customer’s requirements  The NNSH Splunk platform engineers customise reports based on application requirements |
| **Data** | Application-specific logs |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

### Custom Dashboards

| **FDS ID** | **Description** |
| --- | --- |
| FDS-CD-001 | The NNSH Splunk platform will design database audit dashboard based on logs |
| FDS-CD-002 | The NNSH Splunk platform will design OS tier user auditing dashboard based on logs |
| FDS-CD-003 | The NNSH Splunk platform can send dashboards to specific people at regular intervals |
| FDS-CD-004 | The NNSH Splunk platform can customise dashboards based on application requirements |

|  |  |
| --- | --- |
| **FDS ID** | FDS-CD-001 |
| **Description** | The NNSH Splunk platform will design database audit dashboard based on logs |
| **Functions** | URS-CD-001: The NNSH Splunk platform needs to support producing a database audit dashboard  The NNSH Splunk platform engineer designs database audit dashboard based on database log analysis |
| **Data** | Database related logs |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-CD-002 |
| **Description** |  |
| **Functions** | URS-CD-002: The NNSH Splunk platform needs to support producing an OS layer user audit dashboard  The NNSH Splunk platform engineer designs system audit dashboard based on system log analysis |
| **Data** | Windows and Linux system logs |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-CD-003 |
| **Description** | The NNSH Splunk platform can send dashboards to specific people at regular intervals |
| **Functions** | URS-CD-003: The NNSH Splunk platform needs to support sending dashboards at regular intervals.  The NNSH Splunk platform engineers configure timed tasks to send dashboards on demand |
| **Data** | Application-specific logs |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-CD-004 |
| **Description** | The NNSH Splunk platform can customise dashboards based on application requirements |
| **Functions** | URS-CD-004: The NNSH Splunk platform needs to support customized dashboards according to customer’s requirements.  The NNSH Splunk platform engineers customise the dashboard to the needs of the application |
| **Data** | Application-specific logs |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

### Non-Functional requirements
### Performance Requirements

| **FDS ID** | **Description** |
| --- | --- |
| FDS-PR-001 | The NNSH Splunk platform will receive and store logs of 50 GB per day. |
| URS-PR-002 | The homepage of the NNSH Splunk platform responds to user web requests within 3 seconds. |
| URS-PR-003 | The average response time of the API interface is less than 1 second. |

|  |  |
| --- | --- |
| **FDS ID** | FDS-PR-001 |
| **Description** | The NNSH Splunk platform will receive and store logs of 50 GB per day. |
| **Functions** | URS-PR-001: The NNSH Splunk platform can receive and store logs of 50 GB per day.  Several servers will be set up to receive and store logs.  All servers will be set up following the requirements of Splunk software published by official web site, with the log requirements of 50 GB per day. |
| **Data** | All logs |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-PR-002 |
| **Description** | The homepage of the NNSH Splunk platform responds to user web requests within 3 seconds. |
| **Functions** | URS-PR-002: The homepage of the NNSH Splunk platform must respond to user web requests within 3 seconds.  Configure the network devices and servers with the required resources to achieve the goal of responding to user web requests within 3 seconds. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-PR-003 |
| **Description** | The average response time of the HTTP API interface is less than 1 second. |
| **Functions** | URS-PR-003: The average response time of the HTTP API interface must be less than 1 second.  Configure the network devices and servers with the required resources to achieve the goal of responding to HTTP API interface request within 1 second. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

### Availability Requirements

| **FDS ID** | **Description** |
| --- | --- |
| FDS-AR-001 | The reliability of the NNSH Splunk platform's interface will reach 99%. |
| FDS-AR-002 | The operational reliability of the platform will reach 99.5% |
| FDS-AR-003 | Recovery Time Objective (RTO)=1 day and Recovery Point Objective (RPO)=1 day |

|  |  |
| --- | --- |
| **FDS ID** | FDS-AR-001 |
| **Description** | The reliability of the NNSH Splunk platform's interface will reach 99%. |
| **Functions** | FDS-AR-001: The reliability of the NNSH Splunk platform's interface must reach 99%.  The Splunk servers will be monitored, to ensure server is running continuously.  The log receiving port, such as 9997, HTTPS will be monitored.  If any event raised by Monitoring system, NNIT maintenance team will be notified by calling. |
| **Data** | Monitor configuration |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-AR-002 |
| **Description** | The operational reliability of the platform will reach 99.5%. |
| **Functions** | FDS-AR-001: The reliability of the NNSH Splunk platform's interface must reach 99%.  The Splunk servers and the web service will be monitored, to ensure Splunk service is running continuously.  If any event raised by Monitoring system, NNIT maintenance team will be notified by calling. |
| **Data** | Monitor configuration |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-AR-003 |
| **Description** | Recovery Time Objective (RTO)=1 day and Recovery Point Objective (RPO)=1 day |
| **Functions** | FDS-AR-003: Recovery Time Objective (RTO)=1 day and Recovery Point Objective (RPO)=1 day.  All logs are stored on servers in the Azure China Cloud. The servers on the Azure China Cloud are configured with a full disk backup strategy: daily disk backups, weekly backups retained for one month, and monthly backups retained for six months. This meets the RPO (Recovery Point Objective) target 1 day.  The servers can be quickly restored using daily snapshots, meeting the RTO (Recovery Time Objective) target 1day. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

### Operation Requirements

| **FDS ID** | **Description** |
| --- | --- |
| FDS-OR-001 | All operational requirements and platform-related incidents will be recorded and tracked using SNOW. |
| FDS-OR-002 | The CMP needs to be set up, and CR management will follow the CIOA agreement. |
| FDS-OR-003 | The NNSH Splunk platform will to be available on 24 hours a day, 7 days a week.  Incident and event related with the NNSH Splunk platform will be handled on 24 hours a day, 7 days a week.  The customer request will be handled on China Business Days, Monday through Friday 09:00 to 18:00 GMT+8. |
| FDS-OR-004 | Set up and deploy a test environment, ensuring it has the same functionalities and interfaces as the production environment. |

|  |  |
| --- | --- |
| **FDS ID** | FDS-OR-001 |
| **Description** | All operational requirements and platform-related incidents will be recorded and tracked using SNOW. |
| **Functions** | URS-OR-001: All operational requirements and platform-related incidents will be recorded and tracked using SNOW.  Each operator will apply the NN initial and SNOW privilege.  A service request will be raised for each user requirement and any other operational requirement related with the NNSH Splunk platform. All follow-up actions will be tracked in SNOW.  An incident will be raised if any incident happened related with the NNSH Splunk platform, and all of investigation and resolving actions will be tracked in SNOW.  All of these requirements need to be detailed in Operation Manual. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | NN SNOW |

|  |  |
| --- | --- |
| **FDS ID** | FDS-OR-002 |
| **Description** | The CMP needs to be set up, and CR management will follow the CIOA agreement. |
| **Functions** | URS-OR-002: The CMP needs to be set up, and CR management will follow the CIOA agreement.  The Configuration Management Process will be drafted and upload to NNIT QPoint system.  The change request will be raised if any changing of key items in CMP.  The key items of configurations will be monitored and reviewed per year. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | NN SNOW  NNIT QPoint |

|  |  |
| --- | --- |
| **FDS ID** | FDS-OR-003 |
| **Description** | The NNSH Splunk platform will to be available on 24 hours a day, 7 days a week.  Incident and event related with the NNSH Splunk platform will be handled on 24 hours a day, 7 days a week.  The customer request will be handled on China Business Days, Monday through Friday 09:00 to 18:00 GMT+8. |
| **Functions** | URS-OR-003: The NNSH Splunk platform will to be available on 24 hours a day, 7 days a week.  Incident and event related with the NNSH Splunk platform will be handled on 24 hours a day, 7 days a week.  The customer request will be handled on China Business Days, Monday through Friday 09:00 to 18:00 GMT+8.  The Splunk servers and all services on servers will be running with no interrupt, unless any closing window.  The servers and core services will be monitored by Monitoring system.  If there are any issues with the platform or core services, the monitoring system will notify the on-duty person through the duty phone, also a SNOW incident will be raised.  The duty phone is on 24/7, and the on-duty person are on standby 24 hours a day, 7 days a week.  The customer request will be handled on working time, and will be tracked with a ticket in SNOW. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | Monitor system  NN SNOW |

Set up and deploy a test environment, ensuring it has the same functionalities and interfaces as the production environment.

|  |  |
| --- | --- |
| **FDS ID** | FDS-OR-004 |
| **Description** | Set up and deploy a test environment, ensuring it has the same functionalities and interfaces as the production environment. |
| **Functions** | URS-OR-003: The system needs to establish a testing environment. The resources for the testing environment should be configured according to the minimum requirements..  Deploy a server on the NNSH Azure China cloud with 4 cores and 16GB of memory, install the Splunk Enterprise software, and install the same plugins and config the same functionalities as the server environment. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | NNSH Azure China cloud |

### Security Requirements

| **FDS ID** | **Description** |
| --- | --- |
| FDS-SR-001 | The audit trail of the NNSH Splunk platform should be set up as required, and the audit logs should be preserved for 180 days.  Splunk system can generates audit trails, includes:  1. Creation, change, and cancellation of access authorization  2. Login success/failure, date/time of event and account  3. Who performed the log operation action  4. What was created/modified/deleted related with system management  Audit trail records is preserved for 6 months. |
| FDS-SR-002 | Admin users can delete logs which contain specific keyword and these activities will be logged.  Only admin user which was granted with "delete" privilege can delete the logs.  No data change can be performed. |
| FDS-SR-003 | Logs can be exported by a specific ‘individual’ request, and these activities will be logged. |
| FDS-SR-004 | Logs which include which include specific keyword can be temporarily excluded by a specific ‘individual’ request, and these activities will be logged. |
| FDS-SR-005 | All log data is transited in encryption by default. |
| FDS-SR-006 | All log data is stored in encryption by default. |
| FDS-SR-007 | User account can be traced to individuals and no shared account is used. All accounts will be individual, and activities will be logged. |
| FDS-SR-008 | The Splunk Platform can define user roles based on the supported business process which following the principle of least privilege |
| FDS-SR-009 | The Splunk Platform can follow the principle of separation of duties, ensuring that responsibilities are separated between different users. |
| FDS-SR-010 | The password policy can be set as:  i. minimum password length: 14  ii. frequency or triggers for changing passwords:120 days  iii. User will be log off after inactive for 15 minutes.  iv. limits on invalid logon attempts:5 times  v. locking of account after invalid logon attempts: 15 mins  vi. reset newly issued passwords at first use.  vii. token based authentication for application programming interfaces |
| FDS-SR-011 | The management interface of the NNSH Splunk platform can be accessed through the NNSH bastion host. |
| FDS-SR-012 | The servers of Splunk Platform must be deployed in a segregated Azure network, and controlled by PA firewall and NSG. |
| FDS-SR-013 | The user logon session will be set as time out if not active for 15 minutes. |
| FDS-SR-014 | All application log transfer activities that pass through the application log transfer interface will be recorded, including the time, source, and transfer result. The interface logs will be stored in a specific log repository and retained for 180 days. |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-001 |
| **Description** | The audit trail of the NNSH Splunk platform should be set up as required, and the audit logs should be preserved for 180 days.  Splunk system can generates audit trails, includes:  1. Creation, change, and cancellation of access authorization  2. Login success/failure, date/time of event and account  3. Who performed the log operation action  4. What was created/modified/deleted related with system management  Audit trail records is preserved for 180 days. |
| **Functions** | URS-SR-001: The audit trail is set up as default.  Splunk system can generates audit trails, includes:  1. Creation, change, and cancellation of access authorization  2. Login success/failure, date/time of event and account  3. Who performed the log operation action  4. What was created/modified/deleted related with system management  Audit trail records is preserved for 6 months.  While the software of Splunk Platform is installed, the audit trail is set as default. And all of these logs are recorded in \_initial index:  1. Creation, change, and cancellation of access authorization  2. Login success/failure, date/time of event and account  3. Who performed the log operation action  4. What was created/modified/deleted related with system management  The rotation period of \_initial index should be set as 6 months. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | NNSH Splunk platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-002 |
| **Description** | Admin users can delete logs which maybe contain specific keyword and these activities will be logged.  Only admin user which was granted with "delete" privilege can delete the logs.  No data change can be performed. |
| **Functions** | URS-SR-002: Admin users can delete logs which maybe contain specific keyword, and these activities will be logged.  Only admin user which was granted with "delete" privilege can delete the logs.  No data change can be performed.  The “delete” role can be granted to specific account which is responsible for delete logs as required.  The granted users can delete specific logs using “delete” comment, which is following the search action for certain specific keyword in logs.  All tasks will be done according to the customer's requirements, and all actions will be logged with the relevant logs preserved for 6 months.  No changes to logs can be performed on the NNSH Splunk platform as designed by the software. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | NNSH Splunk platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-002 |
| **Description** | Admin users can delete logs which contain specific keyword, and these activities will be logged.  Only admin user which was granted with "delete" privilege can delete the logs.  No data change can be performed. |
| **Functions** | URS-SR-002: Admin users can delete logs which contain specific keyword, and these activities will be logged.  Only admin user which was granted with "delete" privilege can delete the logs.  No data change can be performed.  The “delete” role can be granted to specific account which is responsible for delete logs as required.  The granted users can delete specific logs using “delete” comment, which is following the search action for certain specific keyword in logs.  All tasks will be done according to the customer's requirements, and all actions will be logged with the relevant logs preserved for 6 months.  No change to logs in the NNSH Splunk platform can be performed on the NNSH Splunk platform as designed by the software. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | NNSH Splunk platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-003 |
| **Description** | Logs which include specific keyword can be exported by a specific ‘individual’ request, and these activities will be logged. |
| **Functions** | URS-SR-003: Logs can be exported by a specific ‘individual’ request, and these activities will be logged.  Logs which include specific keyword can be filtered in “Search”.  The searching result can be downloaded from the NNSH Splunk platform.  All the searching and downloading actions must be done according to a specific ‘individual’ customer request, which will be tracked by ticket in SNOW.  All the searching and downloading actions will be recorded in \_internal index of Splunk. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | Splunk platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-004 |
| **Description** | Logs which include specific keyword can be temporarily excluded by a specific ‘individual’ request, and these activities will be logged. |
| **Functions** | URS-SR-004: Logs which include specific keyword can be temporarily excluded by a specific ‘individual’ request, and these activities will be logged.  Logs which include specific keyword can be temporarily excluded in “Search” or other customized Alert, Report and Dashboard, with specific SPL searching language.  All of the actions must be done according to a specific ‘individual’ customer request, which will be tracked by ticket in SNOW.  All of the actions will be recorded in \_internal index of Splunk. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | NNSH Splunk platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-005 |
| **Description** | All log data is transited in encryption by default. |
| **Functions** | URS-SR-005: All log data is transited in encryption by default.  Logs data is stored in separated indexed on a specific virtual Disk attaching with each server on Azure. The disks are encrypted by Azure by default.  All log transferring interfaces are encrypted, such as Splunk Agent to FW server, Azure Event Hub, HTTP API, DB Connection, SFTP and FTPS log file transferring, etc. |
| **Data** | All logs |
| **Non-functional attributes** | N/A |
| **Environment** | NNSH Splunk platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-006 |
| **Description** | All log data is stored in encryption by default. |
| **Functions** | URS-SR-006: All log data must be stored in encryption by default.  Logs data is stored in separated indexed on a specific virtual Disk attaching with 2 Splunk Index servers on Azure. The virtual disks are encrypted by Azure by default. |
| **Data** | All logs |
| **Non-functional attributes** | N/A |
| **Environment** | Azure China cloud |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-007 |
| **Description** | User account can be traced to individuals and no shared account is used. All accounts will be individual, and activities will be logged. |
| **Functions** | URS-SR-007: User account can be traced to individuals and no shared account is used. All accounts will be individual, and activities will be logged.  The account applying process is integrated in Novo Access.  After approval of request in Novo Access, the platform administrator will create individual accounts with the "Initial" identifier for the requester.  Shared accounts will not be created for platform access.  All accounts in the NNSH Splunk platform will be reviewed yearly.  All user activity logs will be categorized and recorded in the platform logs, and will be associated with individual accounts. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | NNSH Splunk platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-008 |
| **Description** | The Splunk Platform can define user roles based on the supported business process which following the principle of least privilege. |
| **Functions** | URS-SR-008: The NNSH Splunk Platform can define user roles based on the supported business process which following the principle of least privilege.  The NNSH Splunk platform has some default roles, such as admin, power, and can\_delete.  Also New Role can be defined with different functions, such as search, license management, file upload/download.  The individual account can be granted with customized role to follow the principle of least privilege. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | NNSH Splunk platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-009 |
| **Description** | The Splunk Platform can follow the principle of separation of duties, ensuring that responsibilities are separated between different users. |
| **Functions** | URS-SR-009: The Splunk Platform can Follow the principle of separation of duties, ensuring that responsibilities are separated between different users.  Create different accounts on the platform and configure the Segregation of Duties (SoD) between different accounts.  Refer to FDS-SR-7, we can grant least privilege to different accounts, to fulfil the SoD requirement. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | NNSH Splunk platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-010 |
| **Description** | The password policy will be set as:  i. minimum password length: 14  ii. frequency or triggers for changing passwords: 24  iii. limits on invalid logon attempts:5  iv. locking of account after 5 invalid logon attempts in 5 minutes, and locking for 15 minutes  v. reset newly issued passwords at first use. |
| **Functions** | URS-SR-010: The password policy can be set as:  i. minimum password length: 14  ii. frequency or triggers for changing passwords: 24  iii. limits on invalid logon attempts: 5  iv. locking of account after 5 invalid logon attempts in 5 minutes, and locking for 15 minutes  v. reset newly issued passwords at first use.  The password policy in NNSH Splunk platform will be set as:  15  When set up a new account, the “Require password change on first login” must be checked. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | NNSH Splunk platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-011 |
| **Description** | The management interface of NNSH Splunk platform can be accessed through the NNSH bastion host. |
| **Functions** | URS-SR-011: The management interface of the NNSH Splunk platform can only be accessed through the NNSH bastion host.  The NNSH Splunk platform's management interfaces are added in the bastion host.  Restrict access to the management interface so that it can only be accessed through a bastion host. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | NNSH Splunk platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-012 |
| **Description** | The servers of Splunk Platform must be deployed in a segregated Azure network, and controlled by PA firewall and NSG. |
| **Functions** | URS-SR-011: The network of system is isolated network and controlled by Cloud firewall and NSG.  The Azure network where the Splunk server is located will be configured with a Network Security Group (NSG) to restrict access to the Splunk server according to the log transferring request.  Configure firewall and WAF (Web Application Firewall) protection for the API interface, allowing access only through the HTTPS port and defending against web attacks. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | Azure CN cloud. |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-013 |
| **Description** | The user logon session will be set as time out if not active for 15 minutes. |
| **Functions** | URS-SR-012: The user logon session can be set as time out if not active for 15 minutes.  In the parameter configuration of the server's web login interface, the Splunk Web session timeout can be set as 15 minutes: |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | NNSH Splunk platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-SR-014 |
| **Description** | All application log transfer activities that pass through the application log transfer interface will be recorded, including the time, source, and transfer result. The interface logs will be stored in a specific log repository and retained for 180 days. |
| **Functions** | URS-SR-014: All application log transfer activities that pass through the application log transfer interface must be recorded, including the time, source, and transfer result. The interface logs must be stored in a specific log repository and retained for 180 days.  Store the application log data import behaviour logs in a separate log database. The log content should include the log source, transmission time, transmission result, and other relevant details. The transmission behaviour logs should be retained for 180 days. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | Application logs |

### Maintainability Requirements

| **FDS ID** | **Description** |
| --- | --- |
| FDS-MR-001 | 6 Servers will be built up, as different roles in Splunk Platform. |
| FDS-MR-002 | The capacity and performance of the NNSH Splunk platform can be easily improved. |

|  |  |
| --- | --- |
| **FDS ID** | FDS-MR-001 |
| **Description** | 6 Servers will be built up, as different roles in Splunk Platform. |
| **Functions** | URS-MR-001 : Breaking down the system into smaller, independent components that are easier to maintain.  6 Servers will be built up on NNSH Azure China, as different roles in Splunk Platform.  1 server will act as Splunk Search Head server, which acts as management server, and serve for user searching and customized alerts, customized report and customized dashboards.  2 servers will act as Splunk Index servers, which index and store all logs.  1 server will act as Forwarder server, which collect all kinds of logs from various interfaces, and send logs to Index servers.  1 server will be deployed in the DMZ network of the NNSH internal network and act as the file log hub server.  1 server will be installed as test server which is responsible for conducting preliminary tests before any key configuration change of production environment. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

|  |  |
| --- | --- |
| **FDS ID** | FDS-MR-002 |
| **Description** | The capacity and performance of the NNSH Splunk platform can be easily improved. |
| **Functions** | URS-MR-002: It is ease to improve the system processing capacity according to the log receiving capacity requirements..  Refer to FDS-MR-001, 4 servers will be set up and act as different roles in NNSH Splunk platform.  If related services experience performance issues, we can address the performance requirements of the corresponding functions by either enhancing the performance of the servers associated with the service roles or by adding new servers. |
| **Data** | N/A |
| **Non-functional attributes** | N/A |
| **Environment** | Azure Cloud Platform |

## Traceability between user requirement and specification requirement ID
### Functional requirements

| **User requirement** | **FDS ID** |
| --- | --- |
| URS-LC-001 | FDS-LC-001 |
| URS-LC-002 | FDS-LC-002 |
| URS-LC-003 | FDS-LC-003 |
| URS-LC-004 | FDS-LC-004 |
| URS-LC-005 | FDS-LC-005 |
| URS-LC-006 | FDS-LC-006 |
| URS-LC-007 | FDS-LC-007 |
| URS-LC-008 | FDS-LC-008 |
| URS-LDS-001 | FDS-LDS-001 |
| URS-LDS-002 | FDS-LDS-002 |
| URS-LA-001 | FDS-LA-001 |
| URS-LA-002 | FDS-LA-002 |
| URS-LA-003 | FDS-LA-003 |
| URS-LS-001 | FDS-LS-001 |
| URS-LS-002 | FDS-LS-002 |
| URS-LS-003 | FDS-LS-003 |
| URS-CA-001 | FDS-CA-001 |
| URS-CA-002 | FDS-CA-002 |
| URS-CA-003 | FDS-CA-003 |
| URS-CA-004 | FDS-CA-004 |
| URS-CR-001 | FDS-CR-001 |
| URS-CR-002 | FDS-CR-002 |
| URS-CR-003 | FDS-CR-003 |
| URS-CD-001 | FDS-CD-001 |
| URS-CD-002 | FDS-CD-002 |
| URS-CD-003 | FDS-CD-003 |
| URS-CD-004 | FDS-CD-004 |

### Non-Functional requirements

| **User requirement** | **FDS ID** |
| --- | --- |
| URS-PR-001 | FDS-PR-001 |
| URS-PR-002 | FDS-PR-002 |
| URS-PR-003 | FDS-PR-003 |
| URS-AR-001 | FDS-AR-001 |
| URS-AR-002 | FDS-AR-002 |
| URS-AR-003 | FDS-AR-003 |
| URS-OR-001 | FDS-OR-001 |
| URS-OR-002 | FDS-OR-002 |
| URS-OR-003 | FDS-OR-003 |
| URS-OR-004 | FDS-OR-004 |
| URS-SR-001 | FDS-SR-001 |
| URS-SR-002 | FDS-SR-002 |
| URS-SR-003 | FDS-SR-003 |
| URS-SR-004 | FDS-SR-004 |
| URS-SR-005 | FDS-SR-005 |
| URS-SR-006 | FDS-SR-006 |
| URS-SR-007 | FDS-SR-007 |
| URS-SR-008 | FDS-SR-008 |
| URS-SR-009 | FDS-SR-009 |
| URS-SR-010 | FDS-SR-010 |
| URS-SR-011 | FDS-SR-011 |
| URS-SR-012 | FDS-SR-012 |
| URS-SR-013 | FDS-SR-013 |
| URS-SR-014 | FDS-SR-014 |
| URS-MR-001 | FDS-MR-001 |
| URS-MR-002 | FDS-MR-002 |

## Enclosures

N/A

## References

|  |  |
| --- | --- |
| [1] | Doc. no. 187405, Specify User Requirements and Plan Implementation of IT Systems |
| [2] | ServiceNow no. 15502 Log Collection China |
| [3] | Doc. No. 187655, Manage IT Security |

1. [↑](#footnote-ref-2)