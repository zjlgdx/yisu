"""What readers did on the site: the counts src/worker.js keeps in Workers Analytics Engine.

    CLOUDFLARE_ACCOUNT_ID=... CLOUDFLARE_API_TOKEN=... python3 -I tools/events.py [DAYS]

The token needs Account Analytics: Read. DAYS is how far back to look (7 by default; Analytics
Engine keeps three months). It prints each event with its values, most first, then the
characters readers looked up in 字庫 that the fonts don't have yet: a list of what to draw next.
Each row is weighted by its sample interval, so the counts stay true when Analytics Engine samples.
"""
import json
import os
import sys
import urllib.request

DATASET = 'yisu_events'


def sql(query):
    account, token = os.environ['CLOUDFLARE_ACCOUNT_ID'], os.environ['CLOUDFLARE_API_TOKEN']
    req = urllib.request.Request(
        f'https://api.cloudflare.com/client/v4/accounts/{account}/analytics_engine/sql',
        data=query.encode(), headers={'Authorization': f'Bearer {token}'}, method='POST')
    with urllib.request.urlopen(req) as r:
        return json.load(r)['data']


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    since = f"timestamp > NOW() - INTERVAL '{days}' DAY"
    rows = sql(f"""SELECT blob1 AS event, blob2 AS value, SUM(_sample_interval) AS n
                   FROM {DATASET} WHERE {since} AND blob1 != 'missing'
                   GROUP BY event, value ORDER BY event, n DESC FORMAT JSON""")
    print(f'== the last {days} days')
    event = None
    for r in rows:
        if r['event'] != event:
            event = r['event']; print(f'\n{event}')
        print(f"  {r['value'] or '·':10} {int(r['n'])}")
    places = sql(f"""SELECT blob3 AS country, blob4 AS device, SUM(_sample_interval) AS n
                     FROM {DATASET} WHERE {since} GROUP BY country, device ORDER BY n DESC LIMIT 15 FORMAT JSON""")
    print('\n== where from (events, not readers)')
    for r in places:
        print(f"  {r['country'] or '?':3} {r['device']:8} {int(r['n'])}")
    missing = sql(f"""SELECT blob2 AS ch, SUM(_sample_interval) AS n FROM {DATASET}
                      WHERE {since} AND blob1 = 'missing' GROUP BY ch ORDER BY n DESC LIMIT 100 FORMAT JSON""")
    print('\n== looked for and not drawn yet')
    print('  ' + ('  '.join(f"{r['ch']} {int(r['n'])}" for r in missing) or 'none'))


if __name__ == '__main__':
    main()
