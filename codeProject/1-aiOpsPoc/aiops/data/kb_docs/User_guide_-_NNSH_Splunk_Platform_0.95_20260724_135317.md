|  |
| --- |
| **User guide – NNSH Splunk Platform** |
|  |
| **This document is signed electronically using QualityDocs.**  **Signatures appear on a separate signature page.** |

**Table of contents**

[1. Introduction 3](#_Toc180135606)

[1.1. Purpose 3](#_Toc180135607)

[1.2. Scope 3](#_Toc180135608)

[1.3. Abbreviations and definitions 3](#_Toc180135609)

[1.4. Roles and responsibilities 3](#_Toc180135610)

[2. NNSH Splunk platform operation 4](#_Toc180135611)

[2.1. overview 4](#_Toc180135614)

[2.2. Permission Application 4](#_Toc180135615)

[2.3. Platform login 4](#_Toc180135616)

[2.4. Log import 5](#_Toc180135617)

[2.5. Log search 5](#_Toc180135618)

[2.6. Log export 5](#_Toc180135619)

[2.7. Alert and report configuration 5](#_Toc180135620)

[Appendix 1. Application Log Integration Prerequisite 5](#_Toc180135621)

[Appendix 2. Application Log Integration Process 7](#_Toc180135622)

[Appendix 3. Application Log Integration Request Template 8](#_Toc180135623)

# Introduction

This instruction applies to all users of NNSH Splunk platform.

## Purpose

This document is to describe the steps on how to handle the security event and how to operate the NNSH Splunk platform on NNSH Azure cloud.

## Scope

* NNSH Splunk platform operation
* Application log import

## Abbreviations and definitions

|  |  |
| --- | --- |
| **Abbreviation** | **Definition** |
| NNSH | NOVO NORDISK (SHANGHAI) PHARMA TRADING CO., LTD. |
| NNSH GITO | NNSH Global IT Operation – APAC |
| Splunk | A powerful log management platform |

## Roles and responsibilities

| **Role** | **Team/Department** | **Responsibilities** |
| --- | --- | --- |
| Application log import requester | NNSH Application team | * Select the log import interface; * Develop the log export function * Send the logs to the NNSH Splunk platform through the selected interface. * Fill out the log import application form and submit it to the NNIT CN Security team. * Discuss with NNIT CN Security team and clarify the log import interface, alerting, and reporting requirements, etc. |
| NNSH Splunk platform operator | NNIT CN Security team | * Discuss with NNSH Application team and clarify the log import interface, alerting, and reporting requirements, etc. * Configure the log import interface and import the application's logs according to the requirements specified in the application form. * Configure alerts and reports according to the requirements specified in the application form and set them up to be sent to the designated email address * Export a sample of imported application log and send it to NNSH Application team to ensure the success of log import * Send the sample alert and report mail to NNSH Application team to To confirm that the alert and report configurations have been successfully set up. |
| NNSH Splunk Platform owner | NNSH GITO | * Approve the application of log import |

# NNSH Splunk platform operation

## overview

The NNSH Splunk platform runs on the NNSH Azure virtual server. The NNSH Splunk platform uses Splunk Enterprise software and components, Forwarder and Add-ons, to supply log management and SIEM platform.

The logs in platform can’t be modified by anyone, as Splunk stores logs in its own databases with un-discovered formats, and does not provide any function or interface to modify the logs. The logs in database can be deleted by users who are authorized.

## Permission Application

All operations on the NNSH Splunk platform must be authorized first. Permission requests are processed through the Novo Access platform, and the NNIT CN security team needs to assist in configuring the required permissions.

## Platform login

Start the Edge or other web browser, and open NNSH Bastion Host with Initial account. Then open the Applications with the URL of NNSH Splunk platform as below:

https://spl9headn3.chinanorth3.cloudapp.chinacloudapi.cn:8000/

![](data:image/png;base64...)

## Log import

After the application team develops and configures the log export interface, they can fill out the log application form and send it to the security team to discuss log import, alert, and report configuration matters.

For related requirements, processes, and application forms, please refer to the attachment.

## Log search

In the search interface, by entering search conditions and keywords, the NNSH Splunk platform can search and retrieve all logs that meet the criteria based on user input. Additionally, the search interface supports direct statistics and analysis of the retrieved logs. Relevant search commands need to be written according to the SPL (Search Processing Language) or simply by entering the keywords to be queried.

## Log export

After the log search is completed, directly click the export button on the interface to export all the search results to a specified CSV or PDF file.

## Alert and report configuration

The NNIT CN security team will configure the alerts and reports according to the application team's requirements, send them to the recipient email address specified in the application form.

# Appendix 1. Application Log Integration Prerequisite

The application logs need to be integrated into the NNSH Splunk platform for log auditing, and the following requirements need to be met:

1. The application should be able to generate and output logs.
2. The logs output by the application should be in JSON/CSV format.
3. The logs output by the application should comply with the Novo Nordisk IT Risk Assessment (ITRA) standard or meet the audit requirements. Audit-compliant logs must contain relevant information such as timestamps, user or hostname, operation descriptions, and operation results.
4. Avoid application log output containing personally sensitive data.
5. For applications using the HTTPS API interface, please contact NNIT Splunk Operation team to obtain tokens and samples, and verify the feasibility of using the HTTPS API interface for the application.
6. For Corp applications using the File Log interface, please contact NNIT Splunk Operation team to obtain FTP account and password, and ensure that logs are correctly transmitted to the File Log server.
7. For applications using DB Connection and Azure Event Hub, it should be confirmed that the logs have been properly stored.

# Appendix 2. Application Log Integration Process

Application Log Management Process:

1. The system manager must confirm that the application meets the prerequisites outlined in "Appendix 1. Application Log Integration Prerequisite".
2. The system manager or delegate should complete "Appendix 3. Application Log Integration Request Template" and submit it to NNIT via NNITSupport@novonordisk.com.
3. The NNIT Service Manager will contact the system manager within 8 hours, discuss system requirements, and assess related costs (including one-time and operational fees) and negotiate business terms.
   1. During this period, NNIT will inform the system manager of the necessary operations based on the submitted application's log access interface requirements, such as applying for FTP accounts or HTTPs API tokens, and verifying whether the application's storage in DB or Azure Event Hub meets the requirements.
   2. The application must prepare the logs according to the requirements of the different interfaces.
4. The application submits a purchase order (PO) to NNIT.
5. Once the application logs are prepared and NNIT receives the PO, the NNIT Splunk Operation team collaborates with the application team to debug log imports, configure log alerts and reports, and completes this process within 5 working days of PO receipt. (Within 5 working days, NNIT can handle a maximum of 5 requests in parallel. If there are more than 5 requests, NNIT will inform the system manager and prioritize the requests based on a first-come, first-served principle, adding a new request only after the completion of the previous one.)
6. After the configuration is completed, NNIT will notify the system manager via email. Upon the system manager's confirmation via email, NNIT will issue an invoice to the system manager.

# Appendix 3. Application Log Integration Request Template

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| **提示信息 | Information** | | | | | |
| 此邮件用于NNSH Splunk平台的应用日志接入申请，作为一个Service Request，NNIT提供工作日5\*8的支持服务，KPI: 收到PO后5天。  申请方式：请填写下面表格信息，并发送邮件到NNITSupport@novonordisk.com，NNIT Service Manager及NNSH Splunk平台运维工程师会和您联系，您也可以先和NNIT服务交付人员联系，在核实相关信息后再进行填写后发送给NNIT。 | | | | | |
| NNSH Splunk 应用日志接入申请模板 | | | | | |
| 序号 No. | 描述 Description | 请填写 Please fill in the fields below | | | 备注 Comments |
| 1 | Requestor Initial： | <举例：WZZL> | | | Requestor的NN Initial |
| 2 | ServiceNow BA(Business Application)： | <举例：GITO Splunk platform> | | | ServiceNow中注册的BA名称 |
| 3 | BA ServiceNow ID: | <举例：11111> | | | ServiceNow中注册的BA ID号 |
| 4 | IT Solution Owner： | <举例：TAOX> | | | 系统Owner的Initial |
| 5 | IT Solution Manager： | <举例：WZZL> | | | 系统经理的Initial |
| 6 | Application solution tech contact： | <举例：LPNL> | | | 比如Application Manager或者应用的技术负责人 |
| 7 | 应用日志传输方式： | <举例：DB Connection> | | | 4种传输类型（根据应用实际情况如有需要可多选）： 1. HTTPs API 2. DB Connection 3. File log（CSV/JSON格式） 4. Azure.cn Event Hub  其中域内网应用可以使用HTTPs API或File log两种方式 |
| 8 | Alert及触发Alert的逻辑： | Alert | Alert逻辑 | Alert频率 | 1.Alert:是指您所期望设置的告警行为，比如“Login Failed” 2.Alert逻辑：是指同一个事件发生几次后触发一个Alert，比如“Login Failed”事件发生五次触发一次告警 3.Alert频率：是指针对某一事件的检测周期，检测周期默认每15分钟一次，您可以根据需要定制检测的时间，比如30分钟，1小时，2小时等 |
| 9 | <举例：Login failed> | <举例：发生五次触发一次告警> | <举例：15分钟一次> |
| 10 |  |  |  |
| 11 |  |  |  |
| 12 |  |  |  |
| 13 |  |  |  |
| 14 |  |  |  |
| 15 | Alert接收人的NN邮箱地址： | <举例：WZZL@novonordisk.com> <举例：LPNL@novonordisk.com> | | | Alert会通过邮件发送给接收人，请提供接收人的NN邮箱 |
| 16 | 报告内容及发送： | 报告内容 | 时间范围 | 发送周期 | 1.报告内容：所需报表内容：（比如:Admin账户登录/新增账户/数据条目总数等） 2.时间范围：是指所需报告的时间范围，默认为1个月，您可以根据需要定制比如: 24小时/1周/1月/1年等） 3.发送周期：是指所需报告定时发送的时间：默认每月发送一次，您可以根据需要定制发送周期，比如：24小时/1周/1月/1年等） |
| 17 | <举例：Admin账户登录> | <举例：1个月> | <举例：1个月一次> |
| 18 | <举例：新增账号> | <举例：1周> | <举例：1周一次> |
| 19 |  |  |  |
| 20 |  |  |  |
| 21 |  |  |  |
| 22 |  |  |  |
| 23 | 报告接收人的NN邮箱地址： | <举例：WZZL@novonordisk.com> <举例：LPNL@novonordisk.com> | | | 报告会通过邮件发送，请提供接收人的NN邮箱 |
| 24 | 日志保存周期： | <举例：3年> | | | 日志保存周期是指应用日志收集到Splunk中保留的时间，默认6个月，之后自动覆盖，您可以根据应用的实际需要定制保存周期比如1年，2年，3年，以及其他 |
| 25 | 其他信息： |  | | | 其他补充信息 |