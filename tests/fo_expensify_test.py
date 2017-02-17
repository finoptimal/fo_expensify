#!/usr/bin/env python

import argparse, datetime, json, pytz, time
import fo_expensify

parser = argparse.ArgumentParser()

parser.add_argument("-e", "--employee_data_path", 
                    type=str,
                    default="",
                    help="path to .csv file of employees to update?")

parser.add_argument("-i", "--partnerUserID", 
                    type=str,
                    default="",
                    help="Credential: partnerUserID")

parser.add_argument("-l", "--get_policy_list", 
                    action="store_true",
                    default=False,
                    help="List all policies accessible with these creds.")

parser.add_argument("-p", "--policyIDs", 
                    type=str,
                    nargs="*",
                    default=[],
                    help="Which policy are we dealing with?")

parser.add_argument("-s", "--partnerUserSecret", 
                    type=str,
                    default="",
                    help="Credential: partnerUserSecret")

parser.add_argument("-v", "--verbosity", 
                    type=int,
                    default=0,
                    help="Debugging functionality")

if __name__=='__main__':
    start = time.time()
    args = parser.parse_args()

    creds = {
        "partnerUserID"     : args.partnerUserID,
        "partnerUserSecret" : args.partnerUserSecret,
    }

    if args.employee_data_path:
        response_json = fo_expensify.update_employees(
            args.policyIDs[0], args.employee_data_path,
            troubleshoot=args.troubleshoot, verbosity=args.verbosity, **creds)

    if args.get_policy_list:
        response_json = fo_expensify.get_policy_list(
            verbosity=args.verbosity, **creds)

    if len(args.policyIDs) > 1:
        response_json = fo_expensify.get_policies(
            policy_ids=args.policyIDs,
            verbosity=args.verbosity, **creds)
        
    end = time.time()

    if args.verbosity > 0:
        print "Running time: {:.2f} seconds.".format(end-start)
        if args.verbosity > 5:
            import ipdb;ipdb.set_trace()
