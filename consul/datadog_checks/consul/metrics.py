# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
METRIC_MAP = {
    'consul_client_rpc': 'client.rpc',
    'consul_client_rpc_failed': 'client.rpc.failed',
    'consul_memberlist_degraded': 'memberlist.degraded',
    'consul_memberlist_gossip': 'memberlist.gossip',
    'consul_memberlist_health_score': 'memberlist.health.score',
    'consul_memberlist_msg_alive': 'memberlist.msg.alive',
    'consul_memberlist_msg_dead': 'memberlist.msg.dead',
    'consul_memberlist_msg_suspect': 'memberlist.msg.suspect',
    'consul_memberlist_probeNode': 'memberlist.probenode',
    'consul_memberlist_pushPullNode': 'memberlist.pushpullnode',
    'consul_memberlist_tcp_accept': 'memberlist.tcp.accept',
    'consul_memberlist_tcp_connect': 'memberlist.tcp.connect',
    'consul_memberlist_tcp_sent': 'memberlist.tcp.sent',
    'consul_memberlist_udp_received': 'memberlist.udp.received',
    'consul_memberlist_udp_sent': 'memberlist.udp.sent',
    'consul_raft_state_leader': 'raft.state.leader',
    'consul_raft_state_candidate': 'raft.state.candidate',
    'consul_raft_state_apply': 'raft.apply',
    'consul_raft_commitTime': 'raft.commitTime',
    'consul_raft_leader_dispatchLog': 'raft.leader.dispatchLog',
    'consul_raft_leader_lastContact': 'raft.leader.lastContact',
    'consul_runtime_gc_pause_ns': 'runtime.gc_pause_ns',
    'consul_serf_events': 'serf.events',
    'consul_serf_coordinate_adjustment_ms': 'serf.coordinate.adjustment_ms',
    'consul_serf_member_flap': 'serf.member.flap',
    'consul_serf_member_join': 'serf.member.join',
    'consul_serf_member_update': 'serf.member.update',
    'consul_serf_member_left': 'serf.member.left',
    'consul_serf_member_failed': 'serf.member.failed',
    'consul_serf_msgs_received': 'serf.msgs.received',
    'consul_serf_msgs_sent': 'serf.msgs.sent',
    'consul_serf_queue_Event': 'serf.queue.event',
    'consul_serf_queue_Intent': 'serf.queue.intent',
    'consul_serf_queue_Query': 'serf.queue.query',
    'consul_serf_snapshot_appendline': 'serf.snapshot.appendLine',
    'consul_serf_snapshot_compact': 'serf.snapshot.compact',
    # Available since 1.9.0
    'consul_api_http': 'http.request',
    'consul_raft_replication_installSnapshot': 'raft.replication.installSnapshot',
    'consul_raft_replication_heartbeat': 'raft.replication.heartbeat',
    'consul_raft_replication_appendEntries_rpc': 'raft.replication.appendEntries.rpc',
    'consul_raft_replication_appendEntries_logs': 'raft.replication.appendEntries.logs',
}
