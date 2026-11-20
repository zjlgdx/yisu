// The site is static files. The one thing this script does is count what readers do: the page
// posts a name and a short value to /e, and they go into Workers Analytics Engine with the
// reader's country and kind of device. No cookie, no IP address, no user agent is kept.

// Each event the page sends, and the values it may carry. Anything else is dropped.
const EVENTS = {
  read: /^(lanting|chibi|tengwang)$/,          // 朗讀 turned on, in this text
  sound: /^(light|dark)$/,                     // the music turned on, by day or by night
  piece: /^(lanting|chibi|tengwang)$/,         // a text picked under 讀全文
  pen: /^(clay|sand|rain)$/,                   // a family picked for the scroll
  done: /^(lanting|chibi|tengwang)$/,          // the scroll written to its end
  finish: /^(lanting|chibi|tengwang)$/,        // 一次寫完: the rest shown at once
  cine: /^(lanting|chibi|tengwang)$/,          // 觀影 opened
  'cine-end': /^(lanting|chibi|tengwang)$/,    // 觀影 watched to its end
  char: /^\p{Script=Han}$/u,                   // a character looked up in 字庫 and found
  missing: /^\p{Script=Han}$/u,                // a character looked up and not drawn yet
  try: /^$/,                                   // the box to type in, first used
};

const MOBILE = /Mobi|Android|iPhone|iPad/;

async function count(request, env) {
  let e;
  try { e = JSON.parse(await request.text()); } catch { return new Response(null, { status: 400 }); }
  const name = typeof e?.n === 'string' ? e.n : '', value = typeof e?.v === 'string' ? e.v : '';
  if (!EVENTS[name]?.test(value)) return new Response(null, { status: 400 });
  const device = MOBILE.test(request.headers.get('user-agent') || '') ? 'mobile' : 'desktop';
  env.EVENTS?.writeDataPoint({
    indexes: [name],
    blobs: [name, value, request.cf?.country || '', device],
    doubles: [1],
  });
  return new Response(null, { status: 204 });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/e') {
      if (request.method !== 'POST') return new Response(null, { status: 405, headers: { Allow: 'POST' } });
      return count(request, env);
    }
    return env.ASSETS.fetch(request);
  },
};
