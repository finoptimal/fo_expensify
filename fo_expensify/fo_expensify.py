"""
Wrapper around this REST API:

https://integrations.expensify.com/Integration-Server/doc/

Copyright 2017 FinOptimal. All rights reserved.
"""

import json, requests

URL = "https://integrations.expensify.com/Integration-Server/" + \
      "ExpensifyIntegrations"

DEFAULT_TEMPLATE = """
[
    <#list reports as report>
        <#list report.transactionList as expense>
    {
        "Merchant"      : "${expense.merchant}",
        "Amount"        : ${expense.amount},
        "Category"      : "${expense.category}",
        "ReportID"      : "${report.reportID}",
        "TransactionId" : "${expense.transactionID}"
    }<#if expense?has_next>,<#else><#if report?has_next>,</#if></#if>
        <#assign expenseNumber = expenseNumber + 1>
        </#list>
    <#assign reportNumber = reportNumber + 1>
    </#list>
]
"""

def export_and_download(report_states=None, limit=None,
                        report_ids=None, policy_ids=None,
                        start_date=None, end_date=None, approved_after=None,
                        export_mark_filter=None, export_mark=None,
                        file_base_name="fo_exp", file_extension="json",
                        template=None,
                        verbosity=0, **credentials):
    """
    https://integrations.expensify.com/Integration-Server/doc/#report-exporter

    returns a file name you pass to the downloader endpoint to get the file
    """
    rjd = {
        "type"           : "file",
        "credentials"    : credentials,
        "onReceive"      : {"immediateResponse" : ["returnRandomFileName"]},
        "inputSettings"  : {"type" : "combinedReportData", "filters" : {}},
        "outputSettings" : {"fileExtension" : file_extension}}

    if report_states:
        if isinstance(report_states, (str, unicode)):
            report_states                   = report_states.split(",")
        rjd["inputSettings"]["reportState"] = ",".join(report_states)

    if limit:
        rjd["inputSettings"]["limit"]       = limit

    if start_date:
        rjd["inputSettings"]["filters"]["startDate"]     = str(start_date)
    elif not report_ids:
        raise Exception("Need either a start date or a list of report IDs!")
    
    if end_date:
        rjd["inputSettings"]["filters"]["endDate"]       = str(end_date)
        
    if approved_after:
        rjd["inputSettings"]["filters"]["approvedAfter"] = str(approved_after)

    if report_ids:
        if isinstance(report_ids, (str, unicode)):
            report_ids = report_ids.split(",")
        rjd["inputSettings"]["filters"]["reportIDList"] = ",".join(report_ids)
            
    if policy_ids:
        if isinstance(policy_ids, (str, unicode)):
            policy_ids = policy_ids.split(",")
        rjd["inputSettings"]["filters"]["policyIDList"] = ",".join(policy_ids)

    if export_mark_filter:
        rjd["inputSettings"]["filters"]["markedAsExported"] = export_mark_filter

    if export_mark:
        # This wrapper doesn't support emailing yet...
        rjd["onFinish"] = [
            {"actionName" : "markAsExported",
             "label"      : "FinOptimal Expensify API Wrapper Export"}]

    if file_base_name:
        rjd["outputSettings"]["fileBasename"] = file_base_name

    if not template:
        template = DEFAULT_TEMPLATE

    data = {"requestJobDescription" : json.dumps(rjd, indent=4),
            "template"              : template}
        
    resp = requests.post(URL, data=data)

    if verbosity > 1:
        print "Expensify {} {} call response status code: {}".format(
            rjd["inputSettings"]["type"], rjd["type"], resp.status_code) 
        if verbosity > 3:
            print resp.text

    rjd2 = {"type"        : "download",
            "credentials" : credentials,
            "fileName"    : resp.text}

    data2 = {"requestJobDescription" : json.dumps(rjd2, indent=4)}
    
    resp2 = requests.post(URL, data=data2)

    if verbosity > 1:
        print "Expensify {} call response status code: {}".format(
            rjd2["type"], resp2.status_code) 
        if verbosity > 3:
            print resp2.json()

    return resp2.json()

def get_policies(policy_ids=None, user_email=None,
                 verbosity=0, **credentials):
    """
    https://integrations.expensify.com/Integration-Server/doc/#policy-getter
    """
    if isinstance(policy_ids, (str, unicode)):
        policy_ids = policy_ids.split(",")
    elif not policy_ids:
        policy_ids = []
        
    # requestJobDescription
    rjd = {
        "type"          : "get",
        "credentials"   : credentials,
        "inputSettings" : {
            "type"         : "policy",
            "fields"       : ["categories", "reportFields", "tags", "tax"],
            "policyIDList" : policy_ids}}
        
    if user_email:
        rdj["inputSettings"]["userEmail"] = user_email

    data = {"requestJobDescription" : json.dumps(rjd, indent=4)}

    resp = requests.post(URL, data=data)

    if verbosity > 1:
        print "Expensify {} {} call response status code: {}".format(
            rjd["inputSettings"]["type"], rjd["type"], resp.status_code) 
        if verbosity > 3:
            print json.dumps(resp.json(), indent=4)
    
    return resp.json()    

def get_policy_list(admin_only=True, user_email=None, verbosity=0,
                    **credentials):
    """
    https://integrations.expensify.com/Integration-Server/doc/
     #policy-list-getter
    """
    # requestJobDescription
    rjd = {
        "type"          : "get",
        "credentials"   : credentials,
        "inputSettings" : {
            "type"      : "policyList",
            "adminOnly" : admin_only}}

    if user_email:
        rdj["inputSettings"]["userEmail"] = user_email

    data = {"requestJobDescription" : json.dumps(rjd, indent=4)}

    resp = requests.post(URL, data=data)

    if verbosity > 1:
        print "Expensify {} {} call response status code: {}".format(
            rjd["inputSettings"]["type"], rjd["type"], resp.status_code) 
        if verbosity > 3:
            print json.dumps(resp.json(), indent=4)
    
    return resp.json()    

def update_employees(policy_id, data_path, verbosity=0, **credentials):
    """
    https://integrations.expensify.com/Integration-Server/doc/#employee-updater
    """
    # requestJobDescription
    rjd = {
        "type"          : "update",
        "credentials"   : credentials.copy(),
        "inputSettings" : {
            "type"     : "employees",
            "policyID" : policy_id,
            "fileType" : "csv"}}

    data  = {
        "requestJobDescription" : json.dumps(rjd, indent=4),}
    files = {
        "data" : ("employees.csv", open(data_path, "r")),}
    
    resp = requests.post(URL, data=data, files=files)

    if verbosity > 1:
        print "Expensify {} {} call response status code: {}".format(
            rjd["inputSettings"]["type"], rjd["type"], resp.status_code) 
        if verbosity > 3:
            print json.dumps(resp.json(), indent=4)
    
    return resp.json()    

