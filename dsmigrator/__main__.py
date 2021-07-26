import sys

import click
import urllib3
import yaml

from dsmigrator.logging import console, log
from dsmigrator.api import WorkloadApi, DSMApi

from dsmigrator.workload_security_link import create_c1ws_link

# Welcome Banner
console.print(
    """\

              %###################,
          #############################
       ######################\\.         `#
     #################################,    \\
   #####################################     #
  #######################################     #
 ##############  ########################    .##
(##########(    ########################     ###(
#####(              ###################     #####
######(      ########################     (######
######       #######################      #######
 ####       ######################      #########
  ###       ###################      ###########
   #        ###############       (#############
    #         #######.         ###############&
      \\                   .#################
        %.          ######################
           \\###########################
               ###################
    """,
    style="bold red",
    overflow="crop",
)
console.print(
    "Welcome to the Trend Micro Policy Migration Tool",
    style="bold red",
)


# Init helpers


def validate_url(ctx, param, url: str) -> str:
    """
    Makes sure urls start with 'http' and end with a '/'

    Args:
        ctx: necessary for click
        param: necessary for click
        url (str): url string

    Raises:
        click.BadParameter: kicks the user out of the cli and lets them know
                            about the specific error

    Returns:
        str: a sanitized url
    """
    try:
        url = url.strip()
        assert url[0:4] == "http"
        if url[-1] != "/":
            url = url + "/"
        return url
    except:
        raise click.BadParameter(
            "DSM url must start with 'https://' or , please double-check input"
        )


def validate_api_keys(ctx, param, api_key):
    try:
        api_key = api_key.strip()
        last_equal = api_key[-1] == "="
        first_validation_bit = api_key.split("-")
        last_validation_bit = first_validation_bit[4].split(":")
        clean_list = [i for i in first_validation_bit[0:4]]
        clean_list.append(last_validation_bit[0])
        validate_list = [len(i) for i in clean_list]
        validate_list.append(last_equal)

        if validate_list == [8, 4, 4, 4, 12, True]:
            return api_key
        else:
            raise click.BadParameter(
                "Invalid API key format, please double-check the input."
            )
    except:
        raise click.BadParameter(
            "Invalid API key format, please double-check the input."
        )


# override the click invoke method


def CommandWithConfigFile(config_file_param_name):
    class CustomCommandClass(click.Command):
        def invoke(self, ctx):
            config_file = ctx.params[config_file_param_name]
            if config_file is not None:
                with open(config_file) as f:
                    config_data = yaml.safe_load(f)
                    for param, value in ctx.params.items():
                        if value is None and param in config_data:
                            ctx.params[param] = config_data[param]
                            ctx.params[param].prompt = None

            return super(CustomCommandClass, self).invoke(ctx)

    return CustomCommandClass


# pass options


@click.command(cls=CommandWithConfigFile("config_file"))
@click.option("--config-file", type=click.Path(), is_eager=True)
@click.option(
    "-ou",
    "--original-url",
    callback=validate_url,
    prompt="Old DSM address and port (e.g. https://10.10.10.10:4119/)",
    help="A resolvable FQDN for the old DSM, with port number (e.g. https://192.168.1.1:4119/)",
    envvar="ORIGINAL_URL",
)
@click.option(
    "-oa",
    "--original-api-key",
    callback=validate_api_keys,
    prompt="Old DSM API key",
    help="API key for the old DSM with Full Access permissions",
    envvar="ORIGINAL_API_KEY",
)
@click.option(
    "-nu",
    "--new-url",
    default="https://cloudone.trendmicro.com/",
    show_default=True,
    help="Destination url",
)
@click.option(
    "-coa",
    "--cloud-one-api-key",
    prompt="New Cloud One API key",
    help="API key for Cloud One Workload Security with Full Access permissions",
    envvar="CLOUD_ONE_API_KEY",
)
@click.option(
    "-d",
    "--delete-policies/--keep-policies",
    is_flag=True,
    default=False,
    prompt="Do you want to wipe existing policies in Cloud One? (not required, but will give best results)",
    help="Wipes existing policies in Cloud One (not required, but will give best results)",
)
@click.option(
    "-t",
    "--tasks",
    is_flag=True,
    help="(BETA) Enable the task migrator (may be buggy)",
)
@click.option(
    "-k",
    "--insecure",
    is_flag=True,
    help="Suppress the InsecureRequestWarning for self-signed certificates",
)
@click.option(
    "-f",
    "--filter",
    help="A list of policy names in form '[name, name, ...]' which are the only ones which will be transferred.",
)
# @click.option(
#     "-c",
#     "--cert",
#     default=False,
#     show_default=True,
#     help="(Optional) Allows the use of a cert file",
# )

# Main tool


def main(
    config_file,
    original_url,
    original_api_key,
    new_url,
    cloud_one_api_key,
    # cert,
    insecure,
    tasks,
    delete_policies,
    filter,
):
    """Moves your on-prem DS deployment to the cloud!"""
    OLD_API_KEY = original_api_key
    OLD_HOST = original_url
    NEW_API_KEY = cloud_one_api_key
    NEW_HOST = new_url

    ds_api = DSMApi(f"{OLD_HOST}/api", OLD_API_KEY, False)
    workload_api = WorkloadApi(f"{NEW_HOST}/api", NEW_API_KEY, False)

    if insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Double-check that creds will work
    console.rule("Validating Credentials")
    validation_result1 = ds_api.check_api_access()
    validation_result2 = workload_api.check_api_access()

    if validation_result1 and validation_result2:
        log.info("Successfully authenticated!")
    else:
        log.error("Something went wrong with authentication.")
        log.error(
            "Double-check that your api key is correct, active, and has 'Full Access' permissions."
        )
        log.error("Aborting...")
        sys.exit(0)

    if delete_policies:
        console.rule("Delete C1 Policies")
        # delete_cloud_one_policies(NEW_API_KEY)

    console.rule("Creating C1WS Link")
    create_c1ws_link(OLD_HOST, OLD_API_KEY, NEW_API_KEY)

    console.rule("Migrating Policies")


if __name__ == "__main__":
    try:
        main()  # pylint: disable=no-value-for-parameter
    except Exception:
        log.exception("Fatal error in main.")
