# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import platform
import re
import socket
from copy import deepcopy

import mock
import pytest

from datadog_checks.tcp_check.tcp_check import AddrTuple, TCPCheck

from . import common

# from datadog_checks.tcp_check.utils import has_ipv6_connectivity


def test_down(aggregator):
    """
    Service expected to be down
    """
    instance = deepcopy(common.INSTANCE_KO)
    instance['collect_response_time'] = True
    check = TCPCheck(common.CHECK_NAME, {}, [instance])
    check.check(instance)
    expected_tags = ["instance:DownService", "target_host:127.0.0.1", "port:65530", "foo:bar", "address:127.0.0.1"]
    aggregator.assert_service_check('tcp.can_connect', status=check.CRITICAL, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=0, tags=expected_tags)
    aggregator.assert_metric('network.tcp.response_time', count=0)  # should not submit response time metric on failure
    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == 1


def test_reattempt_resolution_on_error():
    instance = deepcopy(common.INSTANCE)
    check = TCPCheck(common.CHECK_NAME, {}, [instance])
    check.check(instance)

    assert check.ip_cache_duration is None

    # IP is not normally re-resolved after the first check run
    with mock.patch.object(check, 'resolve_ips', wraps=check.resolve_ips) as resolve_ips:
        check.check(instance)
        assert not resolve_ips.called

    # Upon connection failure, cached resolved IP is cleared
    with mock.patch.object(check, 'connect', wraps=check.connect) as connect:
        connect.side_effect = lambda self, addr, socket_type: Exception()
        check.check(instance)
        assert check._addrs is None

    # On next check run IP is re-resolved
    with mock.patch.object(check, 'resolve_ips', wraps=check.resolve_ips) as resolve_ips:
        check.check(instance)
        assert resolve_ips.called


def test_reattempt_resolution_on_duration():
    instance = deepcopy(common.INSTANCE)
    instance['ip_cache_duration'] = 0
    check = TCPCheck(common.CHECK_NAME, {}, [instance])
    check.check(instance)

    assert check.ip_cache_duration is not None

    # ip_cache_duration = 0 means IP is re-resolved every check run
    with mock.patch.object(check, 'resolve_ips', wraps=check.resolve_ips) as resolve_ips:
        check.check(instance)
        assert resolve_ips.called
        check.check(instance)
        assert resolve_ips.called
        check.check(instance)
        assert resolve_ips.called


def test_up(aggregator, check):
    """
    Service expected to be up
    """
    check.check(deepcopy(common.INSTANCE))
    expected_tags = ["instance:UpService", "target_host:datadoghq.com", "port:80", "foo:bar"]
    expected_tags.append("address:{}".format(check._addrs[0].address))
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)
    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == 1


def test_response_time(aggregator):
    """
    Test the response time from a server expected to be up
    """
    instance = deepcopy(common.INSTANCE)
    instance['collect_response_time'] = True
    instance['name'] = 'instance:response_time'
    check = TCPCheck(common.CHECK_NAME, {}, [instance])
    check.check(instance)

    # service check
    expected_tags = ['foo:bar', 'target_host:datadoghq.com', 'port:80', 'instance:instance:response_time']
    expected_tags.append("address:{}".format(check._addrs[0].address))
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)

    # response time metric
    expected_tags = ['url:datadoghq.com:80', 'instance:instance:response_time', 'foo:bar']
    expected_tags.append("address:{}".format(check._addrs[0].address))
    aggregator.assert_metric('network.tcp.response_time', tags=expected_tags)
    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == 1


@pytest.mark.parametrize(
    'hostname, getaddrinfo, expected_addrs, multiple_ips, ipv6_conn, ipv4_only, ip_count',
    [
        pytest.param(
            'localhost',
            common.DUAL_STACK_GETADDRINFO_LOCALHOST_IPV6,
            [AddrTuple('::1', socket.AF_INET6)],
            False,
            True,
            False,
            1,
            id='Dual IPv4/IPv6: localhost, IPv6 resolution, multiple_ips False',
        ),
        pytest.param(
            'localhost',
            common.DUAL_STACK_GETADDRINFO_LOCALHOST_IPV4,
            [AddrTuple('127.0.0.1', socket.AF_INET)],
            False,
            True,
            False,
            1,
            id='Dual IPv4/IPv6: localhost, IPv4 resolution, multiple_ips False',
        ),
        pytest.param(
            'localhost',
            common.DUAL_STACK_GETADDRINFO_LOCALHOST_IPV6,
            [AddrTuple('::1', socket.AF_INET6), AddrTuple('127.0.0.1', socket.AF_INET)],
            True,
            True,
            False,
            2,
            id='Dual IPv4/IPv6: localhost, IPv6 resolution, multiple_ips True',
        ),
        pytest.param(
            'localhost',
            common.DUAL_STACK_GETADDRINFO_LOCALHOST_IPV4,
            [AddrTuple('127.0.0.1', socket.AF_INET), AddrTuple('::1', socket.AF_INET6)],
            True,
            True,
            False,
            2,
            id='Dual IPv4/IPv6: localhost, IPv4 resolution, multiple_ips True',
        ),
        pytest.param(
            'some-hostname',
            common.DUAL_STACK_GETADDRINFO_IPV4,
            [AddrTuple('ip1', socket.AF_INET)],
            False,
            True,
            False,
            1,
            id='Dual IPv4/IPv6: string hostname, IPv4 resolution, multiple_ips False',
        ),
        pytest.param(
            'another-hostname',
            common.DUAL_STACK_GETADDRINFO_IPV6,
            [AddrTuple('ip1', socket.AF_INET6)],
            False,
            True,
            False,
            1,
            id='Dual IPv4/IPv6: string hostname, IPv6 resolution, multiple_ips False',
        ),
        pytest.param(
            'some-hostname',
            common.DUAL_STACK_GETADDRINFO_IPV4,
            [
                AddrTuple('ip1', socket.AF_INET),
                AddrTuple('ip2', socket.AF_INET6),
                AddrTuple('ip3', socket.AF_INET6),
            ],
            True,
            True,
            False,
            3,
            id='Dual IPv4/IPv6: string hostname, IPv4 resolution, multiple_ips True',
        ),
        pytest.param(
            'another-hostname',
            common.DUAL_STACK_GETADDRINFO_IPV6,
            [
                AddrTuple('ip1', socket.AF_INET6),
                AddrTuple('ip2', socket.AF_INET),
                AddrTuple('ip3', socket.AF_INET6),
            ],
            True,
            True,
            False,
            3,
            id='Dual IPv4/IPv6: string hostname, IPv6 resolution, multiple_ips True',
        ),
        pytest.param(
            'localhost',
            common.SINGLE_STACK_GETADDRINFO_LOCALHOST_IPV4,
            [AddrTuple('127.0.0.1', socket.AF_INET)],
            False,
            True,
            False,
            1,
            id='Single stack IPv4: localhost, IPv4 resolution, multiple_ips False',
        ),
        pytest.param(
            'localhost',
            common.SINGLE_STACK_GETADDRINFO_LOCALHOST_IPV4,
            [AddrTuple('127.0.0.1', socket.AF_INET), AddrTuple('ip2', socket.AF_INET)],
            True,
            True,
            False,
            2,
            id='Single stack IPv4: localhost, IPv4 resolution, multiple_ips True',
        ),
        pytest.param(
            'another-hostname',
            common.SINGLE_STACK_GETADDRINFO_IPV4,
            [AddrTuple('ip1', socket.AF_INET)],
            False,
            True,
            False,
            1,
            id='Single stack IPv4: string hostname, IPv4 resolution, multiple_ips False',
        ),
        pytest.param(
            'another-hostname',
            common.SINGLE_STACK_GETADDRINFO_IPV4,
            [
                AddrTuple('ip1', socket.AF_INET),
                AddrTuple('ip2', socket.AF_INET),
                AddrTuple('ip3', socket.AF_INET),
            ],
            True,
            True,
            False,
            3,
            id='Single stack IPv4: string hostname, IPv4 resolution, multiple_ips True',
        ),
        pytest.param(
            'localhost',
            common.DUAL_STACK_GETADDRINFO_LOCALHOST_IPV4,
            [AddrTuple('127.0.0.1', socket.AF_INET)],
            False,
            False,
            False,
            1,
            id='Dual stack IPv4: localhost, IPv4 resolution, no ipv6 connectivity, multiple_ips False',
        ),
        pytest.param(
            'localhost',
            common.DUAL_STACK_GETADDRINFO_LOCALHOST_IPV6,
            [AddrTuple('127.0.0.1', socket.AF_INET)],
            True,
            False,
            False,
            1,
            id='Dual stack IPv4: localhost, IPv4 resolution, no ipv6 connectivity, multiple_ips True',
        ),
        pytest.param(
            'another-hostname',
            common.DUAL_STACK_GETADDRINFO_IPV4,
            [
                AddrTuple('ip1', socket.AF_INET),
            ],
            True,
            False,
            False,
            1,
            id='Dual stack IPv4: string hostname, IPv4 resolution, no ipv6 connectivity, multiple_ips True',
        ),
        pytest.param(
            'another-hostname',
            common.DUAL_STACK_GETADDRINFO_IPV6,
            [
                AddrTuple('ip2', socket.AF_INET),
            ],
            False,
            False,
            False,
            1,
            id='Dual stack IPv4: string hostname, IPv4 resolution, no ipv6 connectivity, multiple_ips False',
        ),
        pytest.param(
            'another-hostname',
            common.DUAL_STACK_GETADDRINFO_LOCALHOST_IPV4_ONLY,
            [AddrTuple('127.0.0.1', socket.AF_INET)],
            False,
            False,
            True,
            1,
            id='Dual stack IPv4: localhost, IPv4 resolution, no ipv6 connectivity, multiple_ips False, IPv4 only',
        ),
        pytest.param(
            'another-hostname',
            common.DUAL_STACK_GETADDRINFO_IPV4_ONLY,
            [AddrTuple('ip2', socket.AF_INET), AddrTuple('ip3', socket.AF_INET)],
            True,
            True,
            True,
            2,
            id='Dual stack IPv4: string hostname, IPv4 resolution, has ipv6 connectivity, multiple_ips True, IPv4 only',
        ),
    ],
)
def test_hostname_resolution(
    aggregator, monkeypatch, hostname, getaddrinfo, expected_addrs, multiple_ips, ipv6_conn, ipv4_only, ip_count
):
    """
    Test that string hostnames get resolved to ipv4 address format properly.
    """
    instance = deepcopy(common.INSTANCE)
    instance['host'] = hostname
    instance['multiple_ips'] = multiple_ips
    instance['ipv4_only'] = ipv4_only
    check = TCPCheck(common.CHECK_NAME, {}, [instance])

    monkeypatch.setattr('socket.getaddrinfo', mock.Mock(return_value=getaddrinfo))
    monkeypatch.setattr(check, 'has_ipv6_connectivity', mock.Mock(return_value=ipv6_conn))
    monkeypatch.setattr(
        'socket.gethostbyname_ex',
        mock.Mock(return_value=('localhost', [], [expected_addr.address for expected_addr in expected_addrs])),
    )
    monkeypatch.setattr(check, 'connect', mock.Mock())

    expected_tags = [
        "instance:UpService",
        "target_host:{}".format(hostname),
        "port:80",
        "foo:bar",
        "address:{}".format(expected_addrs[0].address),
    ]

    check.check(instance)

    assert check._addrs == expected_addrs
    assert check.connect.call_count == ip_count

    calls = [mock.call(address, socket_type) for address, socket_type in expected_addrs]
    check.connect.assert_has_calls(calls, any_order=True)

    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags, count=1)
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags, count=1)
    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == ip_count


def test_multiple(aggregator):
    """
    Test when a domain is attached to 3 IPs [UP, DOWN, UP]
    """
    instance = deepcopy(common.INSTANCE_MULTIPLE)
    instance['name'] = 'multiple'
    instance['ip_cache_duration'] = 0
    check = TCPCheck(common.CHECK_NAME, {}, [instance])

    with mock.patch(
        'socket.getaddrinfo',
        return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('ip1', 80)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('ip2', 80, 0, 0)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('ip3', 80, 0, 0)),
        ],
    ), mock.patch.object(check, 'connect', wraps=check.connect) as connect:
        connect.side_effect = [None, Exception(), None] * 2
        expected_tags = ['foo:bar', 'target_host:datadoghq.com', 'port:80', 'instance:multiple']

        # Running the check twice
        check.check(None)
        check.check(None)

        aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags + ['address:ip1'], count=2)
        aggregator.assert_metric('network.tcp.can_connect', value=0, tags=expected_tags + ['address:ip2'], count=2)
        aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags + ['address:ip3'], count=2)
        aggregator.assert_service_check('tcp.can_connect', status=check.OK, count=4)
        aggregator.assert_service_check('tcp.can_connect', status=check.CRITICAL, count=2)

    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == 6


def test_ipv6(aggregator, check):
    """
    Service expected to be up
    """
    instance = deepcopy(common.INSTANCE_IPV6)
    check = TCPCheck(common.CHECK_NAME, {}, [instance])
    check.check(instance)
    has_ipv6 = check.has_ipv6_connectivity()

    nb_ipv4, nb_ipv6 = 0, 0
    for addr in check.addrs:
        expected_tags = ["instance:UpService", "target_host:ip-ranges.datadoghq.com", "port:80", "foo:bar"]
        expected_tags.append("address:{}".format(addr.address))
        if re.match(r'^[0-9a-f:]+$', addr.address):
            nb_ipv6 += 1
            if has_ipv6:
                aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
                aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)
            elif platform.system() == 'Darwin':
                # IPv6 connectivity varies when running test locally on macOS, so we do not check status or metric value
                aggregator.assert_service_check('tcp.can_connect', tags=expected_tags)
                aggregator.assert_metric('network.tcp.can_connect', tags=expected_tags)
            else:
                aggregator.assert_service_check('tcp.can_connect', status=check.CRITICAL, tags=expected_tags)
                aggregator.assert_metric('network.tcp.can_connect', value=0, tags=expected_tags)
        else:
            nb_ipv4 += 1
            aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
            aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)
    assert nb_ipv4 == 4
    # The Windows CI machine doesn't return IPv6
    # Windows or MacOS might not have IPv6 connectivity when testing locally
    if has_ipv6 and platform.system() not in ('Windows', 'Darwin'):
        assert nb_ipv6 == 8
    if platform.system() == 'Linux':
        assert has_ipv6 is True

    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == nb_ipv4 + nb_ipv6


@pytest.mark.parametrize(
    'hostname, getaddrinfo, gethostbyname_ex, expected_result',
    [
        pytest.param(
            'localhost',
            [(socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('::ffff:127.0.0.1', 0, 0, 0))],
            ('localhost', [], ['127.0.0.1']),
            True,
            id="",
        ),
        pytest.param(
            'another-host',
            [(socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('fe80::1234:a56b:c789:d1e', 0, 0, 0))],
            ('linklocal-host', [], ['127.0.0.1']),
            False,
            id="",
        ),
        pytest.param(
            'hostname',
            [(socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('::ffff:127.0.0.1', 0, 0, 0))],
            ('hostname', [], ['127.0.0.1']),
            True,
            id="",
        ),
    ],
)
def test_has_ipv6_connectivity(monkeypatch, hostname, getaddrinfo, gethostbyname_ex, expected_result):
    instance = deepcopy(common.INSTANCE_IPV6)
    instance['hostname'] = hostname
    check = TCPCheck(common.CHECK_NAME, {}, [instance])
    monkeypatch.setattr('socket.gethostname', mock.Mock(return_value=hostname))
    monkeypatch.setattr('socket.gethostbyname_ex', mock.Mock(return_value=gethostbyname_ex))
    monkeypatch.setattr('socket.getaddrinfo', mock.Mock(return_value=getaddrinfo))

    has_ipv6 = check.has_ipv6_connectivity()

    assert has_ipv6 == expected_result
