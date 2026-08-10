## URS-UAT Matrix
| [NNSH Splunk platform] URS-UAT Matrix | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 |
| --- | --- | --- | --- |
| NaN | NaN | NaN | NaN |
| URS No. | URS Description | Testing Cases | Test Results |
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
| URS-LA-003 | Splunk platform needs to support fuzzy keyword searches.\n Splunk platform needs to support the constructed presentation of logs. | TC-LA-003 | OK |
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
| URS-OR-003 | The NNSH Splunk platform needs to be available on 24 hours a day, 7 days a week.\nIncident and event related with the NNSH Splunk platform will be handled on 24 hours a day, 7 days a week.\nThe customer request will be handled on China Business Days, Monday through Friday 09:00 to 18:00 GMT+8. | TC-OR-003 | OK |
| URS-OR-004 | The system needs to establish a testing environment. The resources for the testing environment should be configured according to the minimum requirements. | TC-OR-004 | OK |
| URS-SR-001 | The audit trail is set up as default.\nSplunk system can generates audit trails, includes:\n1. Creation, change, and cancellation of access authorization\n2. Login success/failure, date/time of event and account\n3. Who performed the log operation action\n4. What was created/modified/deleted related with system management\nAudit trail records is preserved for 180 days. | TC-SR-001 | OK |
| URS-SR-002 | Admin users can delete logs which contain specific keyword and these activities will be logged. \nOnly admin user which was granted with "delete" privilege can delete the logs.\nNo data change can be performed. | TC-SR-002 | OK |
| URS-SR-003 | Logs can be exported by a specific ‘individual’ request, and these activities will be logged. | TC-SR-003 | OK |
| URS-SR-004 | Logs which include specific keyword can be temporarily excluded by a specific ‘individual’ request, and these activities will be logged. | TC-SR-004 | OK |
| URS-SR-005 | All log data must be transited in encryption by default. | TC-SR-005 | OK |
| URS-SR-006 | All log data must be stored in encryption by default. | TC-SR-006 | OK |
| URS-SR-007 | User account can be traced to individuals and no shared account is used. All accounts will be individual, and activities will be logged. | TC-SR-007 | OK |
| URS-SR-008 | The NNSH Splunk platform can define user roles based on the supported business process which following the principle of least privilege. | TC-SR-008 | OK |
| URS-SR-009 | The NNSH Splunk platform can Follow the principle of separation of duties, ensuring that responsibilities are separated between different users. | TC-SR-009 | OK |
| URS-SR-010 | The password policy can be set as:\ni. minimum password length: 14\nii. frequency or triggers for changing passwords:120 days \niii. User will be log off after inactive for 15 minutes. \niv. limits on invalid logon attempts:5 times\nv. locking of account after invalid logon attempts: 15 mins\nvi. reset newly issued passwords at first use.\nvii. token based authentication for application programming interfaces | TC-SR-010 | OK |
| URS-SR-011 | The management interface of the NNSH Splunk platform can only be accessed through the NNSH bastion host. | TC-SR-011 | OK |
| URS-SR-012 | The network of the NNSH Splunk platform is isolated network and controlled by PA firewall and NSG. | TC-SR-012 | OK |
| URS-SR-013 | The user logon session can be set as time out if not active for 15 minutes. | TC-SR-013 | OK |
| URS-SR-014 | All application log transfer activities that pass through the application log transfer interface must be recorded, including the time, source, and transfer result. The interface logs must be stored in a specific log repository and retained for 180 days. | TC-SR-014 | OK |
| URS-MR-001 | Breaking down the system into smaller, independent components that are easier to maintain. | TC-MR-001 | OK |
| URS-MR-002 | It is easy to improve the system processing capacity according to the log receiving capacity requirements. | TC-MR-002 | OK |
| NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN |
| Tested by: | NaN | Date: | NaN |
| NaN | Tester (1) | NaN | NaN |
| NaN | NaN | NaN | NaN |
| Reviewed by | NaN | Date: | NaN |
| NaN | System Manager (2) | NaN | NaN |
| NaN | NaN | NaN | NaN |
| Approved by: | NaN | Date: | NaN |
| NaN | System Owner (3) | NaN | NaN |
| NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN |
| (1) By signing this you agree that the test plan is appropriate and you have executed all test steps in test plan. | NaN | NaN | NaN |
| (2) By signing this you agree that the test plan is appropriate and you have reviewed the tests performed by tester and agree to the actual result and conclusion. | NaN | NaN | NaN |
| (3) By signing this you agree that the test plan is appropriate and you have reviewed the tests performed by tester and agree to the actual result. Meanwhile, you agree to release the change to production based on the tests performed. | NaN | NaN | NaN |

## TC-LC-001
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LC-001 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Open the Splunk platform login screen to log in | The UI should be displayed normally | The UI displays normally | TC-LC-001-CR1 | OK |
| NaN | 2 | Search for logs collected as by Splunk Agent in the search interface | Logs collected by Splunk Agent should be displayed | Logs collected by Splunk Agent are displayed normally | TC-LC-001-CR2 | OK |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LC-002
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LC-002 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Search for logs collected as by Azure Event Hub in the search interface | Logs collected by Azure Event Hub should be displayed | Logs collected by Azure Event Hub are displayed normally | TC-LC-002-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LC-003
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LC-003 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Search for firewall logs collected by port collection in the search interface | Firewall logs collected by port collection should be displayed | Firewall logs collected by port collection are displayed normally | TC-LC-003-CR1 | OK |
| NaN | 2 | Search for bastion logs collected by port collection in the search interface | Bastion logs collected by port collection should be displayed | Bastion logs collected by port collection are displayed normally | TC-LC-003-CR2 | OK |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LC-004
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LC-004 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Search for logs collected as by file collection in the search interface | Logs collected by file collection should be displayed | Logs collected by file collection are displayed normally | TC-LC-004-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LC-005
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LC-005 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Search for logs collected as by DB Connect in the search interface | Logs collected by DB Connect should be displayed | Logs collected by DB Connect are displayed normally | TC-LC-005-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LC-006
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LC-006 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Search for logs collected as by file collection in the search interface | Logs collected by file collection should be displayed | Logs collected by file collection are displayed normally | TC-LC-006-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LC-007
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LC-007 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Search for logs collected as by Http Api in the search interface | Logs collected by Http Api should be displayed | Logs collected by Http Api are displayed normally | TC-LC-007-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LC-008
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LC-008 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Search for logs collected as by Azure Event Hub in the search interface | Logs collected by Azure Event Hub should be displayed | Logs collected by Azure Event Hub are displayed normally | TC-LC-008-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LDS-001
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LDS-001 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Adjust parameters in the log storage configuration interface. | The Configuration Log Store UI should be displayed | The Configuration Log Store UI is displayed normally | TC-LDS-001-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LDS-002
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LDS-002 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Adjust parameters in the log storage configuration interface. | The Configuration Log Store UI should be displayed | The Configuration Log Store UI is displayed normally | TC-LDS-002-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LA-001
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LA-001 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Configure the field extraction method in the field extraction interface | The field extraction UI should be displayed | The field extraction UI is displayed normally | TC-LA-001-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LA-002
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LA-002 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Rename a field in the Field Rename interface | The field renaming UI should be displayed | The field renaming UI is displayed normally | TC-LA-002-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LA-003
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LA-003 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Calculate the required fields in the field calculation interface | The field calculation UI should be displayed | The field calculation UI is displayed normally | TC-LA-003-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LS-001
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LS-001 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Enter keywords in the search interface | Search results should be displayed | Search results are displayed normally | TC-LS-001-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LS-002
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LS-002 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Enter keywords in the search interface | Search results should be displayed in a structured way | Search results are displayed in a structured way | TC-LS-002-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-LS-003
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-LS-003 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Enter keywords in the search interface | Export search results function should be displayed | Export search results function is displayed normally | TC-LS-003-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-CA-001
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-CA-001 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Adding a new alert in alert editor | Alert editing function UI should be displayed | Alert editing function UI is displayed normally | TC-CA-001-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-CA-002
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-CA-002 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Adding email alert in alert editor | The email alert UI should be displayed | The email alert UI is displayed normally | TC-CA-002-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-CA-003
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-CA-003 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Check the license usage status on the Splunk platform. | The Licence Usage UI should be displayed | The Licence Usage UI is displayed normally | TC-CA-003-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-CA-004
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-CA-004 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Adding a new alert in alert editor | Alert editing function UI should be displayed | Alert editing function UI is displayed normally | TC-CA-004-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-CR-001
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-CR-001 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Adding new reports in Report Management | The report management UI should be displayed | The report management UI is displayed normally | TC-CR-001-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-CR-002
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-CR-002 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Designing calculation logic and storing results in report management | The report management UI should be displayed | The report management UI is displayed normally | TC-CR-002-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-CR-003
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-CR-003 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Adding new reports in Report Management | The report management UI should be displayed | The report management UI is displayed normally | TC-CR-003-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-CD-001
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-CD-001 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | View the required Dashboard | A designed Dashboard UI should be displayed | A designed Dashboard UI is displayed normally | TC-CD-001-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-CD-002
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-CD-002 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | View the required Dashboard | A designed Dashboard UI should be displayed | A designed Dashboard UI is displayed normally | TC-CD-002-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-CD-003
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-CD-003 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Configure relevant timed tasks in dashboard management | The dashboard management UI should be displayed | The dashboard management UI is displayed normally | TC-CD-003-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-CD-004
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-CD-004 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Creating a new Dashboard in the dashboard management | The dashboard management UI should be displayed | The dashboard management UI is displayed normally | TC-CD-004-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-PR-001
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-PR-001 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Open the License Usage View window, select to view the License usage for the past 60 days, and check if the daily received log volume is close to or exceeds 50GB. | There are instances where the received log volume is close to or exceeds 50GB per day. | There are 3 days where the received log volume is close to 50GB per day. | TC-PR-001-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-PR-002
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-PR-002 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Open the browser, bring up the developer tools, then visit the platform's login page and check the page load time. | The page load time is less than or equal to 3 seconds. | The page load time is less than 3 seconds. | TC-PR-002-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-PR-003
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-PR-003 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Use the CURL tool to connect to the NNSH Splunk platform's API interface. Add the -w parameter to test if the API response time is less than 1 second. | The NNSH Splunk platform's API response time is less than 1 second. | The NNSH Splunk platform's API response time is less than 1 second. | TC-PR-003-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-AR-001
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-AR-001 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Check the monitoring platform to find out if the NNSH Splunk platform's log receiving port has been added to the monitoring platform. | The platform's log receiving port has been added to the monitoring platform. | The platform's log receiving port has been added to the monitoring platform. | TC-AR-001-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-AR-002
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-AR-002 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Check if the platform's admin web management interface has been added to the monitoring platform. | The platform'sadmin web management interface has been added to the monitoring platform. | The platform's admin web management interface has been added to the monitoring platform. | TC-AR-002-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-AR-003
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-AR-003 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Check the frequency of the image backups generated by Microsoft Azure for the server of NNSH Splunk platform. | The image backups are generated by Microsoft Azure every day for the servers of NNSH Splunk platform. | The image backups are generated by Microsoft Azure every day for the servers of NNSH Splunk platform. | TC-AR-003-CR1 | OK |
| NaN | 2 | Check the retention period of the disk image backups to see if it is greater than or equal to 30 days. | The retention period for the platform's disk image backups is greater than or equal to 30 days. | The retention period for the platform's disk image backups is equal to 30 days. | TC-AR-003-CR1 | OK |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-OR-001
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-OR-001 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | In the SNOW platform of Novo Nordisk, searching for the keyword [Log Management], find tickets created for platform operations and maintenance. | Ticket of [Log Management] can be found on SNOW. | Ticket of [Log Management] is found on SNOW. | TC-OR-001-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-OR-002
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-OR-002 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | In the SNOW platform of Novo Nordisk, searching for the keyword [Azure China Splunk], find Change Request created for platform operations and maintenance. | Change Request of [Azure China Splunk] can be found on SNOW. | Change Request of [Azure China Splunk] is found on SNOW. | TC-OR-002-CR1 | OK |
| NaN | 2 | Open the NNIT CMDB platform and check if all servers of NNSH Splunk platform have been added to the CMDB and are subject to Change Management processes. | All servers of NNSH Splunk platform have been added to the NNIT CMDB. | All servers of NNSH Splunk platform have been added to the NNIT CMDB. | TC-OR-002-CR2 | OK |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-OR-003
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-OR-003 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Check the NNSH monitoring platform, to verify if all servers of the NNSH Splunk platform are integrated into the NNSH monitoring platform, to monitor performance metrics and other related parameters. | All servers on the platform are integrated into the NNSH monitoring platform | All servers on the platform are integrated into the NNSH monitoring platform | TC-OR-003-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-OR-004
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-OR-004 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Open the web management portal of the test environment. | The web management portal of the test environment is opened. | The web management portal of the test environment is opened. | TC-OR-004-CR1 | OK |
| NaN | 2 | After logging in, check if the installed components are similar to those in the production environment. | "The plugins are installed similarly to those in the production environment. | "The plugins are installed similarly to those in the production environment. | TC-OR-004-CR2 | OK |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-SR-001
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-SR-001 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Search the internal audit trail of the NNSH Splunk platform, to check if the required audit logs are recorded, such as:\n1. Creation, change, and cancellation of access authorization\n2. Login success/failure, date/time of event and account\n3. Who performed the log operation action\n4. What was created/modified/deleted related with system management | Required audit logs are searched out. | Required audit logs are searched out. | TC-SR-001-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-SR-002
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-SR-002 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Admin users which has been granted with "delete" priledge can add the delete command to the Search interface, so that the logs found can be deleted. | The logs which are searched out are deleted | The logs which are searched out are deleted | TC-SR-002-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-SR-003
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-SR-003 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | In the search interface, logs found using specific keywords can be exported. | The logs found using specific keywords are exported. | The logs found using specific keywords are exported. | TC-SR-003-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-SR-004
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-SR-004 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | In the search interface, use the NOT command to exclude specific keywords, so that the related logs are excluded from the search results. | Logs containing specific keyword are excluded from the search results. | Logs containing specific keyword are excluded from the search results. | TC-SR-004-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-SR-005
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-SR-005 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Use OpenSSL to verify the SSL encryption status of the server's log receiving port. | The command returns a message similar to the following with a good certificate:\nVerify return code: 0 (ok) | The command returns a message similar to the following with a good certificate:\nVerify return code: 0 (ok) | TC-SR-005-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-SR-006
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-SR-006 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Check if the server's disks are encrypted | All disks are encrypted by default using the Azure default encryption. | All disks are encrypted by default using the Azure default encryption. | TC-SR-006-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-SR-007
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-SR-007 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Open the user management interface, check the user account configurations, and ensure that all user accounts are associated with personal accounts. | All user accounts are associated with personal accounts. | All user accounts are associated with personal accounts. | TC-SR-007-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-SR-008
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-SR-008 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Open the user role definition interface on NNSH Splunk platform, and modify the permissions for specific user roles. | Permissions for specific user roles are modified. | Permissions for specific user roles are modified. | TC-SR-008-CR1 | OK |
| NaN | 2 |  | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-SR-009
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-SR-009 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Open the user permissions definition interface in Splunk to see if different user roles have been assigned to different users. | Different user roles have been assigned to different users. | Different user roles have been assigned to different users. | TC-SR-009-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-SR-0010
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-SR-010 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Open the password policy configuration interface on NNSH Splunk platform to check if password rules are set follow requirements as below:\ni. minimum password length: 15 \nii. frequency or triggers for changing passwords: 24\niii. limits on invalid logon attempts: 5\niv. locking of account after 5 invalid logon attempts in 5 minutes, and locking for 15 minutes | Password rules are set follow requirements | Password rules are set follow requirements | TC-SR-010-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-SR-0011
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-SR-011 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Access the NNSH Splunk platform through the NNSH bastion host. | NNSH Splunk platform can be accessed through the NNSH bastion host. | NNSH Splunk platform can be accessed through the NNSH bastion host. | TC-SR-011-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-SR-012
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-SR-012 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Inspect the Splunk network configuration on Azure China cloud, check if a separate network is configged for the servers, and be protected by a NSG (Network Security Group). | The servers are deployed in a separate network , and be protected by a NSG (Network Security Group). | The servers are deployed in a separate network , and be protected by a NSG (Network Security Group). | TC-SR-012-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-SR-013
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-SR-013 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Open the Splunk web management interface and check if the login session timeout has been configured to 15 minutes. | Session timeout is configured to 15 minutes. | Session timeout is configured to 15 minutes. | TC-SR-013-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-SR-014
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-SR-014 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Search for interface logs within the system's internal log library, you can find logs of the log interface transmissions. | Logs of the log interface transmissions can be found. | Logs of the log interface transmissions can be found. | TC-SR-014-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-MR-001
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-MR-001 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Check the system architecture to find out if the servers are deployed by roles. This will determine if the number of servers in each role can be increased or decreased based on requirements. | All servers are deployed by roles. | All servers are deployed by roles. | TC-MR-001-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |

## TC-MR-002
| NNSH Splunk platform | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| Testing Case No.: | NaN | TC-MR-002 | NaN | NaN | NaN | NaN |
| System Name: | NaN | NNSH Splunk platform | NaN | NaN | NaN | NaN |
| Date: | NaN | 2024-10-29 00:00:00 | NaN | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| No. | Step | Input/Action | Expected Result(s) | Actual Result(s)/Enclosure(s) | Screenshot No | Conclusion |
| 1 | 1 | Check the server's resource configuration to determine if capacity of NNSH Splunk platform can be increased by adjusting the server resource setting. | The server resource setting can be adjusted. | The server resource setting can be adjusted. | TC-MR-002-CR1 | OK |
| NaN | 2 | NaN | NaN | NaN | NaN | NaN |
| Note1: \nConclusion, "OK" means the testing case has been performed successfully, "Not OK" means the testing case has been performed fail. | NaN | NaN | NaN | NaN | NaN | NaN |