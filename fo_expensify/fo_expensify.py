"""
Wrapper around this REST API:

https://integrations.expensify.com/Integration-Server/doc/

Copyright 2017 FinOptimal. All rights reserved.
"""

import json, requests

URL = "https://integrations.expensify.com/Integration-Server/" + \
      "ExpensifyIntegrations"

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

