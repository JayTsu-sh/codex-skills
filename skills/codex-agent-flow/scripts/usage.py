#!/usr/bin/env python3
"""Summarize Codex token_usage_record telemetry for one session and its descendants.

No guessed prices, cumulative-total summation, or legacy-format fallback.
"""
import argparse
from collections import Counter, defaultdict
import datetime as dt
import json
import os
from pathlib import Path

FIELDS = ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
          'output_tokens', 'reasoning_output_tokens', 'total_tokens')


def timestamp(value):
    result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamps must include a timezone')
    return result


def events(path, warnings):
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            try:
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError('Expected object')
                yield event
            except (ValueError, TypeError):
                warnings['malformed_json_lines'] += 1


def summarize(root, session, since=None, until=None):
    warnings, metas, paths = Counter(), {}, {}
    for path in sorted(root.rglob('*.jsonl')):
        # Forked files may embed their parent's metadata later. Only the first is owner.
        for event in events(path, warnings):
            if event.get('type') == 'session_meta':
                meta = event.get('payload', {})
                if meta.get('id'):
                    metas[meta['id']] = meta
                    paths.setdefault(meta['id'], []).append(path)
                break
            break
    if session not in metas:
        raise ValueError('Session not found; use its full ID and correct --sessions-dir')
    selected = {session}
    while True:
        before = len(selected)
        for sid, meta in metas.items():
            source = meta.get('source', {})
            subagent = source.get('subagent', {}) if isinstance(source, dict) else {}
            spawn = subagent.get('thread_spawn', {}) if isinstance(subagent, dict) else {}
            if not isinstance(spawn, dict):
                continue
            # A manual fork is not a child agent of this task.
            if spawn.get('parent_thread_id') in selected:
                selected.add(sid)
        if len(selected) == before:
            break
    records, calls, contexts = {}, {}, {}
    duplicates = 0
    for sid in sorted(selected):
        for path in paths[sid]:
            for event in events(path, warnings):
                payload = event.get('payload', {})
                typ = event.get('type')
                if typ == 'turn_context':
                    contexts[payload.get('turn_id')] = payload
                if typ == 'response_item' and payload.get('type') in ('function_call', 'custom_tool_call'):
                    calls[payload.get('call_id')] = event
                if typ != 'token_usage_record' or payload.get('thread_id') not in selected:
                    continue
                when = timestamp(event['timestamp'])
                if (since and when < since) or (until and when >= until):
                    continue
                rid = payload.get('response_id')
                if not rid:
                    raise ValueError('Usage record lacks response_id; cannot safely deduplicate')
                if rid in records:
                    if records[rid]['payload']['usage'] != payload['usage']:
                        raise ValueError('Conflicting usage for response ID ' + rid)
                    duplicates += 1
                else:
                    records[rid] = event
    if not records:
        raise ValueError('No token_usage_record data in this selection; unsupported format or empty interval')
    totals, by_thread, models = Counter(), defaultdict(Counter), Counter()
    turns, times, observed_threads = set(), [], set()
    for event in records.values():
        payload = event['payload']
        usage = payload['usage']
        if any(key not in usage for key in ('input_tokens', 'cached_input_tokens', 'output_tokens')):
            raise ValueError('Usage lacks required input/cache/output fields')
        if any(not isinstance(v, int) or v < 0 for k, v in usage.items() if k in FIELDS):
            raise ValueError('Invalid token count')
        if usage['cached_input_tokens'] > usage['input_tokens']:
            raise ValueError('Cached input exceeds input; schema needs review')
        if usage.get('reasoning_output_tokens', 0) > usage['output_tokens']:
            raise ValueError('Reasoning output exceeds output; schema needs review')
        values = {k: usage.get(k, 0) for k in FIELDS}
        values['total_tokens'] = usage['input_tokens'] + usage['output_tokens']
        if 'total_tokens' in usage and usage['total_tokens'] != values['total_tokens']:
            raise ValueError('Total differs from input + output; schema needs review')
        for optional in ('reasoning_output_tokens', 'cache_write_input_tokens'):
            if optional not in usage:
                warnings['missing_' + optional] += 1
        totals.update(values)
        by_thread[payload['thread_id']].update(values)
        observed_threads.add(payload['thread_id'])
        turns.add(payload.get('turn_id'))
        times.append(timestamp(event['timestamp']))
        context = contexts.get(payload.get('turn_id'), {})
        effort = context.get('effort') or context.get('collaboration_mode', {}).get('settings', {}).get('reasoning_effort', 'unknown')
        models[str(context.get('model', 'unknown')) + '/' + str(effort)] += 1
    for sid in selected - observed_threads:
        warnings['selected_threads_without_usage'] += 1
    tool_calls = 0
    for event in calls.values():
        p = event['payload']
        turn = p.get('internal_chat_message_metadata_passthrough', {}).get('turn_id')
        when = timestamp(event['timestamp'])
        if turn in turns and not (since and when < since) and not (until and when >= until):
            tool_calls += 1
    totals['uncached_input_tokens'] = totals['input_tokens'] - totals['cached_input_tokens']
    totals['non_reasoning_output_tokens'] = totals['output_tokens'] - totals['reasoning_output_tokens']
    return dict(schema_version=1, root_session=session, sessions=sorted(selected),
                interval=dict(since=since.isoformat() if since else None,
                              until=until.isoformat() if until else None),
                responses=len(records), deduplicated_copies=duplicates,
                tool_calls_with_matching_turn=tool_calls, usage=dict(totals),
                by_thread={k: dict(v) for k, v in by_thread.items()},
                responses_by_model_effort=dict(models), warnings=dict(warnings),
                first_response=min(times).isoformat(), last_response=max(times).isoformat(),
                response_span_seconds=(max(times) - min(times)).total_seconds(),
                average_input_tokens=round(totals['input_tokens'] / len(records), 2),
                input_cache_hit_ratio=totals['cached_input_tokens'] / totals['input_tokens'] if totals['input_tokens'] else None,
                limitations=['Local recorded usage only; missing logs/remote sessions cannot be counted.',
                             'Response span is not task wall time. Tool calls count outer calls, not nested commands.',
                             'No cost or quota estimate; missing optional fields are zero-filled with warnings.',
                             'Non-reasoning output includes tool arguments, not only visible prose.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--sessions-dir', type=Path,
                        default=Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'sessions')
    parser.add_argument('--since', type=timestamp)
    parser.add_argument('--until', type=timestamp)
    parser.add_argument('--json', type=Path, help='Save full report here')
    args = parser.parse_args()
    if args.since and args.until and args.since >= args.until:
        parser.error('--since must precede --until')
    try:
        report = summarize(args.sessions_dir, args.session, args.since, args.until)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f'Cannot measure safely: {exc}\n')
    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    for key in ('root_session', 'responses', 'deduplicated_copies', 'tool_calls_with_matching_turn',
                'average_input_tokens', 'input_cache_hit_ratio', 'responses_by_model_effort', 'warnings'):
        print(f'{key}: {report[key]}')
    for key, value in report['usage'].items():
        print(f'{key}: {value}')
    print('Recorded sessions:', len(report['sessions']))
    print('No monetary/plan-quota estimate; optional-field gaps appear in warnings.')


if __name__ == '__main__':
    main()
