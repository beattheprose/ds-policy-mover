import json

import requests
import urllib3
from deepsecurity.rest import ApiException
from nested_lookup import nested_lookup, nested_update

from dsmigrator.api_config import (
    ApplicationTypesApiInstance,
    IntrusionPreventionApiInstance,
)
from dsmigrator.migrator_utils import (
    validate_create,
    validate_create_dict,
    validate_create_dict_custom,
)

cert = False


def ips_rules_transform(
    allofpolicy,
    t1portlistid,
    t2portlistid,
    t1scheduleid,
    t2scheduleid,
    t1contextid,
    t2contextid,
    OLD_HOST,
    OLD_API_KEY,
    NEW_HOST,
    NEW_API_KEY,
):
    og_ipsruleid_dict = IPSGet(allofpolicy)
    og_ipsappid_dict = IPSappGet(allofpolicy)

    ipsappid_dict, ipscustomapp_dict = IPSappDescribe(
        og_ipsappid_dict,
        t1portlistid,
        t2portlistid,
        OLD_HOST,
        NEW_HOST,
        OLD_API_KEY,
        NEW_API_KEY,
    )

    ipsruleid_dict, ipscustomrule_dict = IPSDescribe(
        og_ipsruleid_dict,
        t1scheduleid,
        t2scheduleid,
        t1contextid,
        t2contextid,
        OLD_HOST,
        OLD_API_KEY,
        NEW_HOST,
        NEW_API_KEY,
    )

    aop_replace_ips_rules = IPSReplace(allofpolicy, ipsruleid_dict, ipscustomrule_dict)
    aop_replace_ips_apps = IPSappReplace(
        aop_replace_ips_rules, ipsappid_dict, ipscustomapp_dict
    )
    final = aop_replace_ips_apps
    return final


def IPSappGet(allofpolicy):
    # Takes in allofpolicy and creates a skeleton id dict
    ipsappid = []
    for describe in allofpolicy:
        namejson = json.loads(describe)
        if "applicationTypeIDs" in namejson["intrusionPrevention"]:
            for assigned_app_id in namejson["intrusionPrevention"][
                "applicationTypeIDs"
            ]:
                ipsappid.append(assigned_app_id)
    ipsappid_dict = dict.fromkeys(ipsappid)
    print("IPS application types in Tenant 1:", flush=True)
    print(ipsappid, flush=True)
    return ipsappid_dict


def IPSappDescribe(
    ipsappid_dict,
    t1portlistid,
    t2portlistid,
    url_link_final,
    url_link_final_2,
    tenant1key,
    tenant2key,
):
    allipsapp = []
    allipsappname = []
    allipscustomapp = []
    ipsapp_api_instance = ApplicationTypesApiInstance(tenant2key)

    print("Searching IPS application types in Tenant 1...", flush=True)
    if ipsappid_dict:
        for count, name in enumerate(list(ipsappid_dict.keys())):
            payload = {}
            url = url_link_final + "api/applicationtypes/" + str(name)
            headers = {
                "api-secret-key": tenant1key,
                "api-version": "v1",
                "Content-Type": "application/json",
            }
            response = requests.request(
                "GET", url, headers=headers, data=payload, verify=cert
            )
            describe = str(response.text)
            try:
                ipsappjson = json.loads(describe)
                allipsappname.append(str(ipsappjson["name"]))
                print(
                    "#"
                    + str(count)
                    + " IPS Application Type name: "
                    + str(ipsappjson["name"]),
                    flush=True,
                )
                old_port_list_id = ipsappjson.get("portListID")
                if old_port_list_id is not None:
                    indexnum = t1portlistid.index(str(old_port_list_id))
                    ipsappjson["portListID"] = t2portlistid[indexnum]
                allipsapp.append(json.dumps(ipsappjson))
                print(
                    "#" + str(count) + " IPS Application Type ID: " + name, flush=True
                )
            except:
                print(describe)
    print("Done!", flush=True)
    print("Searching and Modifying IPS application types in Tenant 2...", flush=True)
    # add printing to this
    ipsappid_dict, allipscustomapp = validate_create_dict_custom(
        allipsapp, ipsappid_dict, ipsapp_api_instance, "IPS Application Type"
    )
    if allipscustomapp:
        ipscustomapp_dict = validate_create_dict(
            allipscustomapp, ipsapp_api_instance, "IPS Custom App"
        )
    else:
        ipscustomapp_dict = {}
    print("Done!", flush=True)
    return ipsappid_dict, ipscustomapp_dict


def IPSappReplace(allofpolicy, ipsappid_dict, ipscustomapp_dict):
    for count, policy in enumerate(allofpolicy):
        policyjson = json.loads(policy)
        if "applicationTypeIDs" in policyjson["intrusionPrevention"]:
            all_ipsapp_ids_list = policyjson["intrusionPrevention"][
                "applicationTypeIDs"
            ]
            for index, ipsapp_id in enumerate(all_ipsapp_ids_list):
                new_ipsapp_id = ipsappid_dict.get(ipsapp_id)
                new_ipscustomapp_id = ipscustomapp_dict.get(ipsapp_id)
                if new_ipsapp_id is not None:
                    all_ipsapp_ids_list[index] = new_ipsapp_id
                elif new_ipscustomapp_id is not None:
                    all_ipsapp_ids_list[index] = new_ipscustomapp_id
        allofpolicy[count] = json.dumps(policyjson)
    return allofpolicy


def IPSGet(allofpolicy):
    # Takes in allofpolicy and creates a skeleton id dict
    ipsruleid = []
    for describe in allofpolicy:
        namejson = json.loads(describe)
        if "ruleIDs" in namejson["intrusionPrevention"]:
            for assigned_rule_id in namejson["intrusionPrevention"]["ruleIDs"]:
                ipsruleid.append(assigned_rule_id)
    ipsruleid_dict = dict.fromkeys(ipsruleid)
    print("IPS rules in Tenant 1:", flush=True)
    print(ipsruleid, flush=True)
    return ipsruleid_dict


def IPSDescribe(
    ipsruleid_dict,
    t1scheduleid,
    t2scheduleid,
    t1contextid,
    t2contextid,
    url_link_final,
    tenant1key,
    url_link_final_2,
    tenant2key,
):
    allipsrule = []
    allipsrulename = []
    ipsrule_api_instance = IntrusionPreventionApiInstance(tenant2key)
    print("Searching IPS rules in Tenant 1...", flush=True)

    if ipsruleid_dict:
        for count, dirlist in enumerate(list(ipsruleid_dict.keys())):
            payload = {}
            url = url_link_final + "api/intrusionpreventionrules/" + str(dirlist)
            headers = {
                "api-secret-key": tenant1key,
                "api-version": "v1",
                "Content-Type": "application/json",
            }
            response = requests.request(
                "GET", url, headers=headers, data=payload, verify=cert
            )
            describe = str(response.text)
            try:
                ipsjson = json.loads(describe)
                allipsrulename.append(str(ipsjson["name"]))
                print(
                    "#" + str(count) + " IPS Rule name: " + str(ipsjson["name"]),
                    flush=True,
                )
                if "scheduleID" in ipsjson:
                    indexnum = t1scheduleid.index(str(ipsjson["scheduleID"]))
                    ipsjson["scheduleID"] = t2scheduleid[indexnum]
                if "contextID" in ipsjson:
                    indexnum = t1contextid.index(str(ipsjson["contextID"]))
                    ipsjson["contextID"] = t2contextid[indexnum]

                print("#" + str(count) + " IPS Rule ID: " + describe, flush=True)
                allipsrule.append(json.dumps(ipsjson))
            except:
                print(describe)

    print("Done!", flush=True)
    print("Searching and Modifying IPS rule in Tenant 2...", flush=True)
    ipsruleid_dict, allipscustomrule = validate_create_dict_custom(
        allipsrule, ipsruleid_dict, ipsrule_api_instance, "IPS Rule"
    )
    if allipscustomrule:
        ipscustomrule_dict = validate_create_dict(
            allipscustomrule, ipsrule_api_instance, "IPS Custom Rule"
        )
    else:
        ipscustomrule_dict = {}
    print("Done!", flush=True)
    return ipsruleid_dict, ipscustomrule_dict


def IPSReplace(allofpolicy, ipsruleid_dict, ipscustomrule_dict):
    for count, policy in enumerate(allofpolicy):
        policyjson = json.loads(policy)
        if "ruleIDs" in policyjson["intrusionPrevention"]:
            all_ips_rule_ids_list = policyjson["intrusionPrevention"]["ruleIDs"]
            for index, ipsrule_id in enumerate(all_ips_rule_ids_list):
                new_ipsrule_id = ipsruleid_dict.get(ipsrule_id)
                new_ipscustomrule_id = ipscustomrule_dict.get(ipsrule_id)
                if new_ipsrule_id is not None:
                    all_ips_rule_ids_list[index] = new_ipsrule_id
                elif new_ipscustomrule_id is not None:
                    all_ips_rule_ids_list[index] = new_ipscustomrule_id
        allofpolicy[count] = json.dumps(policyjson)
    return allofpolicy
