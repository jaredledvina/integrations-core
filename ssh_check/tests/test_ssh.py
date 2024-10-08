# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading
from collections import namedtuple
from copy import deepcopy

import paramiko
import pytest
from mock import MagicMock, call, create_autospec

from datadog_checks.ssh_check import CheckSSH

from . import common

pytestmark = pytest.mark.unit


def test_ssh(aggregator):
    check = CheckSSH('ssh_check', {}, [common.INSTANCES['main']])

    nb_threads = threading.active_count()

    check.check(common.INSTANCES['main'])

    for sc in aggregator.service_checks(CheckSSH.SSH_SERVICE_CHECK_NAME):
        assert sc.status == CheckSSH.OK
        for tag in sc.tags:
            assert tag in ('instance:io.netgarage.org-22', 'optional:tag1')

    # Check that we've closed all connections, if not we're leaking threads
    common.wait_for_threads()
    assert nb_threads == threading.active_count()


def test_ssh_bad_config(aggregator):

    nb_threads = threading.active_count()

    with pytest.raises(Exception):
        check = CheckSSH('ssh_check', {}, [common.INSTANCES['bad_auth']])
        check.check(common.INSTANCES['bad_auth'])

    with pytest.raises(Exception):
        check = CheckSSH('ssh_check', {}, [common.INSTANCES['bad_hostname']])
        check.check(common.INSTANCES['bad_hostname'])

    for sc in aggregator.service_checks(CheckSSH.SSH_SERVICE_CHECK_NAME):
        assert sc.status == CheckSSH.CRITICAL

    # Check that we've closed all connections, if not we're leaking threads
    common.wait_for_threads()
    assert nb_threads == threading.active_count()


@pytest.mark.parametrize(
    'version, metadata',
    [
        (
            'OpenSSH_for_Windows_7.7p1, LibreSSL 2.6.5',
            {
                'version.major': '7',
                'version.minor': '7',
                'version.release': 'p1',
                'version.scheme': 'ssh_check',
                'version.raw': 'OpenSSH_for_Windows_7.7p1, LibreSSL 2.6.5',
                'flavor': 'OpenSSH',
            },
        ),
        (
            'SSH-2.0-OpenSSH_8.1',
            {
                'version.major': '8',
                'version.minor': '1',
                'version.scheme': 'ssh_check',
                'version.raw': 'SSH-2.0-OpenSSH_8.1',
                'flavor': 'OpenSSH',
            },
        ),
        (
            'SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u2',
            {
                'version.major': '7',
                'version.minor': '4',
                'version.release': 'p1',
                'version.scheme': 'ssh_check',
                'version.raw': 'SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u2',
                'flavor': 'OpenSSH',
            },
        ),
    ],
)
def test_collect_metadata(version, metadata, datadog_agent):
    client = MagicMock()
    client.get_transport = MagicMock(return_value=namedtuple('Transport', ['remote_version'])(version))

    ssh = CheckSSH('ssh_check', {}, [common.INSTANCES['main']])
    ssh.check_id = 'test:123'
    ssh._collect_metadata(client)
    datadog_agent.assert_metadata('test:123', metadata)


def test_collect_bad_metadata(datadog_agent):
    client = MagicMock()
    client.get_transport = MagicMock(return_value=namedtuple('Transport', ['remote_version'])('Cannot parse this'))

    ssh = CheckSSH('ssh_check', {}, [common.INSTANCES['main']])
    ssh.check_id = 'test:123'
    ssh._collect_metadata(client)
    datadog_agent.assert_metadata_count(1)
    datadog_agent.assert_metadata('test:123', {'flavor': 'unknown'})


def _setup_check_with_mock_client(settings, connect_mock_result):
    client = create_autospec(paramiko.SSHClient)
    client.connect.side_effect = [connect_mock_result]
    client.get_transport.return_value = namedtuple('Transport', ['remote_version'])('SSH-2.0-OpenSSH_8.1')

    inst = deepcopy(common.INSTANCES['main'])
    inst.update(settings)

    ssh = CheckSSH('ssh_check', {}, [inst])
    ssh.initialize_client = MagicMock(return_value=client)

    return client, ssh


@pytest.mark.parametrize(
    'settings',
    [
        pytest.param({}, id='implicitly'),
        pytest.param({'force_sha1': False}, id='explicitly'),
    ],
)
def test_force_sha1_disabled(aggregator, dd_run_check, settings):
    client, ssh = _setup_check_with_mock_client(settings, paramiko.ssh_exception.AuthenticationException)

    with pytest.raises(Exception, match='AuthenticationException'):
        dd_run_check(ssh)

    aggregator.assert_service_check(CheckSSH.SSH_SERVICE_CHECK_NAME, CheckSSH.CRITICAL)
    assert client.connect.mock_calls == [
        call(
            ssh.instance['host'],
            port=ssh.instance['port'],
            username=ssh.instance['username'],
            password=ssh.instance['password'],
        )
    ]


def test_force_sha1_enabled(aggregator, dd_run_check):
    client, ssh = _setup_check_with_mock_client({'force_sha1': True}, None)

    dd_run_check(ssh)

    aggregator.assert_service_check(CheckSSH.SSH_SERVICE_CHECK_NAME, CheckSSH.OK)
    assert client.connect.mock_calls == [
        call(
            ssh.instance['host'],
            port=ssh.instance['port'],
            username=ssh.instance['username'],
            password=ssh.instance['password'],
            disabled_algorithms={'pubkeys': ['rsa-sha2-512', 'rsa-sha2-256']},
        ),
    ]
