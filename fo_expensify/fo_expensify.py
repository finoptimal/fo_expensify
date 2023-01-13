"""
Wrapper around this REST API:

https://integrations.expensify.com/Integration-Server/doc/

Copyright 2017-2022 FinOptimal, Inc. All rights reserved.
"""
import json
import re
import requests
import time

from finoptimal.logging import get_file_logger

api_logger = get_file_logger('api/expensify')

URL = "https://integrations.expensify.com/Integration-Server/ExpensifyIntegrations"

MAX_TRIES = 3
DEFAULT_JSON_TEMPLATE = """
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


def post(data, files=None, timeout=60):
    resp = requests.post(url=URL, data=data, files=files, timeout=timeout)

    api_logger.info(f"{resp.__hash__()} - {resp.status_code} {resp.reason} - "
                    f"{resp.request.method.ljust(4)} {resp.url}")
    return resp


def retry(max_tries=3, delay_secs=1):
    """
    Produces a decorator which tries effectively the function it decorates
     a given number of times. This is meant to (considerately) address
     occassional, transient unexpected behavior by the Expensify API.
    """

    def decorator(retriable_function):
        def inner(*args, **kwargs):
            """
            Retries retriable_function max_tries times, waiting delay_secs
             between tries (and increasing delay_secs geometrically by the
             drag_factor). escape can be set to true during a run to get out
             immediately if, e.g. ipdb is running.
            """
            tries = kwargs.get("tries", max_tries)
            delay = kwargs.get("delay", delay_secs)

            attempts = 0

            while True:
                try:
                    return retriable_function(*args, **kwargs)
                except:
                    tries -= 1
                    attempts += 1

                    if tries <= 0:
                        # raise Exception(f"Failing after {attempts} tries!")
                        raise
                    # back off as failures accumulate in case it's transient
                    time.sleep(delay * attempts)

        return inner

    return decorator


@retry()
def export_and_download_reports(
        report_states=None, limit=None, report_ids=None, policy_ids=None,
        start_date=None, end_date=None, approved_after=None,
        export_mark_filter=None, export_mark=None,
        file_base_name="fo_exp_", file_extension="json", download_path=None,
        template=None, clear_bad_escapes=True, verbosity=0, **credentials):
    """
    https://integrations.expensify.com/Integration-Server/doc/#report-exporter

    returns a file name you pass to the downloader endpoint to get the file
    """
    rjd = {
        "type": "file",
        "credentials": credentials,
        "onReceive": {
            "immediateResponse": ["returnRandomFileName"]
        },
        "inputSettings": {
            "type": "combinedReportData", "filters": {}
        },
        "outputSettings": {
            "fileExtension": file_extension.replace(".", "")
        }
    }

    if report_states:
        if isinstance(report_states, str):
            report_states = report_states.split(",")
        rjd["inputSettings"]["reportState"] = ",".join(report_states)

    if limit:
        rjd["inputSettings"]["limit"] = limit

    if start_date:
        rjd["inputSettings"]["filters"]["startDate"] = str(start_date)
    elif not report_ids:
        raise Exception("Need either a start date or a list of report IDs!")

    if end_date:
        rjd["inputSettings"]["filters"]["endDate"] = str(end_date)

    if approved_after:
        rjd["inputSettings"]["filters"]["approvedAfter"] = str(approved_after)

    if report_ids:
        if isinstance(report_ids, str):
            report_ids = report_ids.split(",")
        elif isinstance(report_ids, (float, int)):
            # i.e. just a single report
            report_ids = [ report_ids ]

        rjd["inputSettings"]["filters"]["reportIDList"] = ",".join(report_ids)

    if policy_ids:
        if isinstance(policy_ids, str):
            policy_ids = policy_ids.split(",")

        rjd["inputSettings"]["filters"]["policyIDList"] = ",".join(policy_ids)

    if export_mark_filter:
        rjd["inputSettings"]["filters"]["markedAsExported"] = export_mark_filter

    if export_mark:
        # This wrapper doesn't support emailing yet...
        rjd["onFinish"] = [
            {
                "actionName": "markAsExported",
                "label": export_mark
            }
        ]

    if file_base_name:
        rjd["outputSettings"]["fileBasename"] = file_base_name

    if not template:
        template = DEFAULT_JSON_TEMPLATE

    data = {
        "requestJobDescription": json.dumps(rjd, indent=4),
        "template": template
    }

    # Verbose Job Description / JSON Dict?
    vjd = rjd.copy()
    del (vjd["credentials"])
    dumped_vjd = json.dumps(vjd, indent=4)

    if verbosity > 2:
        print("Expensify JobDescription (sans creds):")
        print(dumped_vjd)

    # Start Time
    st = time.time()
    resp = post(data=data, timeout=240)
    # Call Time
    ct = time.time() - st

    if verbosity > 6:
        print(resp.text)

    if verbosity > 2:
        print(f"Expensify {rjd['inputSettings']['type']} {rjd['type']} call response status code: "
              f"{resp.status_code} ({ct:,.0f} seconds)")

    if resp.text[0] == "{" and resp.json().get("responseCode") == 500:
        msg = "\n\n".join([dumped_vjd, resp.text])
        raise Exception(msg)

    rjd2 = {
        "type": "download",
        "credentials": credentials,
        "fileName": resp.text
    }

    data2 = {
        "requestJobDescription": json.dumps(rjd2, indent=4)
    }

    if verbosity > 2:
        print("Expensify JobDescription (sans creds):")
        vjd2 = rjd2.copy()
        del (vjd2["credentials"])
        print(json.dumps(vjd2, indent=4))

    # Start Time
    st = time.time()
    resp2 = post(data=data2, timeout=240)
    # Call Time
    ct = time.time() - st

    if file_extension.replace(".", "").lower() == "pdf":
        # Just save and return the path
        destination_handle = open(download_path, 'wb')
        with open(download_path, 'wb') as destination_handle:
            destination_handle.write(resp2.content)

        return download_path

    else:
        # This is a JSON response, then...
        if clear_bad_escapes:
            # Expensify uses colons as tag delimimters. If there's a colon in
            #  the tag name, it "escapes" them with a backslash. That backslash,
            #  which makes for invalid json because it's not actually escaping
            #  anything, will blow up json.loads, so it needs to get gone.
            # We don't turn \: into just :, though, because then a downstream
            #  process can't tell if it's supposed to be a delimiter or a
            #  literal colon. Instead, we make it something that a downstream
            #  process is VERY unlikely to mistake for anything but a colon...
            colon_cleansed_rj = re.sub(r"\\\\*:", "|||||", resp2.text)
            # colon_cleansed_rj = resp2.text.replace("\\:", "|||||") #65403
            rj = json.loads(colon_cleansed_rj)

        else:
            rj = resp2.json()

    if verbosity > 2:
        if verbosity > 8:
            print(json.dumps(rj, indent=4))

        print(f"Expensify {rjd2['type']} call response status code: {resp2.status_code} ({ct:,.0f} seconds)")

        if verbosity > 10:
            print("Inspect resp2.text, rj:")
            import ipdb
            ipdb.set_trace()

    return rj


# @retry()
def export_and_download_reconciliation(
        domain, start_date, end_date,
        reconciliation_type="Unreported", asynchronous=False,
        file_base_name="fo_exp_", file_extension="json",
        download_path=None, template=None, clear_bad_escapes=True,
        verbosity=0, **credentials):
    """
    https://integrations.expensify.com/Integration-Server/doc/#report-exporter

    returns a file name you pass to the downloader endpoint to get the file
    """
    rjd = {
        "type": "reconciliation",
        "credentials": credentials,
        "inputSettings": {
            "type": reconciliation_type,
            "async": asynchronous,
            "startDate": str(start_date),
            "endDate": str(end_date),
            "domain": domain,
            "feed": "export_all_feeds",
        },
        "outputSettings": {
            "fileExtension": file_extension.lstrip(".")
        },
    }

    if not template:
        # TODO: broken reference to DEFAULT_REC_CSV_TEMPLATE here...
        if not file_extension.lstrip(".") == "csv":
            raise NotImplementedError(file_extension)

        template = DEFAULT_REC_CSV_TEMPLATE

    data = {
        "requestJobDescription": json.dumps(rjd, indent=4),
        "template": template
    }

    # Verbose Job Description / JSON Dict?
    vjd = rjd.copy()
    del (vjd["credentials"])
    dumped_vjd = json.dumps(vjd, indent=4)

    if verbosity > 2:
        print("Expensify JobDescription (sans creds):")
        print(dumped_vjd)

    # Start Time
    st = time.time()
    resp = post(data=data, timeout=240)
    # Call Time
    ct = time.time() - st

    if verbosity > 7:
        print(resp.text)
        import ipdb
        ipdb.set_trace()

    if verbosity > 2:
        print(f"Expensify {rjd['inputSettings']['type']} {rjd['type']} call response status code:"
              f" {resp.status_code} ({ct:,.0f} seconds)")

    if resp.text[0] == "{" and resp.json().get("responseCode") == 500:
        msg = "\n\n".join([dumped_vjd, resp.text])
        raise Exception(msg)

    rjd2 = {
        "type": "download",
        "credentials": credentials,
        "fileName": resp.json()["filename"],
        "fileSystem": "reconciliation"
    }

    data2 = {
        "requestJobDescription": json.dumps(rjd2, indent=4)
    }

    if verbosity > 2:
        print("Expensify JobDescription (sans creds):")
        vjd2 = rjd2.copy()
        del (vjd2["credentials"])
        print(json.dumps(vjd2, indent=4))

    # Start Time
    st = time.time()
    resp2 = post(data=data2, timeout=240)

    if verbosity > 8:
        print(resp2)
        import ipdb
        ipdb.set_trace()

    # Call Time
    ct = time.time() - st

    if file_extension.replace(".", "").lower() == "pdf":
        # Just save and return the path
        with open(download_path, 'wb') as destination_handle:
            destination_handle.write(resp2.content)

        return download_path

    else:
        rj = resp2.json()

    if verbosity > 2:
        if verbosity > 6:
            print(json.dumps(rj, indent=4))
            import ipdb
            ipdb.set_trace()

        print(f"Expensify {rjd2['type']} call response status code: {resp2.status_code} ({ct:,.0f} seconds)")

        if verbosity > 10:
            print("Inspect resp2.text, rj:")
            import ipdb
            ipdb.set_trace()

    return rj


@retry()
def get_policies(policy_ids=None, user_email=None,
                 verbosity=0, **credentials):
    """
    https://integrations.expensify.com/Integration-Server/doc/#policy-getter
    """
    if isinstance(policy_ids, str):
        policy_ids = policy_ids.split(",")
    elif not policy_ids:
        policy_ids = []

    # requestJobDescription
    rjd = {
        "type": "get",
        "credentials": credentials,
        "inputSettings": {
            "type": "policy",
            "fields": ["categories", "reportFields", "tags", "tax"],
            "policyIDList": policy_ids
        }
    }

    if user_email:
        rjd["inputSettings"]["userEmail"] = user_email

    data = {
        "requestJobDescription": json.dumps(rjd, indent=4)
    }

    # Verbose Job Description / JSON Dict?
    vjd = rjd.copy()
    del (vjd["credentials"])
    dumped_vjd = json.dumps(vjd, indent=4)

    if verbosity > 2:
        print("Expensify JobDescription (sans creds):")
        print(dumped_vjd)

    # Start Time
    st = time.time()
    resp = post(data=data, timeout=240)
    # Call Time
    ct = time.time() - st

    if verbosity > 2:
        print(f"Expensify {rjd['inputSettings']['type']} {rjd['type']} call response status code: "
              f"{resp.status_code} ({ct:,.0f} seconds)")

        if verbosity > 6:
            print(json.dumps(resp.json(), indent=4))

    return resp.json()


@retry()
def get_policy_list(admin_only=True, user_email=None, verbosity=0,
                    **credentials):
    """
    https://integrations.expensify.com/Integration-Server/doc/
     #policy-list-getter
    """
    # requestJobDescription
    rjd = {
        "type": "get",
        "credentials": credentials,
        "inputSettings": {
            "type": "policyList",
            "adminOnly": admin_only}}

    if user_email:
        rjd["inputSettings"]["userEmail"] = user_email

    # Verbose Job Description / JSON Dict?
    vjd = rjd.copy()
    del vjd["credentials"]
    dumped_vjd = json.dumps(vjd, indent=4)

    if verbosity > 2:
        print("Expensify JobDescription (sans creds):")
        print(dumped_vjd)

    data = {"requestJobDescription": json.dumps(rjd, indent=4)}

    # Occasionally there are transient API problems that a tinsure of time
    #  will sufficiently wait out.
    times_tried = 0

    # Start Time
    st = time.time()
    resp = post(data=data, timeout=60)
    # Call Time
    ct = time.time() - st

    if not resp.status_code == 200 or "policyList" not in resp.json():
        msg = "\n\n".join([f"policyList getter failure ({resp.status_code}):", resp.text])

        if verbosity > 3:
            print(msg)

        raise Exception(msg)

    if verbosity > 2:
        print(f"Expensify {rjd['inputSettings']['type']} {rjd['type']} call response status code: {resp.status_code} "
              f"({ct:,.0f} seconds)")

        if verbosity > 5:
            print(json.dumps(resp.json(), indent=4))

    return resp.json()


@retry()
def update_employees(policy_id, data_path, verbosity=0, **credentials):
    """
    https://integrations.expensify.com/Integration-Server/doc/#employee-updater
    """
    # requestJobDescription
    rjd = {
        "type": "update",
        "credentials": credentials.copy(),
        "inputSettings": {
            "type": "employees",
            "policyID": policy_id,
            "fileType": "csv"
        }
    }

    data = {
        "requestJobDescription": json.dumps(rjd, indent=4),
    }

    files = {
        "data": ("employees.csv", open(data_path, "r")),
    }

    # Start Time
    st = time.time()
    resp = post(data=data, files=files, timeout=60)
    # Call Time
    ct = time.time() - st

    if verbosity > 2:
        print(f"Expensify {rjd['inputSettings']['type']} {rjd['type']} call response status code: {resp.status_code} "
              f"({ct:,.0f} seconds)")

        if verbosity > 3:
            print(json.dumps(resp.json(), indent=4))

    return resp.json()


@retry()
def update_policy(policy_id, categories=None, tags=None,
                  default_action="replace", verbosity=0, **credentials):
    """
    https://integrations.expensify.com/Integration-Server/doc/#policy-updater

    categories AND/OR tags must be a json-serializable dictionary as per
     the API documentation.
    """
    if not categories and not tags:
        raise Exception("Need to update a least one of categories or tags!")

    # requestJobDescription
    rjd = {
        "type": "update",
        "credentials": credentials.copy(),
        "inputSettings": {
            "type": "policy",
            "policyID": policy_id
        }
    }

    if categories:
        if not "action" in categories:
            categories["action"] = default_action

        rjd["categories"] = categories

    if tags:
        if tags.get("source") == "file":
            raise NotImplementedError("Implement dependent-level tag updates!")
        elif "source" not in tags:
            tags["source"] = "inline"

        if "action" not in tags:
            tags["action"] = default_action

        rjd["tags"] = tags

    data = {
        "requestJobDescription": json.dumps(rjd, indent=4),
    }

    # Start Time
    st = time.time()
    resp = post(data=data, timeout=60)
    # Call Time
    ct = time.time() - st

    if not resp.status_code == 200:
        raise Exception(resp.text)

    rj = resp.json()

    if len(rj.keys()) > 1 or not rj == {"responseCode": 200}:
        if verbosity > 2:
            print(json.dumps(rj, indent=4))
        raise Exception(rj)

    if verbosity > 2:
        print(f"Expensify {rjd['inputSettings']['type']} {rjd['type']} call response status code: {resp.status_code} "
              f"({ct:,.0f} seconds)")

        if verbosity > 5:
            print(json.dumps(resp.json(), indent=4))

            if verbosity > 10:
                print("Inspect resp:")
                import ipdb
                ipdb.set_trace()

    return resp.json()


@retry()
def set_report_status(report_ids, status="REIMBURSED", verbosity=0,
                      **credentials):
    """
    Currently REIMBURSED is the only thing you can set a report's status to:

    https://integrations.expensify.com/Integration-Server/doc/
     #report-status-updater    
    """
    if not isinstance(report_ids, (list, tuple)):
        report_ids = str(report_ids).split(",")

    data = {
        "requestJobDescription": json.dumps({
            "type": "update",
            "credentials": credentials.copy(),
            "inputSettings": {
                "type": "reportStatus",
                "status": "REIMBURSED",
                "filters": {
                    "reportIDList": ",".join(report_ids)
                }
            }
        }, indent=4)
    }

    # Start Time
    st = time.time()
    resp = post(data=data, timeout=60)
    # Call Time
    ct = time.time() - st

    rj = resp.json()

    if "skippedReports" in rj:
        skipped_reports = rj["skippedReports"]
        print("The following reports were NOT updated:")

        for skip_dict in skipped_reports:
            print(skip_dict['reportID'], "-", skip_dict['reason'])

    if verbosity > 2:
        print("Expensify report-status-updater call status",
              f"code: {resp.status_code} ({ct:,.0f} seconds)")

    return rj
