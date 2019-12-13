#!/usr/bin/env python

import argparse, datetime, json, pytz, time
import fo_expensify

parser = argparse.ArgumentParser()

parser.add_argument("-a", "--approved_after", 
                    type=str,
                    default=None,
                    help="yyyy-mm-dd for export filtering")

parser.add_argument("-b", "--file_base_name", 
                    type=str,
                    default="fo_exp",
                    help="What comes before the extension?")

parser.add_argument("-d", "--export_and_download", 
                    action="store_true",
                    default=False,
                    help="Export AND download.")

parser.add_argument("-e", "--employee_data_path", 
                    type=str,
                    default="",
                    help="path to .csv file of employees to update?")

parser.add_argument("-f", "--start_date", 
                    type=str,
                    default=None,
                    help="yyyy-mm-dd for export filtering (f for from)")

parser.add_argument("-g", "--get_policies", 
                    action="store_true",
                    default=False,
                    help="Get policy details (to be used with -p).")

parser.add_argument("-i", "--partner_user_id", 
                    type=str,
                    default="",
                    help="Credential: partnerUserID")

parser.add_argument("-l", "--get_policy_list", 
                    action="store_true",
                    default=False,
                    help="List all policies accessible with these creds.")

parser.add_argument("-L", "--limit", 
                    type=int,
                    default=None,
                    help="Limit to how many REPORTS (not expenses)?.")

parser.add_argument("-m", "--export_mark", 
                    type=str,
                    default="",
                    help="how to mark newly-exported reports?")

parser.add_argument("-M", "--export_mark_filter", 
                    type=str,
                    default="",
                    help="what prior export marks to exclude?")

parser.add_argument("-p", "--policy_ids", 
                    type=str,
                    nargs="*",
                    default=[],
                    help="Which policy are we dealing with?")

parser.add_argument("-ri", "--report_ids",
                    nargs="*",
                    type=str,
                    default="",
                    help="Export filter: specific reports?")

parser.add_argument("-rs", "--report_states",
                    nargs="*",
                    type=str,
                    default="",
                    help="Export filter: SUBMITTED, APPROVED, etc.")

parser.add_argument("-s", "--partner_user_secret", 
                    type=str,
                    default="",
                    help="Credential: partnerUserSecret")

parser.add_argument("-t", "--end_date", 
                    type=str,
                    default=None,
                    help="yyyy-mm-dd for export filtering (t for to)")

parser.add_argument("-v", "--verbosity", 
                    type=int,
                    default=0,
                    help="Debugging functionality")

parser.add_argument("-x", "--file_extension", 
                    type=str,
                    default="json",
                    help="What kind of download?")

if __name__=='__main__':
    start = time.time()
    args = parser.parse_args()

    creds = {
        "partnerUserID"     : args.partner_user_id,
        "partnerUserSecret" : args.partner_user_secret,
    }

    if args.employee_data_path:
        response_json = fo_expensify.update_employees(
            args.policy_ids[0], args.employee_data_path,
            verbosity=args.verbosity, **creds)

    if args.get_policy_list:
        response_json = fo_expensify.get_policy_list(
            verbosity=args.verbosity, **creds)

    if args.get_policies and len(args.policy_ids) > 0:
        response_json = fo_expensify.get_policies(
            policy_ids=args.policy_ids,
            verbosity=args.verbosity, **creds)

    if args.export_and_download:
        response_json = fo_expensify.export_and_download(
            report_state=args.report_states, limit=args.limit,
            report_ids=args.report_ids, policy_ids=args.policy_ids,
            start_date=args.start_date, end_date=args.end_date,
            approved_after=args.approved_after,
            export_mark_filter=args.export_mark_filter,
            export_mark=args.export_mark, file_base_name=args.file_base_name,
            file_extension=args.file_extension,
            verbosity=args.verbosity, **creds)
                    
    end = time.time()

    if args.verbosity > 0:
        print("Running time: {:.2f} seconds.".format(end-start))
        if args.verbosity > 5:
            import ipdb;ipdb.set_trace()
