# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# This file is autogenerated.
# To change this file you should edit assets/configuration/spec.yaml and then run the following commands:
#     ddev -x validate config -s <INTEGRATION_NAME>
#     ddev -x validate models -s <INTEGRATION_NAME>


def instance_connection_load_balance():
    return False


def instance_disable_generic_tags():
    return False


def instance_empty_default_hostname():
    return False


def instance_min_collection_interval():
    return 15


def instance_only_custom_queries():
    return False


def instance_port():
    return 5433


def instance_server():
    return 'localhost'


def instance_timeout():
    return 10


def instance_tls_validate_hostname():
    return True


def instance_tls_verify():
    return True


def instance_use_global_custom_queries():
    return 'true'


def instance_use_tls():
    return False
