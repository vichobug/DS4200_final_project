"""
generate_vizzes.py
──────────────────
DS4200 Final Project — Visualization Generator
Reads flights_cleaned.csv and writes:
  viz1.html, viz2.html, viz3.html   (Altair, white background)
  viz4.js, viz5.js                   (D3, data embedded inline)

Run AFTER preprocess.py:
  python preprocess.py
  python generate_vizzes.py
  open index.html
"""

import pandas as pd
import numpy as np
import altair as alt
import json
import os
from itertools import product as iproduct

alt.data_transformers.disable_max_rows()

# ── Shared palette ────────────────────────────────────────────────────────────
PALETTE = {
    'Late Aircraft': '#e8913a',
    'Carrier':       '#5b8abf',
    'Weather':       '#6dbcb0',
    'NAS':           '#f2c45a',
    'Security':      '#c47ba0',
}
ACCENT      = '#e8913a'
CAUSE_ORDER = ['Late Aircraft', 'Carrier', 'Weather', 'NAS', 'Security']
TOD_COLORS  = {
    'Morning':   '#5b8abf',
    'Afternoon': '#f2c45a',
    'Evening':   '#e8913a',
    'Night':     '#c47ba0',
}
TOD_ORDER = ['Morning', 'Afternoon', 'Evening', 'Night']

# ── Load cleaned data ─────────────────────────────────────────────────────────
print("Loading flights_cleaned.csv...")
df = pd.read_csv('flights_cleaned.csv', low_memory=False)
print(f"  {len(df):,} rows x {df.shape[1]} cols")

# ═════════════════════════════════════════════════════════════════════════════
# VIZ 1 — Airline On-Time Performance (Altair, static)
# ═════════════════════════════════════════════════════════════════════════════
print("\nBuilding Viz 1...")

CAUSE_COLS = {
    'LATE_AIRCRAFT_DELAY': 'Late Aircraft',
    'AIRLINE_DELAY':       'Carrier',
    'WEATHER_DELAY':       'Weather',
    'AIR_SYSTEM_DELAY':    'NAS',
    'SECURITY_DELAY':      'Security',
}

total    = df.groupby('AIRLINE_NAME').size().rename('total')
delayed  = df[df['ARRIVAL_DELAY'] > 15].groupby('AIRLINE_NAME').size().rename('delayed_ct')
pct_del  = (delayed / total * 100).rename('pct_delayed')

cause_sums = (
    df.groupby('AIRLINE_NAME')[list(CAUSE_COLS.keys())].sum()
    .rename(columns=CAUSE_COLS)
)
cause_props = cause_sums.div(cause_sums.sum(axis=1), axis=0).fillna(0)
seg  = cause_props.multiply(pct_del, axis=0).reset_index()
long = seg.melt(id_vars='AIRLINE_NAME', var_name='Delay Cause', value_name='pct_of_flights')
long = long.merge(pct_del.reset_index(), on='AIRLINE_NAME')

# ascending so best (lowest %) is at top of Y-axis, worst at bottom
airline_order = pct_del.sort_values(ascending=True).index.tolist()
overall_avg   = pct_del.mean()

color_scale = alt.Scale(domain=CAUSE_ORDER, range=[PALETTE[c] for c in CAUSE_ORDER])

bars = (
    alt.Chart(long).mark_bar(height=22)
    .encode(
        x=alt.X('pct_of_flights:Q', stack='zero',
                title='% of All Flights Delayed >15 min (by Cause)',
                axis=alt.Axis(format='.1f', labelFontSize=11, titleFontSize=12)),
        y=alt.Y('AIRLINE_NAME:N', sort=airline_order, title=None,
                axis=alt.Axis(labelFontSize=11)),
        color=alt.Color('Delay Cause:N', scale=color_scale, sort=CAUSE_ORDER,
                        legend=alt.Legend(title='Delay Cause', orient='bottom',
                                          direction='horizontal', columns=5,
                                          labelFontSize=11, titleFontSize=11)),
        order=alt.Order('Delay Cause:N', sort='ascending'),
        tooltip=[
            alt.Tooltip('AIRLINE_NAME:N',   title='Airline'),
            alt.Tooltip('Delay Cause:N',    title='Cause'),
            alt.Tooltip('pct_of_flights:Q', title='% of All Flights', format='.2f'),
            alt.Tooltip('pct_delayed:Q',    title='Total % Delayed',  format='.1f'),
        ]
    )
)

rule = (
    alt.Chart(pd.DataFrame({'x': [overall_avg]}))
    .mark_rule(strokeDash=[5, 4], strokeWidth=1.5, color='#555')
    .encode(x='x:Q')
)
lbl = (
    alt.Chart(pd.DataFrame({'x': [overall_avg], 'label': [f'Avg: {overall_avg:.1f}%']}))
    .mark_text(align='left', dx=4, dy=-8, fontSize=10, color='#555')
    .encode(x='x:Q', y=alt.value(8), text='label:N')
)

viz1 = (
    (bars + rule + lbl)
    .properties(
        title=alt.TitleParams(
            text='Airline On-Time Performance — Summer 2015',
            subtitle='Bar length = % of all flights delayed. Segments show breakdown by delay cause.',
            fontSize=14, subtitleFontSize=11, anchor='start'),
        width=620, height=320)
    .configure(background='white')
    .configure_view(strokeWidth=0)
    .configure_axis(grid=False)
)
viz1.save('viz1.html')
print("  Saved -> viz1.html")

# ═════════════════════════════════════════════════════════════════════════════
# VIZ 2 — Delay Heatmap: Hour x Day of Week (Altair, interactive)
# ═════════════════════════════════════════════════════════════════════════════
print("Building Viz 2...")

DOW_MAP   = {1:'Mon', 2:'Tue', 3:'Wed', 4:'Thu', 5:'Fri', 6:'Sat', 7:'Sun'}
DOW_ORDER = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
df['DOW']  = df['DAY_OF_WEEK'].map(DOW_MAP)

heat = (
    df.groupby(['DOW', 'hour'])
    .agg(avg_delay=('DEPARTURE_DELAY', 'mean'), flight_cnt=('DEPARTURE_DELAY', 'count'))
    .reset_index()
)
full_grid = pd.DataFrame(list(iproduct(DOW_ORDER, range(24))), columns=['DOW', 'hour'])
heat = full_grid.merge(heat, on=['DOW', 'hour'], how='left').fillna(0)
heat['flight_cnt'] = heat['flight_cnt'].astype(int)
heat['avg_delay']  = heat['avg_delay'].round(1)
heat['hour_label'] = heat['hour'].apply(
    lambda h: '12 AM' if h == 0 else f'{h} AM' if h < 12
    else '12 PM' if h == 12 else f'{h-12} PM'
)

viz2 = (
    alt.Chart(heat).mark_rect(stroke='white', strokeWidth=0.4)
    .encode(
        x=alt.X('DOW:O', sort=DOW_ORDER, title='Day of Week',
                axis=alt.Axis(labelFontSize=11, titleFontSize=12, labelAngle=0)),
        y=alt.Y('hour:O', sort='descending', title='Hour of Day (Scheduled Departure)',
                axis=alt.Axis(labelFontSize=10, titleFontSize=12,
                              values=list(range(0, 24, 3)),
                              labelExpr=("datum.value==0?'12 AM':datum.value==12?'12 PM':"
                                         "datum.value<12?datum.value+' AM':(datum.value-12)+' PM'"))),
        color=alt.Color('avg_delay:Q', title='Avg Dep. Delay (min)',
                        scale=alt.Scale(scheme='oranges', domainMin=-3),
                        legend=alt.Legend(orient='right', gradientLength=180,
                                          labelFontSize=10, titleFontSize=11)),
        tooltip=[
            alt.Tooltip('DOW:O',        title='Day'),
            alt.Tooltip('hour_label:N', title='Hour'),
            alt.Tooltip('avg_delay:Q',  title='Avg Delay (min)', format='.1f'),
            alt.Tooltip('flight_cnt:Q', title='Flights',         format=','),
        ]
    )
    .properties(
        title=alt.TitleParams(
            text='Average Departure Delay by Hour and Day of Week',
            subtitle='Summer 2015  |  Top-20 airports  |  Darker = longer delay  |  Hover for details',
            fontSize=14, subtitleFontSize=11, anchor='start'),
        width=460, height=440)
    .configure(background='white')
    .configure_view(strokeWidth=0)
)
viz2.save('viz2.html')
print("  Saved -> viz2.html")

# ═════════════════════════════════════════════════════════════════════════════
# VIZ 3 — Distance vs. Delay with Linked Histogram (Altair, interactive)
# ═════════════════════════════════════════════════════════════════════════════
print("Building Viz 3...")

viz3_df = (
    df[df['ARRIVAL_DELAY'].notna() & df['DISTANCE'].notna()]
    [['DISTANCE', 'ARRIVAL_DELAY', 'time_of_day', 'AIRLINE_NAME']]
    .reset_index(drop=True)
)

brush     = alt.selection_interval(encodings=['x', 'y'], name='brush')
tod_scale = alt.Scale(domain=TOD_ORDER, range=[TOD_COLORS[t] for t in TOD_ORDER])

scatter = (
    alt.Chart(viz3_df).mark_circle(size=20, opacity=0.5)
    .encode(
        x=alt.X('DISTANCE:Q', title='Flight Distance (miles)',
                axis=alt.Axis(labelFontSize=10, titleFontSize=11)),
        y=alt.Y('ARRIVAL_DELAY:Q', title='Arrival Delay (min)',
                scale=alt.Scale(domain=[-60, 200]),
                axis=alt.Axis(labelFontSize=10, titleFontSize=11)),
        color=alt.condition(
            brush,
            alt.Color('time_of_day:N', scale=tod_scale, sort=TOD_ORDER,
                      legend=alt.Legend(title='Time of Day', orient='bottom',
                                        direction='horizontal', columns=4,
                                        labelFontSize=10, titleFontSize=11)),
            alt.value('#cccccc')
        ),
        tooltip=[
            alt.Tooltip('AIRLINE_NAME:N',  title='Airline'),
            alt.Tooltip('DISTANCE:Q',      title='Distance (mi)', format=','),
            alt.Tooltip('ARRIVAL_DELAY:Q', title='Arrival Delay (min)', format='.0f'),
            alt.Tooltip('time_of_day:N',   title='Time of Day'),
        ]
    )
    .add_params(brush)
    .properties(
        title=alt.TitleParams(
            text='Distance vs. Arrival Delay',
            subtitle='Drag to select a region — histogram updates to show only selected flights',
            fontSize=13, subtitleFontSize=10, anchor='start'),
        width=380, height=320)
)

zero_rule = (
    alt.Chart(pd.DataFrame({'y': [0]}))
    .mark_rule(strokeDash=[4, 3], strokeWidth=1, color='#aaa')
    .encode(y='y:Q')
)

histogram = (
    alt.Chart(viz3_df).mark_bar(color=ACCENT, opacity=0.85)
    .encode(
        x=alt.X('ARRIVAL_DELAY:Q', bin=alt.Bin(step=15), title='Arrival Delay (min)',
                axis=alt.Axis(labelFontSize=10, titleFontSize=11)),
        y=alt.Y('count():Q', title='Number of Flights',
                axis=alt.Axis(labelFontSize=10, titleFontSize=11)),
        tooltip=[
            alt.Tooltip('ARRIVAL_DELAY:Q', bin=alt.Bin(step=15), title='Delay bin (min)'),
            alt.Tooltip('count():Q', title='Flights', format=','),
        ]
    )
    .transform_filter(brush)
    .properties(
        title=alt.TitleParams(
            text='Delay Distribution (selected)',
            subtitle='Updates from brush selection',
            fontSize=13, subtitleFontSize=10, anchor='start'),
        width=260, height=320)
)

viz3 = (
    alt.hconcat(scatter + zero_rule, histogram, spacing=24)
    .configure(background='white')
    .configure_view(strokeWidth=0)
    .configure_axis(grid=False)
)
viz3.save('viz3.html')
print("  Saved -> viz3.html")

# ═════════════════════════════════════════════════════════════════════════════
# VIZ 4 — D3 Airport Map  (writes viz4.js with data embedded inline)
# ═════════════════════════════════════════════════════════════════════════════
print("Building Viz 4...")

apt_stats = (
    df.groupby(['ORIGIN_AIRPORT', 'ORIGIN_AIRPORT_NAME', 'ORIGIN_CITY',
                'ORIGIN_STATE', 'ORIGIN_LAT', 'ORIGIN_LON'])
    .agg(total_flights=('FLIGHT_NUMBER', 'count'),
         avg_dep_delay=('DEPARTURE_DELAY', 'mean'))
    .reset_index()
)
top_carrier = (
    df.groupby(['ORIGIN_AIRPORT', 'AIRLINE_NAME']).size().reset_index(name='cnt')
    .sort_values('cnt', ascending=False).drop_duplicates('ORIGIN_AIRPORT')
    .rename(columns={'AIRLINE_NAME': 'top_carrier'})[['ORIGIN_AIRPORT', 'top_carrier']]
)
apt_stats = apt_stats.merge(top_carrier, on='ORIGIN_AIRPORT', how='left')
apt_stats['avg_dep_delay'] = apt_stats['avg_dep_delay'].round(2)
apt_stats = apt_stats.dropna(subset=['ORIGIN_LAT', 'ORIGIN_LON'])

apt_json = apt_stats.rename(columns={
    'ORIGIN_AIRPORT': 'iata', 'ORIGIN_AIRPORT_NAME': 'name',
    'ORIGIN_CITY': 'city', 'ORIGIN_STATE': 'state',
    'ORIGIN_LAT': 'lat', 'ORIGIN_LON': 'lon',
    'total_flights': 'flights', 'avg_dep_delay': 'avg_delay',
}).to_dict(orient='records')

VIZ4_JS = r"""// Auto-generated by generate_vizzes.py — do not edit directly
(function () {
  var AIRPORTS = __DATA__;

  var wrap = document.getElementById('viz4-container');
  if (!wrap) return;

  var W = wrap.clientWidth || 860;
  var H = Math.round(W * 0.52);

  var svg = d3.select(wrap).append('svg')
    .attr('width', W).attr('height', H)
    .style('display', 'block')
    .style('border-radius', '4px')
    .style('background', '#eef3f8');

  var g = svg.append('g');
  var proj = d3.geoAlbersUsa().scale(W * 1.28).translate([W / 2, H / 2]);
  var pathGen = d3.geoPath().projection(proj);

  // Zoom / pan
  var zoom = d3.zoom().scaleExtent([1, 10]).on('zoom', function (ev) {
    g.attr('transform', ev.transform);
    g.selectAll('.apt-bub').attr('stroke-width', 0.6 / ev.transform.k);
    g.selectAll('.st-path').style('stroke-width', (0.5 / ev.transform.k) + 'px');
  });
  svg.call(zoom);
  svg.on('dblclick.zoom', function () {
    svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
  });

  // Tooltip (appended to body so it overlays everything)
  var tip = d3.select('body').append('div').attr('class', 'd3-tip').style('display', 'none');

  var valid = AIRPORTS.filter(function (d) { return proj([d.lon, d.lat]) !== null; });
  var maxF = d3.max(valid, function (d) { return d.flights; });
  var rScale = d3.scaleSqrt().domain([0, maxF]).range([3, 26]);
  var delayExt = d3.extent(valid, function (d) { return d.avg_delay; });
  var cScale = d3.scaleSequential()
    .domain([delayExt[0], 35])
    .interpolator(d3.interpolateRgbBasis(['#5b8abf', '#f5efe8', '#e8913a', '#c0392b']));

  d3.json('https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json').then(function (us) {
    g.append('g').selectAll('path')
      .data(topojson.feature(us, us.objects.states).features)
      .join('path').attr('class', 'st-path')
      .style('fill', '#dce8d4').style('stroke', '#b0c4b0').style('stroke-width', '0.5px')
      .attr('d', pathGen);

    g.append('path')
      .datum(topojson.mesh(us, us.objects.states, function (a, b) { return a !== b; }))
      .attr('fill', 'none').attr('stroke', '#b0c4b0').attr('stroke-width', '0.5')
      .attr('d', pathGen);

    g.append('g').selectAll('circle')
      .data(valid.slice().sort(function (a, b) { return b.flights - a.flights; }))
      .join('circle').attr('class', 'apt-bub')
      .attr('cx', function (d) { return proj([d.lon, d.lat])[0]; })
      .attr('cy', function (d) { return proj([d.lon, d.lat])[1]; })
      .attr('r',  function (d) { return rScale(d.flights); })
      .attr('fill', function (d) { return cScale(d.avg_delay); })
      .attr('opacity', 0.85)
      .attr('stroke', '#fff').attr('stroke-width', 0.6)
      .style('cursor', 'pointer')
      .on('mouseover', function (ev, d) {
        var s = d.avg_delay >= 0
          ? '+' + d.avg_delay.toFixed(1) + ' min late'
          : Math.abs(d.avg_delay).toFixed(1) + ' min early';
        tip.style('display', 'block').html(
          '<strong class="tip-airport-code">' + d.iata + '</strong><br>' +
          d.name + '<br>' + d.city + ', ' + d.state + '<br>' +
          '<strong>Flights:</strong> ' + d3.format(',')(d.flights) + '<br>' +
          '<strong>Avg Delay:</strong> ' + s + '<br>' +
          '<strong>Top Carrier:</strong> ' + (d.top_carrier || 'N/A')
        );
        tip.style('left', (ev.clientX + 14) + 'px').style('top', (ev.clientY - 10) + 'px');
      })
      .on('mousemove', function (ev) {
        tip.style('left', (ev.clientX + 14) + 'px').style('top', (ev.clientY - 10) + 'px');
      })
      .on('mouseout', function () { tip.style('display', 'none'); });

    // Color legend
    var legWrap = d3.select(wrap).append('div').attr('class', 'apt-leg-wrap');
    legWrap.append('span').attr('class', 'apt-leg-title').text('Avg Departure Delay:');
    var canvas = legWrap.append('canvas')
      .attr('width', 180).attr('height', 10)
      .style('border-radius', '3px').node();
    var ctx = canvas.getContext('2d');
    var gr = ctx.createLinearGradient(0, 0, 180, 0);
    for (var i = 0; i <= 10; i++) {
      var t = i / 10;
      gr.addColorStop(t, cScale(delayExt[0] + t * (35 - delayExt[0])));
    }
    ctx.fillStyle = gr; ctx.fillRect(0, 0, 180, 10);
    legWrap.append('span').attr('class', 'apt-leg-lo').text(delayExt[0].toFixed(1) + ' min');
    legWrap.append('span').attr('class', 'apt-leg-hi').text('35+ min');
    legWrap.append('span').attr('class', 'apt-leg-hint').text('  |  Double-click map to reset zoom');
  });
})();
"""

viz4_code = VIZ4_JS.replace('__DATA__', json.dumps(apt_json))
with open('viz4.js', 'w') as f:
    f.write(viz4_code)
print(f"  Saved -> viz4.js  ({len(apt_json)} airports)")

# ═════════════════════════════════════════════════════════════════════════════
# VIZ 5 — D3 Daily Delay Trend by Airline  (writes viz5.js with inline data)
# ═════════════════════════════════════════════════════════════════════════════
print("Building Viz 5...")

df['DATE'] = pd.to_datetime(
    df[['YEAR', 'MONTH', 'DAY']].rename(
        columns={'YEAR': 'year', 'MONTH': 'month', 'DAY': 'day'})
).dt.strftime('%Y-%m-%d')

daily = (
    df.groupby(['DATE', 'AIRLINE_NAME'])
    .agg(avg_delay=('ARRIVAL_DELAY', 'mean'))
    .reset_index()
)
daily['avg_delay'] = daily['avg_delay'].round(2)

worst5 = (
    daily.groupby('AIRLINE_NAME')['avg_delay'].mean()
    .sort_values(ascending=False).head(5).index.tolist()
)
all_airlines = (
    daily.groupby('AIRLINE_NAME')['avg_delay'].mean()
    .sort_values(ascending=False).index.tolist()
)

v5_payload = {
    'airlines': all_airlines,
    'default':  worst5,
    'data': daily[['DATE', 'AIRLINE_NAME', 'avg_delay']].to_dict(orient='records'),
}

VIZ5_JS = r"""// Auto-generated by generate_vizzes.py — do not edit directly
(function () {
  var PAYLOAD = __DATA__;
  var COLORS = ['#e8913a','#5b8abf','#6dbcb0','#f2c45a','#c47ba0',
                '#59a14f','#edc948','#ff9da7','#9c755f','#bab0ac',
                '#d37295','#499894','#86bcb6','#e15759'];

  var wrap = document.getElementById('viz5-container');
  if (!wrap) return;

  // Inject dropdown HTML
  var ddDiv = document.createElement('div');
  ddDiv.className = 'v5-controls';
  ddDiv.innerHTML =
    '<div class="v5-dd-wrap">' +
      '<button class="v5-dd-btn" id="v5-btn">' +
        '<span id="v5-lbl">Airlines shown: 5</span>' +
        '<span class="v5-arr">&#9660;</span>' +
      '</button>' +
      '<div class="v5-dd-panel" id="v5-panel">' +
        '<div class="v5-dd-actions">' +
          '<button id="v5-all">All</button>' +
          '<button id="v5-none">Clear</button>' +
          '<button id="v5-def">Reset</button>' +
        '</div>' +
        '<hr class="v5-divider"/>' +
      '</div>' +
    '</div>';
  wrap.appendChild(ddDiv);

  var TW = wrap.clientWidth || 860;
  var TH = 340;
  var ML = { top: 28, right: 20, bottom: 48, left: 56 };
  var W = TW - ML.left - ML.right;
  var H = TH - ML.top - ML.bottom;

  var svg = d3.select(wrap).append('svg')
    .attr('width', TW).attr('height', TH)
    .style('display', 'block').style('background', '#fff');

  var g = svg.append('g').attr('transform', 'translate(' + ML.left + ',' + ML.top + ')');
  var tip = d3.select('body').append('div').attr('class', 'd3-tip').style('display', 'none');

  var allAirlines = PAYLOAD.airlines;
  var defSet = {};
  PAYLOAD.default.forEach(function (a) { defSet[a] = true; });
  var selected = {};
  PAYLOAD.default.forEach(function (a) { selected[a] = true; });

  var parseDate = d3.timeParse('%Y-%m-%d');
  var raw = PAYLOAD.data.map(function (d) {
    return { date: parseDate(d.DATE), airline: d.AIRLINE_NAME, delay: d.avg_delay };
  });
  var byAirline = d3.group(raw, function (d) { return d.airline; });
  var colorMap = {};
  allAirlines.forEach(function (a, i) { colorMap[a] = COLORS[i % COLORS.length]; });

  var xScale = d3.scaleTime()
    .domain([new Date('2015-06-01'), new Date('2015-08-31')]).range([0, W]);
  var allDelays = raw.map(function (d) { return d.delay; });
  var yScale = d3.scaleLinear()
    .domain([d3.min(allDelays) - 2, d3.max(allDelays) + 4]).nice().range([H, 0]);

  // Axes
  g.append('g').attr('class', 'v5-axis x-axis').attr('transform', 'translate(0,' + H + ')')
    .call(d3.axisBottom(xScale).ticks(d3.timeWeek.every(2)).tickFormat(d3.timeFormat('%b %d')));
  g.append('g').attr('class', 'v5-axis y-axis')
    .call(d3.axisLeft(yScale).ticks(7).tickFormat(function (d) { return d + ' min'; }));

  g.append('text').attr('x', W / 2).attr('y', H + 40)
    .attr('text-anchor', 'middle').attr('font-size', '11px').attr('fill', '#888').text('Date');
  g.append('text').attr('transform', 'rotate(-90)').attr('x', -H / 2).attr('y', -44)
    .attr('text-anchor', 'middle').attr('font-size', '11px').attr('fill', '#888')
    .text('Avg Arrival Delay (min)');

  // Grid + zero line + holiday marker
  g.append('g').attr('class', 'v5-grid')
    .call(d3.axisLeft(yScale).ticks(7).tickSize(-W).tickFormat(''));
  g.append('line').attr('class', 'v5-zero')
    .attr('x1', 0).attr('x2', W).attr('y1', yScale(0)).attr('y2', yScale(0));
  var hx = xScale(new Date('2015-07-04'));
  g.append('line').attr('class', 'v5-hol')
    .attr('x1', hx).attr('x2', hx).attr('y1', 0).attr('y2', H);
  g.append('text').attr('class', 'v5-hol-lbl').attr('x', hx + 3).attr('y', 12).text('Jul 4');

  var lineGen = d3.line()
    .defined(function (d) { return d.delay != null && !isNaN(d.delay); })
    .x(function (d) { return xScale(d.date); })
    .y(function (d) { return yScale(d.delay); })
    .curve(d3.curveMonotoneX);

  var linesG = g.append('g');
  var hLine = g.append('line').attr('class', 'v5-hover-line')
    .attr('y1', 0).attr('y2', H).style('display', 'none');
  var dotsG = g.append('g');
  var bisect = d3.bisector(function (d) { return d.date; }).left;

  // Hover overlay
  g.append('rect').attr('width', W).attr('height', H)
    .attr('fill', 'none').attr('pointer-events', 'all')
    .on('mousemove', function (ev) {
      var mx = d3.pointer(ev)[0];
      var hd = xScale.invert(mx);
      hLine.style('display', null).attr('x1', mx).attr('x2', mx);
      var rows = [];
      allAirlines.filter(function (a) { return selected[a]; }).forEach(function (a) {
        var pts = (byAirline.get(a) || []).slice().sort(function (x, y) { return x.date - y.date; });
        if (!pts.length) return;
        var i = bisect(pts, hd, 1);
        var d0 = pts[i - 1], d1 = pts[i];
        var d = !d1 ? d0 : !d0 ? d1 : (hd - d0.date < d1.date - hd ? d0 : d1);
        if (d) rows.push({ airline: a, d: d, color: colorMap[a] });
      });
      dotsG.selectAll('.v5-dot').remove();
      rows.forEach(function (r) {
        if (r.d.delay == null || isNaN(r.d.delay)) return;
        dotsG.append('circle').attr('class', 'v5-dot')
          .attr('cx', xScale(r.d.date)).attr('cy', yScale(r.d.delay))
          .attr('r', 4).attr('fill', r.color)
          .attr('stroke', '#fff').attr('stroke-width', 1.5)
          .style('pointer-events', 'none');
      });
      if (!rows.length) { tip.style('display', 'none'); return; }
      var ds = d3.timeFormat('%a, %b %e')(rows[0].d.date);
      var rh = rows.slice().sort(function (a, b) { return b.d.delay - a.d.delay; })
        .map(function (r) {
          var sign = r.d.delay >= 0 ? '+' : '';
          var name = r.airline.replace(/ Inc\.| Co\./g, '');
          return '<div class="tip-row">' +
            '<span><span class="tip-sw" style="background:' + r.color + '"></span>' + name + '</span>' +
            '<span><strong>' + sign + r.d.delay.toFixed(1) + ' min</strong></span></div>';
        }).join('');
      tip.style('display', 'block')
        .html('<div class="tip-date">' + ds + '</div>' + rh)
        .style('left', (ev.clientX + 14) + 'px').style('top', (ev.clientY - 10) + 'px');
    })
    .on('mouseleave', function () {
      hLine.style('display', 'none');
      dotsG.selectAll('.v5-dot').remove();
      tip.style('display', 'none');
    });

  var legDiv = d3.select(wrap).append('div').attr('class', 'v5-legend');

  function draw() {
    var ld = allAirlines.filter(function (a) { return selected[a]; });
    var paths = linesG.selectAll('.v5-line').data(ld, function (d) { return d; });
    paths.enter().append('path').attr('class', 'v5-line')
      .merge(paths)
      .attr('fill', 'none').attr('stroke-width', 2)
      .attr('stroke', function (d) { return colorMap[d]; })
      .attr('d', function (d) {
        var pts = (byAirline.get(d) || []).slice().sort(function (a, b) { return a.date - b.date; });
        return lineGen(pts);
      });
    paths.exit().remove();
    legDiv.selectAll('.v5-leg-item').remove();
    ld.forEach(function (a) {
      var item = legDiv.append('div').attr('class', 'v5-leg-item');
      item.append('div').attr('class', 'v5-leg-line').style('background', colorMap[a]);
      item.append('span').text(a);
    });
    document.getElementById('v5-lbl').textContent = 'Airlines shown: ' + ld.length;
  }

  // Dropdown behaviour
  var panel = document.getElementById('v5-panel');
  var btn   = document.getElementById('v5-btn');
  btn.addEventListener('click', function (e) {
    e.stopPropagation(); panel.classList.toggle('open');
  });
  document.addEventListener('click', function () { panel.classList.remove('open'); });
  panel.addEventListener('click', function (e) { e.stopPropagation(); });

  allAirlines.forEach(function (a) {
    var lbl = document.createElement('label'); lbl.className = 'v5-dd-item';
    var cb  = document.createElement('input'); cb.type = 'checkbox'; cb.checked = !!defSet[a];
    cb.addEventListener('change', function () {
      if (cb.checked) selected[a] = true; else delete selected[a]; draw();
    });
    var sw = document.createElement('div'); sw.className = 'v5-sw'; sw.style.background = colorMap[a];
    lbl.appendChild(cb); lbl.appendChild(sw); lbl.appendChild(document.createTextNode(a));
    panel.appendChild(lbl);
  });

  document.getElementById('v5-all').onclick = function () {
    allAirlines.forEach(function (a) { selected[a] = true; });
    panel.querySelectorAll('input').forEach(function (c) { c.checked = true; }); draw();
  };
  document.getElementById('v5-none').onclick = function () {
    selected = {};
    panel.querySelectorAll('input').forEach(function (c) { c.checked = false; }); draw();
  };
  document.getElementById('v5-def').onclick = function () {
    selected = {};
    Object.keys(defSet).forEach(function (a) { selected[a] = true; });
    panel.querySelectorAll('.v5-dd-item').forEach(function (lbl) {
      var cb = lbl.querySelector('input');
      if (cb) cb.checked = !!defSet[lbl.textContent.trim()];
    }); draw();
  };

  draw();
})();
"""

viz5_code = VIZ5_JS.replace('__DATA__', json.dumps(v5_payload))
with open('viz5.js', 'w') as f:
    f.write(viz5_code)
print(f"  Saved -> viz5.js  ({len(all_airlines)} airlines, {len(v5_payload['data'])} daily rows)")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 52)
print("Files generated:")
for fn in ['viz1.html', 'viz2.html', 'viz3.html', 'viz4.js', 'viz5.js']:
    try:
        kb = os.path.getsize(fn) / 1024
        print(f"  {fn:<16} {kb:>7.1f} KB")
    except FileNotFoundError:
        print(f"  {fn:<16}  (not found)")
print("\nDone. Open index.html in a browser (or serve with:")
print("  python -m http.server 8000  then visit http://localhost:8000)")
