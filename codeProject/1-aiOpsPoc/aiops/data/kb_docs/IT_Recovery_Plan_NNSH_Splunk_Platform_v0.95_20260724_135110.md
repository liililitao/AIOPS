|  |  |  |
| --- | --- | --- |
# IT Recovery Plan
|  | | |
| **This document is signed electronically using QualityDocs.**  **Signatures appear on a separate signature page.** | | |
|  | | |
| **Prepared by:** |  |  |
| **Li Peng**  **LPNL**  Author  NNIT | Date  \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ | Signature  **\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_** |
|  |  |  |
| **Review by:** |  |  |
| **Tan Jiyuan**  **JIYT**  Service Manager  NNIT | Date  \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ | Signature  **\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_** |
| **Li Wei, David**  **WZZL**  Senior IT Consultant  6277 IT Support China | Date  \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ | Signature  **\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_** |
|  |  |  |
| **Approved by:** |  |  |
| **Xie Tao, Tony**  **TAOX**  Sr. BIT Manager, IT Operation  6277 IT Support China | Date  \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ | Signature  **\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_** |

Contents

[1. Purpose 3](#_Toc181278843)

[2. Scope 3](#_Toc181278844)

[3. Roles and responsibilities 4](#_Toc181278845)

[4. Contact information and communications 6](#_Toc181278846)

[5. IT recovery planning 9](#_Toc181278847)

[5.1. IT recovery strategy 9](#_Toc181278848)

[5.2. IT recovery priorities 9](#_Toc181278849)

[5.3. Backup and restore information 10](#_Toc181278850)

[5.4. IT recovery list 10](#_Toc181278851)

[5.5. Release of IT solution after recovery (Post-recovery check) 11](#_Toc181278852)

[6. Testing of the IT recovery plan 11](#_Toc181278853)

[6.1. System recovery testing 11](#_Toc181278854)

[6.2. Review of contact information and recovery file 12](#_Toc181278855)

[6.3. Reporting the result 12](#_Toc181278856)

[7. References 12](#_Toc181278857)

[8. Enclosure 12](#_Toc181278858)

[Appendix 1: IT recovery test report 13](#_Toc181278859)

## Purpose

The purpose of this IT recovery plan for the NNSH Splunk platform is to describe IT recovery to ensure recovery from a major incident or disaster as quickly as possible and with minimal disruption.

The IT recovery plan is based on the requirements in the section ‘Manage backup and recovery’ in ‘Manage IT Systems’ [1] and outlined in the [Manage backup and recovery of IT systems – Guideline][[1]](#footnote-1).

Go to the IT&Q Portal to see definitions of terms[[2]](#footnote-2) used in this document.

## Scope

The activities outlined in this document will be executed and reported on according to the following NN QMS instructions:

* Manage IT Systems [1]
* Manage IT Security [2]
* Manage IT Infrastructure [3]
* Ownership of IT systems [4]

The IT recovery plan for NNSH Splunk platform reflects the IT recovery framework shown in Figure 1 and covers:

* System description according to [1]
* System dependent infrastructure services:

![](data:image/png;base64...)

IT recovery plans covering standard or core infrastructure services, for example LAN, WAN, Exchange and Citrix, are recovered according to ‘Manage IT infrastructure’ [3].

## Roles and responsibilities

| **Role** | **Responsibilities** | **Name** | **Department** |
| --- | --- | --- | --- |
| IT System Owner | * Responsible for the availability, and maintenance of the IT system and for the security of the data residing on the system. | Xie Tao  (TAOX) | NN Global IT Operations |
| IT System/ Service Manager | * Ensure the IT recovery plan is established (this document) * Handle major incidents at system/service level according to this plan * Release of NNSH Splunk Platform upon post-recovery check | Li Wei (WZZL) | NN Global IT Operations |
| Major Incident/ Disaster Manager | * Perform high level analysis regarding the impact and consequences of the reported potential Major Incident * Decide whether to invoke the MI/DR plan or handle the incident according to ‘Manage IT Incidents’ (Q204009) or any other applicable local instruction * Establish a MI conference bridge call inviting relevant stakeholders * Communicate the MI/DR information and status to the stakeholders * Manage the MI/DR as described in the Major Incident and Disaster Recovery Plan * Establish a recovery file and ensure that the file is updated every quarter and maintain it in the specified location | Xie Tao(TAOX)  Li Wei (WZZL) | NN Global IT Operations |
| Incident Manager | * Ensure Incident Management under the Incident Manager’s responsibility (location, functional / geographic area or service) is delivered in accordance with the ‘Manage IT Incidents’ processes * Communicate with stakeholders from the client organisation, management, vendors and other organisations * Ensure Incident Management Key Performance Indicators (KPIs) are monitored, met and reported on * Provide proposals for improvements to ‘Manage IT Incidents’ to the Process Owner * Ensure compliance requirements are met with regard to delivery of the ‘Manage IT Incidents’ process, for example that Incidents are identified * Support the Major Incident Manager regarding management and coordination of Major Incidents * Monitor, escalate and report on IT Incidents and IT Service Requests within Incident Manager’s area of responsibility (location, functional/geographic area or service) * Escalate urgent incidents to the Major Incident Manager * Release of NNSH Splunk Platform upon post-recovery check | Liu Yuquan (YQUL) | NNIT Delivery Team |
| Platform Recovery Team  (Platform) | * Responsible for recovering system or services other than VM components according to SLA/contract (defined RPO and RTO targets) | Li Peng  (LPNL) | NNIT |
| Infrastructure Management Team | * Responsibility of availability, maintenance and support of IaaS and PaaS components of NNSH Splunk Platform according to SLA/contract (defined RPO and RTO targets) | TAOX (Xie Tao)  WZZL(Li Wei) | NN Global IT Operations |
| infrastructure service delivery team | * Responsible for recovering IaaS and PaaS components of NNSH Splunk Platform according to SLA/contract (defined RPO and RTO targets) | JIYT(Tan jiyuan)  QNWI(Wei Qiang)  BAOT(Teng Baosen)  BALI(Li Biao) | NNIT |

Go to the IT&Q Portal to see other descriptions of responsibilities for roles[[3]](#footnote-3) used in this guideline.

## Contact information and communications

The contact information and actions that must be in place before a major incident or disaster occurs are documented in below table.

| **Role** | **Contact**  **(name/**  **initials)** | **Action** | **Department** | **How**  <Email> |
| --- | --- | --- | --- | --- |
| Major Incident/  Disaster Manager | Xie Tao (TAOX)  Li Wei (WZZL) | * Decide whether to declare an incident being major incident and invoke the major incident responses * Communicate to relevant stakeholder in case of major incident * Manage the major incident process | NN Global IT Operations | taox@novonordisk.com  wzzl@novonordisk.com |
| IT System/ Service Manager | Li Wei (WZZL) | * Ensure the IT recovery plan is established (this document) * Handle major incidents at system/service level according to this plan * Release of NNSH Splunk Platform upon post-recovery check | NN Global IT Operations | wzzl@novonordisk.com |
| Incident Manager | Liu Yuquan (YQUL) | * Manage the incident according to NN QMS and ensure compliance requirements are met * Communicate with relevant stakeholders in case of incident * Escalate urgent incidents to Major Incident Manager * Support Major Incident Manager regarding management and coordination of Major Incidents * Responsible for coordinating communications between infrastructure manager and application maintenance responsible | NNIT Delivery Team | YQUL@novonordisk.com |
| Major Incident/ Disaster Manager,  Infrastructure Manager | TAOX (Xie Tao) | * Responsible for the Major Incident and Disaster Recovery Plan * Responsibility of availability, maintenance and support of IaaS and PaaS components of NNSH Splunk Platform according to SLA/contract (defined RPO and RTO targets) | NN Global IT Operations | taox@novonordisk.com |
| Major Incident/ Disaster Manager Delegate,  Infrastructure Manager Delegate | WZZL (Li Wei) | * Responsible for the Major Incident and Disaster Recovery Plan * Responsibility of availability, maintenance and support of IaaS and PaaS components of NNSH Splunk Platform according to SLA/contract (defined RPO and RTO targets) | NN Global IT Operations | wzzl@novonordisk.com |
| Infrastructure Service Delivery Manager | JIYT(Tan Jiyuan) | * Responsible for recovering IaaS and PaaS components of the NNSH Splunk platform according to SLA/contract (defined RPO and RTO targets) | NNIT | jiyt@nnit.com |
| infrastructure service delivery team | QNWI(Wei Qiang)  BAOT(Teng Baosen)  BALI(Li Biao)  JYOL(Liu Jiayao) | * Responsible for recovering IaaS and PaaS components of NNSH Splunk Platform according to SLA/contract (defined RPO and RTO targets) | NNIT | qnwi@novonordisk.com  baot@novonordisk.com  bali@novonordisk.com  jyol@novonordisk.com |
| Platform Maintenance Responsible | Li Pent/ LPNL | * Work on recovery of the application-level services * Inform Incident Manager and Major Incident Manager if applicable when services are recovered * Communicate with Incident Manager and Major Incident Manager when RTO and RPO are not expected to meet | NNIT | LPNL@NNIT.com |

### Communication channel

### Identification

1. In the event of an incident (such as system service disruption or hacking), the communication should be first brought to **incident manager** noting the date and time of the incident, events occurred, and relevant details that are helpful to provide insights into root cause of the incident.
2. It is the responsibility of the **incident manager** to communicate to the following relevant stakeholders for the next steps:
   * To notify system owner of the issue
   * To escalate to Major Incident Manager, depending on the urgency and impact scale.
   * Assist Major Incident Manager following Major Incident process, if applicable
3. It is solely the responsibility of the **Major Incident Manager** to declare whether the noted incident is a Major Incident/Disaster and the Major Incident response process should be invoked.
4. It is the responsibility of **System Owner** to communicate with relevant Line of Business stakeholders or provide guidance of specific communication to incident manager if preferred. The **System Owner** also gets to decide whether and when to execute business continuity plan while system is waiting to be recovered.

### Analysis & Resolution

1. Depending on the nature of the incident, incident management process or Major Incident management process is followed
2. **Incident Manager** should first notify **infrastructure management team** via email to perform recovery of relevant Azure services. The communication should include specific Azure VM service to be restored and target resolution time. **The infrastructure management team** (NNIT Cloud Operations team) should be able to restore within 8 hours since being notified of the incident.
3. Once restoration is completed, the **infrastructure management team** should notify Incident Manager and application maintenance team via email of the successful restoration.
4. The next step is for the **Platform Recovery Team** to restore at the Splunk platform level. The team is expected to work on the recovery of system and validate the system can continue to operate as usual and support relevant business operations. The recovery process should take less than 16 hours considering the time needed to recovery infrastructure services, in order to meet the RTO of 24 hours and RPO of 24 hours (backup from yesterday).
5. Once the system has been confirmed to be fully recovered and operates successfully, it is the responsibility of **Platform Recovery Team** to notify **NN incident manage** (and Major Incident Manager, if applicable) via email of the updated status.
6. NN incident manager then can notify **System Owner** of the successful recovery, who can then further distribution the message to impacted Line of Business.

**Note:** In case of any data breach of personal information, it is the responsibility of any Novo Nordisk employee who becomes aware of the incident to immediately report the incident to china-privacy@novonordisk.com. For details on Response Process for Data Breach, please refer to **Q0787836 Personal Data Protection Policy in China**.

## IT recovery planning
### IT recovery strategy

The following is a description of the IT recovery strategy for the NNSH Splunk platform. The IT recovery approach is scaled to need and is based on the IT risk assessment as described in ‘Manage IT Systems’ [1], ‘Manage IT Security’ [2] and ‘Manage IT Infrastructure’ [3].

The recovery of the NNSH Splunk platform relies on infrastructure management team to recover supporting infrastructure services first and for the NNIT CN Security Operation team to recover the NNSH Splunk Platform.

### IT recovery priorities

The top priority of disaster recovery plan is always people. Once we have confirmed people are out of harm, we can then address IT recovery and kick off restoration process.

The following components have been identified to be critical to the operation of the NNSH Splunk platform and data integrity:

* Azure VM Service with snapshot of Operating Systems
* Azure network services
* VM backup in the on-premise network with snapshot of Operating Systems
* Environmental components of application such as: PA firewall, Bastion host

Critical platform component: Management portal

### Backup and restore information

Backup of the NNSH Splunk Platform solely relies on the backup strategy used by Azure and NNSH backup platform in the on-premise network. The backup schedule is also in line with the objectives of RPO (24 hours) and RTO (24 hours).

Currently Azure supports the backup policies for VM which is setting according to the local contract. Backups supported within defined timeframe can be fully recovered.

Currently VM backup platform in the on-premise network supports the backup policies for VM which is setting according to the local contract. Backups supported within defined timeframe can be fully recovered.

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Backup Subject** | **Backup Type** | **Backup Frequency** | **Backup Schedule** | **Retention Period** |
| VMs on Azure CN | Full | Daily | Monday - Saturday | 30 days |
| File log hub server in DMZ | Full | Daily | Monday - Saturday | 30 days |

In the event of major incident or disaster, NNIT infrastructure service delivery team will restore VMs and supported network services to the latest backup version, and After backups have been recovered by NNIT infrastructure service delivery team, the platform operation team will perform system integration testing to verify successful restoration of backup.

### IT recovery list

The listed documents must be available in case of a major incident or disaster.

| **Document** | **Doc. Reference**  **(version, id)** |
| --- | --- |
| IT Recovery Plan (this plan) | F-01070783, IT Recovery Plan\_NNSH Splunk Platform |
| Contact information (if not documented in this plan) | Refer to Section 4 |
| Configuration Items; Include hardware, as relevant | F-01069436, IT Operation and Maintenance Description\_NNSH Splunk Platform |
| Installation guide | F-01038752, Instruction - NNSH Splunk Platform Operation |
| Operations guideline | F-01069436, IT Operation and Maintenance Description\_NNSH Splunk Platform |
| Solution architecture documentation | F-01069436, IT Operation and Maintenance Description\_NNSH Splunk Platform |
| System Definition | F-01069157, User Requirements Specification (URS)\_NNSH Splunk Platform |
| Interface/network diagrams and information | F-01069440, IT Interface Terms of Splunk Platform |
| Data/Database architecture diagram | F-01069158, IT Functional-Design Specification \_NNSH Splunk Platform |
| Equipment configuration | F-01069158, IT Functional-Design Specification \_NNSH Splunk Platform |
| SLA | CIOA |
| Relevant SOPs or guidance | F-01069436, IT Operation and Maintenance Description\_NNSH Splunk Platform |

### Release of IT solution after recovery (Post-recovery check)

To release the recovered NNSH Splunk Platform to the users (fully or partly) after a major incident or disaster, the system manager delegates the application maintenance team to perform the activities described as follows:

1. Check that the NNSH Splunk Platform can log in normally
2. Check that the search function can be used normally
3. Check that each interface can receive the data normally
4. Check the system log for exceptions
5. Notify the system manager of the inspection result
6. Testing of the IT recovery plan
## System recovery testing

System recovery testing is done in case of significant changes to the intended purpose and/or functionality or supporting infrastructure services.

Given the system is hosted in cloud environment of Azure China and the NNSH Splunk platform relies heavily on Azure (21V China) in terms of the availability of the platform, it is determined to perform the system recovery testing in the form of simulation test. The IT disaster recovery plan is distributed to members of the disaster recovery team for review and test for the purpose of system recovery testing.

Simulation recovery test as follow:

1. Infrastructure management team restore production VM backup image to test environment.

2. Infrastructure management team completes testing of Azure VM service, and confirms that the VM has been restored.

Servers involved in recovery test and responsible person are as below:

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| **Server Name** | vm-cdcshared-prd-spl9head | vm-cdcshared-prd-spl9forwarder | vm-cdcshared-prd-spl9index1 | vm-cdcshared-prd-spl9index2 | APPCNBJ173 |
| **IP Address** | 10.31.19.232 | 10.31.19.233 | 10.31.19.234 | 10.31.19.235 | 10.38.28.48 |
| **Infrastructure Zone** | Azure | Azure | Azure | Azure | DMZ |
| **Software Name/Version** | Splunk Enterprise 9.2.2 | Splunk Enterprise 9.2.2 | Splunk Enterprise 9.2.2 | Splunk Enterprise 9.2.2 | N/A |
| **Environment** | Virtual | Virtual | Virtual | Virtual | Virtual |
| **Role** | Head | Heavy Forwarder | Index | Index | File log collection and sending |
| **Recovery test team** | NNIT CN Cloud operation | NNIT CN Cloud operation | NNIT CN Cloud operation | NNIT CN Cloud operation | NNIT CN Server operation |

### The platform recovery team completes testing of Splunk Platform according to Section 5.5, and confirms that the Splunk Platform has been restored.

The involved team member should review the plan to confirm the roles and responsibilities as well as to double check outdated information no longer fit for the system or organization would be updated post-review.

### Review of contact information and recovery file

The IT recovery plan should be reviewed on an annual basis initiated by System Manager and the following elements should be reviewed so that content is up to date:

* Contact information of Disaster Recovery team and/or key stakeholders
* Content of the IT recovery files in the above-mentioned Section 5.4
* Review of contracts to validate SLAs are defined and up to date

Communication of roles and responsibilities with involved Disaster Recovery team members and location of the IT recovery plan

### Reporting the result

Conclusion on the review, including any follow-up actions are documented in Appendix 1.

## References

|  |  |
| --- | --- |
| [1] | *187219 Manage IT Systems.* |
| [2] | *187655 Manage IT Security.* |
| [3] | 216301 Manage IT Infrastructure. |
| [4] | *187218 Ownership of IT Systems.* |

## Enclosure

|  |  |
| --- | --- |
| [1] | Encl.1 Recovery Test Screenshot\_NNSH Splunk platform |

Appendix 1: IT recovery test report

| **Review of contact information** | **Date** | **Doc. reference** |
| --- | --- | --- |
| Contact information reviewed and updated | 31-Oct-2024 | F-01070783, IT Recovery Plan\_NNSH Splunk Platform |
| Recovery file, incl. hard-copy file, reviewed and updated | 31-Oct-2024 | F-01070783, IT Recovery Plan\_NNSH Splunk Platform |
| **System recovery testing** | **Date** | **Doc. reference or summary** |
| Test of system recovery according to description in section 6. | 31-Oct-2024 | F-01070783, IT Recovery Plan\_NNSH Splunk Platform  Encl.1 Recovery Test Screenshot\_NNSH Splunk platform |
| Conclusion | Contacts and recovery testing in Disaster Recovery Plan of NNSH Splunk Platform has been reviewed and no further actions need to be taken. This DRP are agreed to be valid. | |

1. <https://novonordisk.sharepoint.com/sites/ITQ/SitePages/ManageBackupRecovery.aspx> [↑](#footnote-ref-1)
2. <https://novonordisk.sharepoint.com/sites/ITQ/SitePages/Definitions.aspx> [↑](#footnote-ref-2)
3. <https://novonordisk.sharepoint.com/sites/ITQ/SitePages/Roles.aspx> [↑](#footnote-ref-3)